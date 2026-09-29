import XCTest

@MainActor
private final class CacheDeletionTransport: MemoryTransport {
    var deleted: [String] = []
    func send(_ operation: MemoryOperation) async throws {
        if operation.operation == "delete" { deleted.append(operation.sessionID) }
    }
}

@MainActor
final class RecordingNotesCacheTests: XCTestCase {
    private func directory() -> URL { FileManager.default.temporaryDirectory.appendingPathComponent("note-cache-tests-" + UUID().uuidString) }
    private func key(_ owner: String = "owner-a", revision: Int = 1) -> RecordingNotesCache.Key {
        .init(owner: owner, sessionID: "recording", revision: revision)
    }
    private func ready(_ title: String = "Saved summary", revision: Int = 1, version: String = "server-v1") -> RecordingNotesResult {
        .init(revision: revision, generation_version: version, state: "ready", incomplete: false,
              notes: .init(title: title, overview: .init(text: "Fictional cache fixture", passages: ["p1"]), sections: []), error: nil)
    }
    func testDiskReopenOfflineOwnerRevisionAndGenerationReplacement() throws {
        let folder = directory(); defer { try? FileManager.default.removeItem(at: folder) }
        let cache = RecordingNotesCache(directory: folder)
        try cache.store(ready(), for: key())
        let reopened = RecordingNotesCache(directory: folder)
        XCTAssertEqual(try reopened.read(key())?.notes?.title, "Saved summary")
        XCTAssertNil(try reopened.read(key("owner-b")))
        try reopened.store(ready("New generation", version: "server-v2"), for: key())
        let relaunched = RecordingNotesCache(directory: folder)
        XCTAssertEqual(try relaunched.read(key())?.generation_version, "server-v2")
        XCTAssertEqual(try relaunched.read(key())?.notes?.title, "New generation")
    }
    func testKnownNewRevisionRemovesOldSummaryAcrossRelaunch() throws {
        let folder = directory(); defer { try? FileManager.default.removeItem(at: folder) }
        let cache = RecordingNotesCache(directory: folder)
        try cache.store(ready(), for: key())
        XCTAssertNil(try cache.read(key(revision: 2)))
        let reopened = RecordingNotesCache(directory: folder)
        XCTAssertNil(try reopened.read(key()))
        try reopened.store(ready("Late old revision"), for: key())
        XCTAssertNil(try reopened.read(key()))
        try reopened.store(ready("Revision two", revision: 2), for: key(revision: 2))
        XCTAssertEqual(try reopened.read(key(revision: 2))?.notes?.title, "Revision two")
    }
    func testFailedAndPendingRefreshPreserveDisk() async throws {
        let folder = directory(); defer { try? FileManager.default.removeItem(at: folder) }
        let cache = RecordingNotesCache(directory: folder); try cache.store(ready(), for: key())
        do { _ = try await cache.refresh(key()) { throw URLError(.notConnectedToInternet) }; XCTFail("Expected offline") } catch {}
        for state in ["pending", "generating", "failed"] {
            _ = try await cache.refresh(key()) { .init(revision: 1, generation_version: "server-v2", state: state, incomplete: false, notes: nil, error: "fixture") }
            XCTAssertEqual(try RecordingNotesCache(directory: folder).read(key())?.notes?.title, "Saved summary")
        }
    }
    func testOutdatedAndMissingSourceInvalidate() async throws {
        let folder = directory(); defer { try? FileManager.default.removeItem(at: folder) }
        let cache = RecordingNotesCache(directory: folder)
        try cache.store(ready(), for: key())
        _ = try await cache.refresh(key()) { .init(revision: 2, generation_version: "server-v2", state: "outdated", incomplete: false, notes: nil, error: nil) }
        XCTAssertNil(try RecordingNotesCache(directory: folder).read(key()))
        try cache.store(ready(revision: 2), for: key(revision: 2))
        _ = try await cache.refresh(key(revision: 2)) { nil }
        XCTAssertNil(try cache.read(key()))
    }
    func testConcurrentReadersCoalesce() async throws {
        let folder = directory(); defer { try? FileManager.default.removeItem(at: folder) }
        let cache = RecordingNotesCache(directory: folder)
        var count = 0
        let sourceKey = key()
        let fixture = ready()
        let load: @MainActor () async throws -> RecordingNotesResult? = {
            count += 1
            try await Task.sleep(for: .milliseconds(40))
            return fixture
        }
        async let first = cache.refresh(sourceKey, load: load)
        async let second = cache.refresh(sourceKey, load: load)
        let values = try await [first, second]
        XCTAssertEqual(count, 1)
        XCTAssertEqual(values.compactMap { $0?.notes?.title }, ["Saved summary", "Saved summary"])
    }
    func testDeletionOwnerClearAndResetPreventLateRepopulation() async throws {
        let folder = directory(); defer { try? FileManager.default.removeItem(at: folder) }
        let cache = RecordingNotesCache(directory: folder)
        for operation in 0..<3 {
            try cache.clear(owner: "owner-a")
            try cache.store(ready(), for: key())
            try cache.store(ready("Other owner"), for: key("owner-b"))
            var continuation: CheckedContinuation<RecordingNotesResult?, Never>?
            let task = Task { try await cache.refresh(key()) { await withCheckedContinuation { continuation = $0 } } }
            while continuation == nil { await Task.yield() }
            switch operation {
            case 0: try cache.invalidate(owner: "owner-a", sessionID: "recording")
            case 1: try cache.clear(owner: "owner-a")
            default: try cache.clearAll()
            }
            continuation?.resume(returning: ready("Late write"))
            do { _ = try await task.value; XCTFail("Expected cancelled late write") } catch is CancellationError {} catch { XCTFail("Unexpected error: \(error)") }
            XCTAssertNil(try RecordingNotesCache(directory: folder).read(key()))
            XCTAssertEqual(try cache.read(key("owner-b"))?.notes?.title, operation == 2 ? nil : "Other owner")
            let files = FileManager.default.enumerator(at: folder, includingPropertiesForKeys: nil)?.allObjects as? [URL] ?? []
            XCTAssertEqual(files.filter { $0.pathExtension == "json" }.count, operation == 2 ? 0 : 1)
        }
    }
    func testExplicitRetryIsNotLostBehindRead() async throws {
        let folder = directory(); defer { try? FileManager.default.removeItem(at: folder) }
        let cache = RecordingNotesCache(directory: folder)
        var continuation: CheckedContinuation<RecordingNotesResult?, Never>?
        let read = Task { try await cache.refresh(key()) { await withCheckedContinuation { continuation = $0 } } }
        while continuation == nil { await Task.yield() }
        var retries = 0
        let retry = Task { try await cache.refresh(key(), retry: true) { retries += 1; return self.ready() } }
        await Task.yield()
        continuation?.resume(returning: .init(revision: 1, generation_version: "v1", state: "failed", incomplete: false, notes: nil, error: "fixture"))
        _ = try await read.value
        let retried = try await retry.value
        XCTAssertEqual(retried?.state, "ready")
        XCTAssertEqual(retries, 1)
    }
    func testControllerDeletionClearsOnlyDeletedRecording() throws {
        let folder = directory(); defer { try? FileManager.default.removeItem(at: folder) }
        let owner = "cache-fixture-" + UUID().uuidString
        defer { try? RecordingNotesCache.shared.clear(owner: owner) }
        let store = SessionStore(directory: folder)
        let controller = SessionController(store: store)
        for useCurrent in [false, true] {
            var session = CaptureSession(id: UUID(), createdAt: Date())
            session.memoryOwnerID = owner
            try store.save(session)
            let sourceKey = RecordingNotesCache.Key(owner: owner, sessionID: session.id.uuidString, revision: 1)
            try RecordingNotesCache.shared.store(ready(), for: sourceKey)
            if useCurrent { controller.current = session; controller.deleteCurrent() }
            else { XCTAssertTrue(controller.deleteFromLibrary(session)) }
            XCTAssertNil(controller.errorMessage)
            XCTAssertNil(try RecordingNotesCache.shared.read(sourceKey))
            XCTAssertTrue(try store.load().isEmpty)
        }
    }

    func testAuthoritativeErrorsPurgeButTransientErrorsPreserve() async throws {
        for code in ["source_unavailable", "stale_notes", "notes_unavailable"] {
            let folder = directory(); defer { try? FileManager.default.removeItem(at: folder) }
            let cache = RecordingNotesCache(directory: folder)
            try cache.store(ready(), for: key())
            let bytes = try JSONSerialization.data(withJSONObject: ["type": "error", "message": code])
            do {
                _ = try await cache.refresh(key()) {
                    try RecordingNotesConnection.decode(bytes, attachment: .init(session_id: "recording", revision: 1))
                }
                XCTFail("Expected service error")
            } catch let failure as RecordingNotesSourceFailure {
                XCTAssertEqual(failure.reason.rawValue, code)
                XCTAssertFalse(failure.cacheRemovalFailed)
            } catch { XCTAssertEqual(code, "notes_unavailable") }
            let reopened = RecordingNotesCache(directory: folder)
            XCTAssertEqual(try reopened.read(key())?.notes?.title, code == "notes_unavailable" ? "Saved summary" : nil)
            if code == "source_unavailable" {
                var loaded = false
                do { _ = try await reopened.refresh(key()) { loaded = true; return self.ready("Obsolete") } } catch {}
                XCTAssertFalse(loaded)
                XCTAssertNil(try reopened.read(key()))
            }
        }
    }
    func testOutdatedDoesNotEraseRevisionHighWater() async throws {
        let folder = directory(); defer { try? FileManager.default.removeItem(at: folder) }
        let cache = RecordingNotesCache(directory: folder)
        try cache.store(ready(), for: key())
        _ = try cache.read(key(revision: 2))
        _ = try await cache.refresh(key(revision: 2)) { .init(revision: 2, generation_version: "v2", state: "outdated", incomplete: false, notes: nil, error: nil) }
        let reopened = RecordingNotesCache(directory: folder)
        var loaded = false
        do { _ = try await reopened.refresh(key()) { loaded = true; return self.ready("Old revision") }; XCTFail("Expected stale rejection") } catch {}
        XCTAssertFalse(loaded)
        XCTAssertNil(try reopened.read(key()))
    }
    func testDeletionCompletesWhenCacheRemovalFails() async throws {
        for useCurrent in [false, true] {
            let folder = directory(); defer { try? FileManager.default.removeItem(at: folder) }
            let store = SessionStore(directory: folder)
            var session = CaptureSession(id: UUID(), createdAt: Date())
            session.memoryOwnerID = "fixture-owner"
            try store.save(session)
            var attempted = false
            let transport = CacheDeletionTransport()
            let sync = MemorySync(outbox: MemoryOutbox(directory: folder.appendingPathComponent("outbox"), owner: "fixture-owner"), transport: transport)
            let controller = SessionController(store: store, invalidateNotes: { _, _ in
                attempted = true; throw CocoaError(.fileWriteNoPermission)
            }, memorySync: sync)
            controller.current = session
            if useCurrent { controller.deleteCurrent() }
            else { XCTAssertTrue(controller.deleteFromLibrary(session)) }
            XCTAssertTrue(attempted)
            XCTAssertNil(controller.current)
            XCTAssertTrue(controller.sessions.isEmpty)
            XCTAssertTrue(try store.load().isEmpty)
            XCTAssertTrue(controller.errorMessage?.hasPrefix("Recording deleted. Saved notes couldn’t be removed") == true)
            for _ in 0..<100 where transport.deleted.isEmpty { try await Task.sleep(for: .milliseconds(10)) }
            XCTAssertEqual(transport.deleted, [session.id.uuidString])
        }
    }

}
