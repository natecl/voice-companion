import Foundation
import XCTest

private actor GoogleRecoveryTransport: AccountRefreshing {
    enum Outcome: Sendable {
        case timeout
        case rejected
        case response(AccountSession)
    }
    let outcome: Outcome
    private(set) var tokens: [String] = []

    init(_ outcome: Outcome) { self.outcome = outcome }

    func refresh(_ token: String) async throws -> AccountSession {
        tokens.append(token)
        switch outcome {
        case .timeout: throw URLError(.timedOut)
        case .rejected: throw AccountFailure.signInRequired
        case .response(let session): return session
        }
    }
}

/// Injected file persistence, not the application Keychain service.
private final class GoogleRecoveryPersistence: @unchecked Sendable {
    private struct State: Codable { let account: StoredAccount? }
    private let lock = NSLock()
    private let file: URL
    private var failNextSave = false
    private var failClear = false
    private var clears = 0
    private var attemptedSaves: [StoredAccount] = []

    init(file: URL, account: StoredAccount) throws {
        self.file = file
        try JSONEncoder().encode(State(account: account)).write(to: file, options: .atomic)
    }

    func save(_ account: StoredAccount) throws {
        lock.lock(); defer { lock.unlock() }
        attemptedSaves.append(account)
        if failNextSave {
            failNextSave = false
            throw AccountFailure.unavailable
        }
        try JSONEncoder().encode(State(account: account)).write(to: file, options: .atomic)
    }

    func clear() throws {
        lock.lock(); defer { lock.unlock() }
        clears += 1
        if failClear { throw AccountFailure.unavailable }
        try JSONEncoder().encode(State(account: nil)).write(to: file, options: .atomic)
    }

    func load() throws -> StoredAccount? {
        lock.lock(); defer { lock.unlock() }
        return try JSONDecoder().decode(State.self, from: Data(contentsOf: file)).account
    }

    func injectSaveFailure() { lock.lock(); defer { lock.unlock() }; failNextSave = true }
    func injectClearFailure() { lock.lock(); defer { lock.unlock() }; failClear = true }
    func allowClear() { lock.lock(); defer { lock.unlock() }; failClear = false }
    var clearCount: Int { lock.lock(); defer { lock.unlock() }; return clears }
    var saveAttempts: [StoredAccount] { lock.lock(); defer { lock.unlock() }; return attemptedSaves }
}

@MainActor
final class GoogleNativeFailureRecoveryTests: XCTestCase {
    private enum ExpectedFailure { case timeout, signInRequired, invalidResponse, unavailable }
    private enum TestFailure: Error { case unexpectedSuccess }

    private struct Fixture {
        let root: URL
        let account: StoredAccount
        let persistence: GoogleRecoveryPersistence
        let store: SessionStore
        let recording: CaptureSession
        let recordingFile: URL
        let originalBytes: Data
    }

    private func session(owner: String, accessExpired: Bool = false, fresh: Bool = false) -> AccountSession {
        AccountSession(token: String(repeating: fresh ? "b" : "a", count: 43),
                       refreshToken: String(repeating: fresh ? "s" : "r", count: 64),
                       owner: owner,
                       expires: Date.now.timeIntervalSince1970 + (accessExpired ? -1 : 3600),
                       refreshExpires: Date.now.timeIntervalSince1970 + 86400)
    }

    private func account(_ session: AccountSession) -> StoredAccount {
        StoredAccount(endpoint: URL(string: "wss://example.invalid/account")!, provider: .google,
                      session: session,
                      googleGrant: GoogleAccountGrant(subject: "fictional-google-subject",
                                                     token: "fictional-google-grant"))
    }

    private func fixture(accessExpired: Bool = true) throws -> Fixture {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        addTeardownBlock { try FileManager.default.removeItem(at: root) }
        let stored = account(session(owner: UUID().uuidString, accessExpired: accessExpired))
        let persistence = try GoogleRecoveryPersistence(file: root.appendingPathComponent("account.json"),
                                                        account: stored)
        let store = SessionStore(directory: root.appendingPathComponent("sessions"),
                                 expectedOwner: stored.session.owner)
        var recording = CaptureSession(id: UUID(), createdAt: .now)
        recording.memoryOwnerID = stored.session.owner
        recording.completed = true
        recording.transcript.apply(TranscriptSegment(start: 0, duration: 1,
            text: "Fictional Google recovery marker: amber observatory.", words: [], isFinal: true))
        try store.save(recording)
        let file = store.directory.appendingPathComponent(recording.id.uuidString + ".json")
        return Fixture(root: root, account: stored, persistence: persistence, store: store,
                       recording: recording, recordingFile: file, originalBytes: try Data(contentsOf: file))
    }

    private func manager(_ account: StoredAccount?, persistence: GoogleRecoveryPersistence,
                         transport: GoogleRecoveryTransport) -> AccountSessionManager {
        AccountSessionManager(account: account, save: { try persistence.save($0) },
                              clear: { try persistence.clear() }, makeTransport: { _ in transport })
    }

    private func expectFailure(_ manager: AccountSessionManager, _ expected: ExpectedFailure,
                               now: Date = .now) async throws {
        do {
            _ = try await manager.current(now: now)
            XCTFail("Unexpected successful account access")
            throw TestFailure.unexpectedSuccess
        } catch {
            switch (expected, error) {
            case (.timeout, let error as URLError): XCTAssertEqual(error.code, .timedOut)
            case (.signInRequired, AccountFailure.signInRequired),
                 (.invalidResponse, AccountFailure.invalidResponse),
                 (.unavailable, AccountFailure.unavailable): break
            default:
                XCTFail("Unexpected error: \(error)")
                throw error
            }
        }
    }

    private func assertContentPreserved(_ fixture: Fixture) throws {
        XCTAssertEqual(try Data(contentsOf: fixture.recordingFile), fixture.originalBytes)
        let reopened = try fixture.store.load()
        XCTAssertEqual(reopened.count, 1)
        XCTAssertEqual(reopened.first?.id, fixture.recording.id)
        XCTAssertEqual(reopened.first?.memoryOwnerID, fixture.account.session.owner)
        XCTAssertEqual(reopened.first?.transcript.segments.first?.text,
                       "Fictional Google recovery marker: amber observatory.")
    }

    private func recover(_ manager: AccountSessionManager, fixture: Fixture,
                         transport: GoogleRecoveryTransport) async throws {
        // Supplied synthetic proof result; this does not execute Google sign-in.
        let fresh = account(session(owner: fixture.account.session.owner, fresh: true))
        try await manager.install(fresh)
        let current = try await manager.current()
        XCTAssertEqual(current.session.owner, fresh.session.owner)
        XCTAssertEqual(current.session.refreshToken, fresh.session.refreshToken)
        XCTAssertEqual(current.googleGrant, fresh.googleGrant)
        let reopened = self.manager(try fixture.persistence.load(), persistence: fixture.persistence,
                                    transport: transport)
        let restored = try await reopened.current()
        XCTAssertEqual(restored.session.token, fresh.session.token)
        XCTAssertEqual(restored.googleGrant, fresh.googleGrant)
        try assertContentPreserved(fixture)
    }

    private func exercise(_ outcome: GoogleRecoveryTransport.Outcome,
                          expected: ExpectedFailure, fixture: Fixture,
                          expectedSaveAttempts: Int = 0) async throws {
        let transport = GoogleRecoveryTransport(outcome)
        let manager = self.manager(fixture.account, persistence: fixture.persistence, transport: transport)
        try await expectFailure(manager, expected)
        XCTAssertNil(try fixture.persistence.load())
        XCTAssertEqual(fixture.persistence.clearCount, 1)
        // Keep an audit of attempted writes even after clear, so a forbidden
        // transient save of a foreign/expired response cannot hide in cleanup.
        XCTAssertEqual(fixture.persistence.saveAttempts.count, expectedSaveAttempts)
        try assertContentPreserved(fixture)
        try await expectFailure(manager, .signInRequired)
        let signedOutRestart = self.manager(try fixture.persistence.load(), persistence: fixture.persistence,
                                            transport: transport)
        try await expectFailure(signedOutRestart, .signInRequired)
        let tokensBeforeRecovery = await transport.tokens
        XCTAssertEqual(tokensBeforeRecovery, [fixture.account.session.refreshToken])
        try await recover(manager, fixture: fixture, transport: transport)
        XCTAssertEqual(fixture.persistence.saveAttempts.count, expectedSaveAttempts + 1)
        let tokensAfterRecovery = await transport.tokens
        XCTAssertEqual(tokensAfterRecovery, tokensBeforeRecovery, "No failed rotation may be retried automatically")
    }

    func testGoogleNetworkTimeoutPreservesContentAndRecoversAcrossManagerRestart() async throws {
        try await exercise(.timeout, expected: .timeout, fixture: fixture())
    }

    func testGoogleRejectedAppSessionClearsPersistenceWithoutRetry() async throws {
        try await exercise(.rejected, expected: .signInRequired, fixture: fixture())
    }

    func testOtherOwnerRefreshResponseCannotPersistOrExposeAnAccount() async throws {
        try await exercise(.response(session(owner: UUID().uuidString, fresh: true)),
                           expected: .invalidResponse, fixture: fixture())
    }

    func testExpiredRefreshResponseCannotPersistOrExposeAnAccount() async throws {
        let fixture = try fixture()
        try await exercise(.response(session(owner: fixture.account.session.owner, accessExpired: true)),
                           expected: .invalidResponse, fixture: fixture)
    }

    func testUncertainRotationSaveFailureClearsAccessWithoutRetry() async throws {
        let fixture = try fixture()
        fixture.persistence.injectSaveFailure()
        try await exercise(.response(session(owner: fixture.account.session.owner, fresh: true)),
                           expected: .unavailable, fixture: fixture, expectedSaveAttempts: 1)
    }

    func testFailedSecureClearDropsInMemoryAccessButDoesNotProveDurableSignOut() async throws {
        let fixture = try fixture()
        fixture.persistence.injectClearFailure()
        let transport = GoogleRecoveryTransport(.timeout)
        let manager = self.manager(fixture.account, persistence: fixture.persistence, transport: transport)
        try await expectFailure(manager, .timeout)
        try await expectFailure(manager, .signInRequired)
        let tokens = await transport.tokens
        XCTAssertEqual(tokens, [fixture.account.session.refreshToken])
        XCTAssertEqual(fixture.persistence.clearCount, 1)
        // Characterize the limit honestly: failed persistence still contains the
        // old secret. No restart denial or locked-device Keychain claim follows.
        XCTAssertEqual(try fixture.persistence.load()?.session.refreshToken, fixture.account.session.refreshToken)
        try assertContentPreserved(fixture)
        fixture.persistence.allowClear()
        _ = try await manager.removeLocalAccount()
        XCTAssertNil(try fixture.persistence.load())
        try await recover(manager, fixture: fixture, transport: transport)
    }

    func testGoogleFamilyDeadlineClearsWithoutCallingTransport() async throws {
        let fixture = try fixture(accessExpired: false)
        let transport = GoogleRecoveryTransport(.timeout)
        let manager = self.manager(fixture.account, persistence: fixture.persistence, transport: transport)
        try await expectFailure(manager, .signInRequired,
                                now: Date(timeIntervalSince1970: fixture.account.session.refreshExpires))
        XCTAssertNil(try fixture.persistence.load())
        XCTAssertEqual(fixture.persistence.clearCount, 1)
        try await expectFailure(manager, .signInRequired)
        try await recover(manager, fixture: fixture, transport: transport)
        let tokens = await transport.tokens
        XCTAssertTrue(tokens.isEmpty)
    }
}
