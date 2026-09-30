import XCTest
import CryptoKit

final class FounderAccountMigrationTests: XCTestCase {
    func fixture() throws -> (URL, FounderAccountMigration, StoredAccount) {
        let base = FileManager.default.temporaryDirectory.resolvingSymlinksInPath().appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
        addTeardownBlock { try FileManager.default.removeItem(at: base) }
        let owner = UUID().uuidString
        var session = CaptureSession(id: UUID(), createdAt: .now)
        session.memoryOwnerID = owner; session.completed = true
        let directory = base.appendingPathComponent("sessions")
        try SessionStore(directory: directory).save(session)
        let file = directory.appendingPathComponent(session.id.uuidString + ".json")
        let data = try Data(contentsOf: file)
        let hash = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
        let outbox = base.appendingPathComponent("memory-outbox").appendingPathComponent(owner)
        try FileManager.default.createDirectory(at: outbox, withIntermediateDirectories: true)
        let endpoint = URL(string: "wss://example.com/account")!
        let plan = FounderAccountMigration(version: 1, owner: owner, endpoint: endpoint,
                                           sessions: [file.lastPathComponent: hash], outbox: [:])
        try JSONEncoder().encode(plan).write(to: base.appendingPathComponent(FounderAccountMigration.filename))
        let account = StoredAccount(endpoint: endpoint, provider: .google,
            session: AccountSession(token: String(repeating: "a", count: 43), refreshToken: String(repeating: "r", count: 64),
                owner: owner, expires: Date.now.timeIntervalSince1970 + 3600, refreshExpires: Date.now.timeIntervalSince1970 + 86400))
        return (base, plan, account)
    }

    func testRenamePreservesBytesAndResumesBeforeCredentialCommit() throws {
        let (base, plan, account) = try fixture()
        let original = try Data(contentsOf: base.appendingPathComponent("sessions").appendingPathComponent(plan.sessions.keys.first!))
        try plan.prepareStorage(account: account, base: base)
        XCTAssertNotNil(try FounderAccountMigration.pending(base: base))
        XCTAssertFalse(FileManager.default.fileExists(atPath: base.appendingPathComponent("sessions").path))
        let destination = base.appendingPathComponent("accounts").appendingPathComponent(plan.owner).appendingPathComponent("sessions")
        XCTAssertEqual(try Data(contentsOf: destination.appendingPathComponent(plan.sessions.keys.first!)), original)
        // A fresh decode models restart after rename but before Keychain save.
        try XCTUnwrap(FounderAccountMigration.pending(base: base)).prepareStorage(account: account, base: base)
        try plan.finish(account: account, base: base)
        XCTAssertNil(try FounderAccountMigration.pending(base: base))
        XCTAssertEqual(try SessionStore(directory: destination, expectedOwner: plan.owner).load().count, 1)
    }

    func testWrongProviderOwnerOrEndpointCannotMoveFiles() throws {
        let (base, plan, account) = try fixture()
        let another = AccountSession(token: account.session.token, refreshToken: account.session.refreshToken,
            owner: UUID().uuidString, expires: account.session.expires, refreshExpires: account.session.refreshExpires)
        for wrong in [StoredAccount(endpoint: account.endpoint, provider: .apple, session: account.session),
                      StoredAccount(endpoint: account.endpoint, provider: .google, session: another),
                      StoredAccount(endpoint: URL(string: "wss://other.example/account")!, provider: .google, session: account.session)] {
            XCTAssertThrowsError(try plan.prepareStorage(account: wrong, base: base))
        }
        XCTAssertTrue(FileManager.default.fileExists(atPath: base.appendingPathComponent("sessions").path))
    }

    func testChangedSourceAndExistingDestinationAreRejected() throws {
        let (base, plan, account) = try fixture()
        let file = base.appendingPathComponent("sessions").appendingPathComponent(plan.sessions.keys.first!)
        let original = try Data(contentsOf: file)
        try Data("changed".utf8).write(to: file)
        XCTAssertThrowsError(try plan.prepareStorage(account: account, base: base))
        try original.write(to: file)
        let target = base.appendingPathComponent("accounts").appendingPathComponent(plan.owner).appendingPathComponent("sessions")
        try FileManager.default.createDirectory(at: target, withIntermediateDirectories: true)
        XCTAssertThrowsError(try plan.prepareStorage(account: account, base: base))
        XCTAssertEqual(try Data(contentsOf: file), original)
    }

    func testUnplannedOutboxAndDeletionBarrierAreRejected() throws {
        let (base, plan, account) = try fixture()
        let directory = base.appendingPathComponent("memory-outbox").appendingPathComponent(plan.owner)
        let extra = directory.appendingPathComponent("new.json")
        try Data("{}".utf8).write(to: extra)
        XCTAssertThrowsError(try plan.prepareStorage(account: account, base: base))
        try FileManager.default.removeItem(at: extra)
        try Data().write(to: directory.appendingPathComponent(LocalAccountErasure.marker))
        XCTAssertThrowsError(try plan.prepareStorage(account: account, base: base))
    }

    func testOrdinarySignInHasNoMigrationAndSymlinkCannotRedirectMove() throws {
        let (base, plan, account) = try fixture()
        let marker = base.appendingPathComponent(FounderAccountMigration.filename)
        try FileManager.default.removeItem(at: marker)
        XCTAssertNil(try FounderAccountMigration.pending(base: base))
        XCTAssertThrowsError(try plan.prepareStorage(account: account, base: base))
        try JSONEncoder().encode(plan).write(to: marker)
        let redirect = base.appendingPathComponent("redirect")
        try FileManager.default.createDirectory(at: redirect, withIntermediateDirectories: true)
        try FileManager.default.createSymbolicLink(at: base.appendingPathComponent("accounts"), withDestinationURL: redirect)
        XCTAssertThrowsError(try plan.prepareStorage(account: account, base: base))
    }
    func testPrivatePhysicalSnapshotWhenExplicitlyProvided() throws {
        guard let path = ProcessInfo.processInfo.environment["ELLIS_MIGRATION_SNAPSHOT"] else {
            throw XCTSkip("Private physical snapshot supplied only for explicit rehearsal")
        }
        let source = URL(fileURLWithPath: path).resolvingSymlinksInPath()
        let base = FileManager.default.temporaryDirectory.resolvingSymlinksInPath().appendingPathComponent(UUID().uuidString)
        try FileManager.default.copyItem(at: source, to: base)
        addTeardownBlock { try FileManager.default.removeItem(at: base) }
        let sessions = try SessionStore(directory: base.appendingPathComponent("sessions")).load()
        let owner = try XCTUnwrap(sessions.first?.memoryOwnerID)
        XCTAssertEqual(sessions.count, 4)
        XCTAssertTrue(sessions.allSatisfy { $0.memoryOwnerID == owner })
        func hashes(_ directory: URL) throws -> [String: String] {
            try Dictionary(uniqueKeysWithValues: FileManager.default.contentsOfDirectory(at: directory, includingPropertiesForKeys: nil).map {
                ($0.lastPathComponent, SHA256.hash(data: try Data(contentsOf: $0)).map { String(format: "%02x", $0) }.joined())
            })
        }
        let endpoint = URL(string: "wss://example.com/account")!
        let originalHashes = try hashes(base.appendingPathComponent("sessions"))
        let outbox = base.appendingPathComponent("memory-outbox").appendingPathComponent(owner)
        let outboxHashes = try hashes(outbox)
        XCTAssertEqual(outboxHashes.count, 20)
        let plan = FounderAccountMigration(version: 1, owner: owner, endpoint: endpoint, sessions: originalHashes, outbox: outboxHashes)
        try JSONEncoder().encode(plan).write(to: base.appendingPathComponent(FounderAccountMigration.filename))
        let account = StoredAccount(endpoint: endpoint, provider: .google,
            session: AccountSession(token: String(repeating: "a", count: 43), refreshToken: String(repeating: "r", count: 64),
                owner: owner, expires: Date.now.timeIntervalSince1970 + 3600, refreshExpires: Date.now.timeIntervalSince1970 + 86400))
        try plan.prepareStorage(account: account, base: base)
        try XCTUnwrap(FounderAccountMigration.pending(base: base)).prepareStorage(account: account, base: base)
        try plan.finish(account: account, base: base)
        XCTAssertEqual(try hashes(base.appendingPathComponent("accounts").appendingPathComponent(owner).appendingPathComponent("sessions")), originalHashes)
        XCTAssertEqual(try hashes(outbox), outboxHashes)
        XCTAssertEqual(try hashes(source.appendingPathComponent("sessions")), originalHashes)
        XCTAssertNil(try FounderAccountMigration.pending(base: base))
    }

}
