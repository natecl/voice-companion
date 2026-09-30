import XCTest

private actor DeletionServiceFixture: AccountDeleting {
    var calls = 0
    var fail = false
    var held = false
    var continuation: CheckedContinuation<Void, Error>?
    func deleteAccount(_ refreshToken: String) async throws {
        calls += 1
        if held { return try await withCheckedThrowingContinuation { continuation = $0 } }
        if fail { throw AccountFailure.unavailable }
    }
    func resumeDeletion(_ deletionToken: String) async throws { try await deleteAccount(deletionToken) }
    func hold() { held = true }
    func setFailure(_ value: Bool) { fail = value }
    func waitForCall() async { while calls == 0 { await Task.yield() } }
    func release() { continuation?.resume(); continuation = nil }
}

@MainActor
final class AccountDeletionTests: XCTestCase {
    private func account(owner: String = UUID().uuidString) -> StoredAccount {
        StoredAccount(endpoint: URL(string: "wss://example.com/account")!, provider: .google,
                      session: AccountSession(token: String(repeating: "a", count: 43), refreshToken: String(repeating: "r", count: 64),
                          owner: owner, expires: Date.now.timeIntervalSince1970 + 3600, refreshExpires: Date.now.timeIntervalSince1970 + 86400))
    }

    func testPreparationSavesPendingBeforeDroppingAccess() async throws {
        let value = account()
        let manager = AccountSessionManager(account: value, save: { _ in }, clear: {})
        do {
            _ = try await manager.prepareDeletion(savePending: { _ in throw AccountFailure.unavailable })
            XCTFail("Ignored pending-store failure")
        } catch {}
        let stillActive = try await manager.current()
        XCTAssertEqual(stillActive.session.owner, value.session.owner)
        let pending = try await manager.prepareDeletion(savePending: { try $0.validate() })
        XCTAssertEqual(pending.owner, value.session.owner)
        do { _ = try await manager.current(); XCTFail("Kept content access") } catch {}
        let restored = try JSONDecoder().decode(PendingAccountDeletion.self, from: JSONEncoder().encode(pending))
        XCTAssertEqual(restored, pending)
    }

    func testServerFailurePreservesPendingAndNeverErasesLocalData() async throws {
        let original = PendingAccountDeletion(account: account())
        var saved: PendingAccountDeletion? = original
        let service = DeletionServiceFixture()
        await service.setFailure(true)
        let controller = AccountDeletionController(load: { saved }, save: { saved = $0 },
            complete: { _ in XCTFail("Completed failed deletion") }, erase: { _ in XCTFail("Erased before server completion") }, transport: { _ in service })
        do { try await controller.finish(original); XCTFail("Ignored server failure") } catch {}
        XCTAssertEqual(saved, original)
    }

    func testLocalFailureRetriesAfterRelaunchWithoutAnotherServerCall() async throws {
        let original = PendingAccountDeletion(account: account())
        var saved: PendingAccountDeletion? = original
        let service = DeletionServiceFixture()
        var erased: [String] = []
        let first = AccountDeletionController(load: { saved }, save: { saved = $0 },
            complete: { _ in XCTFail("Completed failed cleanup") }, erase: { _ in throw AccountFailure.unavailable }, transport: { _ in service })
        do { try await first.finish(original); XCTFail("Ignored local failure") } catch {}
        XCTAssertEqual(saved?.serverDeleted, true)
        let reopened = AccountDeletionController(load: { saved }, save: { saved = $0 }, complete: { id in
            XCTAssertEqual(id, saved?.id); saved = nil
        }, erase: { erased.append($0) }, transport: { _ in service })
        try await reopened.finish(original)
        XCTAssertNil(saved)
        XCTAssertEqual(erased, [original.owner])
        let calls = await service.calls
        XCTAssertEqual(calls, 1)
    }

    func testLateCompletionCannotClearReplacementReceipt() async throws {
        let original = PendingAccountDeletion(account: account())
        let replacement = PendingAccountDeletion(account: account())
        var saved: PendingAccountDeletion? = original
        let service = DeletionServiceFixture()
        await service.hold()
        let controller = AccountDeletionController(load: { saved }, save: { saved = $0 },
            complete: { _ in XCTFail("Cleared replacement state") }, erase: { _ in XCTFail("Erased replacement owner") }, transport: { _ in service })
        let task = Task { try await controller.finish(original) }
        await service.waitForCall()
        saved = replacement
        await service.release()
        do { try await task.value; XCTFail("Applied stale completion") } catch {}
        XCTAssertEqual(saved, replacement)
    }

    func testLocalErasurePreservesOtherOwnerAndLegacyAndBlocksLateWrites() throws {
        let base = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: base) }
        let cache = RecordingNotesCache(directory: base.appendingPathComponent("cache"))
        let owner = UUID().uuidString, other = UUID().uuidString
        let stores = [owner, other].map { SessionStore(directory: base.appendingPathComponent("accounts").appendingPathComponent($0).appendingPathComponent("sessions"), expectedOwner: $0) }
        let boxes = [owner, other].map { MemoryOutbox(directory: base.appendingPathComponent("memory-outbox").appendingPathComponent($0), owner: $0) }
        let note = RecordingNotesResult(revision: 1, generation_version: "fixture-v1", state: "ready", incomplete: false,
            notes: .init(title: "Fictional note", overview: .init(text: "Fictional context", passages: ["p1"]), sections: []), error: nil)
        var sessions: [CaptureSession] = []
        for (index, id) in [owner, other].enumerated() {
            var session = CaptureSession(id: UUID(), createdAt: .now)
            session.memoryOwnerID = id; session.memoryTerminal = true
            try stores[index].save(session); try boxes[index].stage(session); sessions.append(session)
            try cache.store(note, for: .init(owner: id, sessionID: session.id.uuidString, revision: 1))
        }
        let legacy = SessionStore(directory: base.appendingPathComponent("sessions"))
        let legacySession = CaptureSession(id: UUID(), createdAt: .now)
        try legacy.save(legacySession)
        try LocalAccountErasure.erase(owner: owner, base: base, cache: cache)
        try LocalAccountErasure.erase(owner: owner, base: base, cache: cache)
        XCTAssertTrue(try stores[0].load().isEmpty)
        XCTAssertTrue(try boxes[0].entries().isEmpty)
        XCTAssertEqual(try stores[1].load().first?.id, sessions[1].id)
        XCTAssertEqual(try legacy.load().first?.id, legacySession.id)
        XCTAssertThrowsError(try stores[0].save(sessions[0]))
        XCTAssertThrowsError(try boxes[0].stage(sessions[0]))
        let reopened = RecordingNotesCache(directory: base.appendingPathComponent("cache"))
        let deletedKey = RecordingNotesCache.Key(owner: owner, sessionID: sessions[0].id.uuidString, revision: 1)
        XCTAssertThrowsError(try reopened.store(note, for: deletedKey))
        XCTAssertEqual(try reopened.read(.init(owner: other, sessionID: sessions[1].id.uuidString, revision: 1))?.notes?.title, "Fictional note")
        try reopened.clearAll()
        XCTAssertThrowsError(try reopened.store(note, for: deletedKey))
    }

    func testInvalidOwnerAndOwnerSymlinkCannotDeleteOtherFiles() throws {
        let base = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: base) }
        let other = base.appendingPathComponent("other")
        try FileManager.default.createDirectory(at: other, withIntermediateDirectories: true)
        let file = other.appendingPathComponent("keep.txt")
        try Data("preserve".utf8).write(to: file)
        let cache = RecordingNotesCache(directory: base.appendingPathComponent("cache"))
        XCTAssertThrowsError(try LocalAccountErasure.erase(owner: "../other", base: base, cache: cache))
        let owner = UUID().uuidString
        let accounts = base.appendingPathComponent("accounts")
        try FileManager.default.createDirectory(at: accounts, withIntermediateDirectories: true)
        try FileManager.default.createSymbolicLink(at: accounts.appendingPathComponent(owner), withDestinationURL: other)
        XCTAssertThrowsError(try LocalAccountErasure.erase(owner: owner, base: base, cache: cache))
        XCTAssertEqual(try String(contentsOf: file, encoding: .utf8), "preserve")
    }
}
