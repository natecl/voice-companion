import XCTest

private actor RefreshFixture: AccountRefreshing {
    var calls = 0
    let response: AccountSession
    var continuation: CheckedContinuation<AccountSession, Error>?
    init(_ response: AccountSession) { self.response = response }
    func refresh(_ token: String) async throws -> AccountSession {
        calls += 1
        return try await withCheckedThrowingContinuation { continuation = $0 }
    }
    func waitForRequest() async { while calls == 0 { await Task.yield() } }
    func complete() { continuation?.resume(returning: response); continuation = nil }
}

@MainActor
final class AccountSessionTests: XCTestCase {
    func session(owner: String, expired: Bool = false) -> AccountSession {
        AccountSession(token: String(repeating: "a", count: 43), refreshToken: String(repeating: "r", count: 64),
                       owner: owner, expires: Date.now.timeIntervalSince1970 + (expired ? -1 : 3600),
                       refreshExpires: Date.now.timeIntervalSince1970 + 86400)
    }
    func stored(_ session: AccountSession) -> StoredAccount {
        StoredAccount(endpoint: URL(string: "wss://example.com/account")!, provider: .google, session: session, googleGrant: GoogleAccountGrant(subject: "fictional-subject", token: "fictional-google-grant"))
    }

    func testConcurrentRequestsShareOneRefresh() async throws {
        let owner = UUID().uuidString
        let fixture = RefreshFixture(session(owner: owner))
        let manager = AccountSessionManager(account: stored(session(owner: owner, expired: true)),
                                            save: { _ in }, clear: {}, makeTransport: { _ in fixture })
        let first = Task { try await manager.current() }
        await fixture.waitForRequest()
        let second = Task { try await manager.current() }
        await fixture.complete()
        let a = try await first.value
        let b = try await second.value
        XCTAssertEqual(a.session.owner, b.session.owner)
        XCTAssertEqual(a.googleGrant?.token, "fictional-google-grant")
        let count = await fixture.calls
        XCTAssertEqual(count, 1)
    }

    func testRefreshStartsBeforeFiveMinuteCaptureCouldOutliveAccess() async throws {
        let owner = UUID().uuidString
        let initial = session(owner: owner)
        let fixture = RefreshFixture(session(owner: owner))
        let manager = AccountSessionManager(account: stored(initial), save: { _ in }, clear: {},
                                            makeTransport: { _ in fixture })
        let request = Task { try await manager.current(now: Date(timeIntervalSince1970: initial.expires - 599)) }
        await fixture.waitForRequest()
        await fixture.complete()
        _ = try await request.value
        let calls = await fixture.calls
        XCTAssertEqual(calls, 1)
    }

    func testLateRefreshCannotRestoreSignedOutAccount() async throws {
        let owner = UUID().uuidString
        let fixture = RefreshFixture(session(owner: owner))
        let manager = AccountSessionManager(account: stored(session(owner: owner, expired: true)),
                                            save: { _ in XCTFail("Stale session was saved") }, clear: {},
                                            makeTransport: { _ in fixture })
        let request = Task { try await manager.current() }
        await fixture.waitForRequest()
        _ = try await manager.removeLocalAccount()
        await fixture.complete()
        do { _ = try await request.value; XCTFail("Stale refresh succeeded") } catch {}
        do { _ = try await manager.current(); XCTFail("Account restored") } catch {}
    }

    func testExpiredRefreshClearsSessionBeforeAnotherOwnerCanSignIn() async throws {
        let first = session(owner: UUID().uuidString)
        let manager = AccountSessionManager(account: stored(first), save: { _ in }, clear: {})
        do {
            _ = try await manager.current(now: Date(timeIntervalSince1970: first.refreshExpires + 1))
            XCTFail("Expired session returned")
        } catch {}
        let next = stored(session(owner: UUID().uuidString))
        try await manager.install(next)
        let actual = try await manager.current()
        XCTAssertEqual(actual.session.owner, next.session.owner)
    }

    func testRestoredExpiredAccessRefreshesBeforeSaving() async throws {
        let owner = UUID().uuidString
        let fixture = RefreshFixture(session(owner: owner))
        let manager = AccountSessionManager(account: nil, save: { value in
            XCTAssertGreaterThan(value.session.expires, Date.now.timeIntervalSince1970)
        }, clear: {}, makeTransport: { _ in fixture })
        try await manager.install(stored(session(owner: owner, expired: true)), restoring: true)
        let request = Task { try await manager.current() }
        await fixture.waitForRequest()
        await fixture.complete()
        _ = try await request.value
    }

    func testRequestRefreshRejectsChangedOwnerOrBackend() throws {
        let owner = UUID().uuidString
        let config = RelayConfiguration(url: URL(string: "wss://example.com/stt")!, token: "old", rootCertificate: nil, memoryOwnerID: owner)
        let fresh = stored(session(owner: owner))
        XCTAssertEqual(try config.refreshed(using: fresh).token, fresh.session.token)
        XCTAssertThrowsError(try config.refreshed(using: stored(session(owner: UUID().uuidString))))
        let other = StoredAccount(endpoint: URL(string: "wss://other.example/account")!, provider: .google, session: fresh.session)
        XCTAssertThrowsError(try config.refreshed(using: other))
    }

    func testOwnerSwitchRequiresTeardownAndSignOut() async throws {
        let manager = AccountSessionManager(account: stored(session(owner: UUID().uuidString)), save: { _ in }, clear: {})
        do { try await manager.install(stored(session(owner: UUID().uuidString))); XCTFail("Switched owner") } catch {}
        _ = try await manager.removeLocalAccount()
        let next = stored(session(owner: UUID().uuidString))
        try await manager.install(next)
        let actual = try await manager.current()
        XCTAssertEqual(actual.session.owner, next.session.owner)
    }

    func testAccountStoreRejectsOtherOwnerAndUnownedLegacyRecording() throws {
        let base = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: base) }
        let owner = UUID().uuidString
        let store = SessionStore(directory: base, expectedOwner: owner)
        var recording = CaptureSession(id: UUID(), createdAt: .now)
        XCTAssertThrowsError(try store.save(recording))
        recording.memoryOwnerID = UUID().uuidString
        XCTAssertThrowsError(try store.save(recording))
        recording.memoryOwnerID = owner
        try store.save(recording)
        XCTAssertEqual(try store.load().count, 1)
        var foreign = CaptureSession(id: UUID(), createdAt: .now)
        foreign.memoryOwnerID = UUID().uuidString
        try SessionStore(directory: base).save(foreign)
        XCTAssertThrowsError(try store.load())
    }

    func testTransportRejectsUnencryptedOrCredentialBearingEndpoints() {
        for value in ["ws://example.com/account", "wss://example.com/stt", "wss://user:secret@example.com/account",
                      "wss://example.com/account?token=x", "wss://example.com/account#x"] {
            XCTAssertThrowsError(try AccountTransport(endpoint: URL(string: value)!))
        }
    }
}
