import XCTest

@MainActor
private final class MemoryFixtureRecording: RecordingConnection {
    func run(onReady: (Duration) -> Void, onFinishing: @escaping (RecordingStopReason) -> Void,
             onEvent: (GrokEvent) throws -> Void) async throws {
        onReady(.seconds(300))
        try onEvent(GrokEvent(type: "transcript.partial", text: "Synthetic appointment Tuesday at ten.", words: [], start: 0, duration: 2, is_final: true))
        try onEvent(GrokEvent(type: "transcript.partial", text: "Unstable words", words: [], start: 3, duration: 1, is_final: false))
        onFinishing(.user)
    }
    func stop() {}
    func cancel() {}
}

@MainActor
private final class OfflineMemory: MemoryTransport {
    var calls = 0
    func send(_ operation: MemoryOperation) async throws { calls += 1; throw MemorySyncFailure.unavailable }
}

@MainActor
final class MemoryTests: XCTestCase {
    private func temporaryDirectory() throws -> URL {
        let url = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: url, withIntermediateDirectories: true)
        addTeardownBlock { try? FileManager.default.removeItem(at: url) }
        return url
    }
    private func waitUntil(_ predicate: () throws -> Bool) async throws {
        for _ in 0..<500 {
            if try predicate() { return }
            try await Task.sleep(for: .milliseconds(10))
        }
        throw MemorySyncFailure.unavailable
    }
    private func tracked(_ owner: String) -> CaptureSession {
        var session = CaptureSession(id: UUID(), createdAt: Date())
        session.memoryOwnerID = owner
        session.memoryTerminal = true
        session.completed = true
        session.captureTimezone = "UTC"
        session.transcript.segments = [TranscriptSegment(start: 0, duration: 1, text: "Synthetic fact", words: [], isFinal: true)]
        return session
    }
    func testOutboxRevisionDeletionWinsAndOwnerIsolation() throws {
        let directory = try temporaryDirectory()
        let box = MemoryOutbox(directory: directory, owner: "owner")
        var session = tracked("owner")
        try box.stage(session)
        let first = try XCTUnwrap(box.entry(session.id.uuidString)).operation
        try box.stage(session)
        XCTAssertEqual(try box.entry(session.id.uuidString)?.operation.source?.revision, 1)
        session.transcript.segments = [TranscriptSegment(start: 0, duration: 1, text: "Correction", words: [], isFinal: true)]
        try box.stage(session)
        try box.acknowledge(first)
        XCTAssertEqual(try box.entry(session.id.uuidString)?.operation.source?.revision, 2)
        XCTAssertFalse(try XCTUnwrap(box.entry(session.id.uuidString)).acknowledged)
        let revised = try XCTUnwrap(box.entry(session.id.uuidString)).operation
        try box.delete(session.id)
        try box.acknowledge(revised)
        try box.stage(session)
        XCTAssertEqual(try box.entry(session.id.uuidString)?.operation.operation, "delete")
        XCTAssertFalse(try XCTUnwrap(box.entry(session.id.uuidString)).acknowledged)
        XCTAssertThrowsError(try MemoryOutbox(directory: directory, owner: "other").entries())
    }
    func testAccountShutdownKeepsOutboxButStopsNetworkWork() async throws {
        let directory = try temporaryDirectory()
        let box = MemoryOutbox(directory: directory, owner: "owner")
        let transport = OfflineMemory()
        let sync = MemorySync(outbox: box, transport: transport)
        sync.shutdown()
        sync.stage(tracked("owner"))
        sync.kick()
        await Task.yield()
        XCTAssertEqual(transport.calls, 0)
        XCTAssertEqual(try box.entries().count, 1)
    }

    func testOfflineRecoveryExcludesLegacyAndKeepsLocalTranscript() async throws {
        let directory = try temporaryDirectory()
        let store = SessionStore(directory: directory.appendingPathComponent("sessions"))
        var legacy = tracked("owner"); legacy.memoryOwnerID = nil
        try store.save(legacy)
        var interrupted = tracked("owner"); interrupted.memoryTerminal = false
        try store.save(interrupted)
        let box = MemoryOutbox(directory: directory.appendingPathComponent("outbox"), owner: "owner")
        let transport = OfflineMemory()
        let sync = MemorySync(outbox: box, transport: transport)
        let controller = SessionController(store: store, memorySync: sync, prepareRecording: {})
        try await waitUntil { sync.lastError != nil }
        XCTAssertEqual(controller.sessions.count, 2)
        XCTAssertEqual(try box.entries().count, 1)
        XCTAssertEqual(transport.calls, 1) // no unbounded retry after failure
        XCTAssertEqual(controller.sessions.first(where: { $0.id == interrupted.id })?.completed, false)
        try box.delete(interrupted.id)
        let relaunched = SessionController(store: store, memorySync: MemorySync(outbox: box, transport: transport), prepareRecording: {})
        XCTAssertEqual(relaunched.sessions.map(\.id), [legacy.id])
    }
    func testOutboxWriteFailureDoesNotRemoveSavedTranscript() throws {
        let directory = try temporaryDirectory()
        let store = SessionStore(directory: directory.appendingPathComponent("sessions"))
        let session = tracked("owner")
        try store.save(session)
        let blocked = directory.appendingPathComponent("blocked")
        try Data("not a directory".utf8).write(to: blocked)
        let box = MemoryOutbox(directory: blocked, owner: "owner")
        XCTAssertThrowsError(try box.stage(session))
        XCTAssertEqual(try store.load().first?.transcript.segments.first?.text, "Synthetic fact")
    }
    func testFailedStartDoesNotRewritePreviouslySavedMemorySource() async throws {
        let directory = try temporaryDirectory()
        let store = SessionStore(directory: directory.appendingPathComponent("sessions"))
        let saved = tracked("owner")
        try store.save(saved)
        let box = MemoryOutbox(directory: directory.appendingPathComponent("outbox"), owner: "owner")
        let sync = MemorySync(outbox: box, transport: OfflineMemory())
        let controller = SessionController(store: store, memorySync: sync, prepareRecording: { throw CaptureFailure.permissionDenied })
        controller.current = saved
        controller.startRecording()
        try await waitUntil { !controller.isActive }
        XCTAssertEqual(controller.current?.completed, true)
        XCTAssertNil(controller.current?.endReason)
        XCTAssertEqual(try box.entry(saved.id.uuidString)?.operation.source?.revision, 1)
        XCTAssertEqual(try store.load().first?.completed, true)
    }
    func testPersonalNoteOfflineSaveRecoveryAndValidation() async throws {
        let directory = try temporaryDirectory()
        let store = SessionStore(directory: directory.appendingPathComponent("sessions"))
        let box = MemoryOutbox(directory: directory.appendingPathComponent("outbox"), owner: "owner")
        let transport = OfflineMemory()
        let sync = MemorySync(outbox: box, transport: transport)
        let controller = SessionController(store: store, memorySync: sync)
        XCTAssertFalse(controller.savePersonalNote("   "))
        XCTAssertFalse(controller.savePersonalNote(String(repeating: "a", count: 8001)))
        XCTAssertTrue(controller.savePersonalNote("My daughter Maya enjoys swimming."))
        let id = try XCTUnwrap(controller.current?.id)
        try await waitUntil { sync.lastError != nil }
        let entry = try XCTUnwrap(box.entry(id.uuidString))
        XCTAssertEqual(entry.operation.version, 2)
        XCTAssertEqual(entry.operation.source?.origin, "personal_text")
        XCTAssertEqual(entry.operation.source?.passages.first?.speakers, [])
        XCTAssertFalse(entry.acknowledged)
        XCTAssertEqual(transport.calls, 1)
        XCTAssertTrue(controller.personalNoteSyncStatus?.contains("Saved on this device") == true)
        let next = SessionController(store: store, memorySync: MemorySync(outbox: box, transport: transport))
        XCTAssertEqual(next.sessions.first?.source, "personal_text")
        XCTAssertEqual(next.sessions.first?.transcript.segments.first?.text, "My daughter Maya enjoys swimming.")
        next.current = next.sessions.first
        next.deleteCurrent()
        XCTAssertTrue(try store.load().isEmpty)
        XCTAssertEqual(try box.entry(id.uuidString)?.operation.operation, "delete")
    }

    func testLibraryDeletionPreservesActiveCaptureAndRequiresAcknowledgedAttachment() throws {
        let directory = try temporaryDirectory()
        let store = SessionStore(directory: directory.appendingPathComponent("sessions"))
        let past = tracked("owner")
        let active = tracked("owner")
        try store.save(past); try store.save(active)
        let box = MemoryOutbox(directory: directory.appendingPathComponent("outbox"), owner: "owner")
        let controller = SessionController(store: store, memorySync: MemorySync(outbox: box, transport: OfflineMemory()), prepareRecording: {})
        XCTAssertNil(controller.companionAttachment(for: past))
        let upload = try XCTUnwrap(box.entry(past.id.uuidString)).operation
        try box.acknowledge(upload)
        XCTAssertEqual(controller.companionAttachment(for: past)?.revision, 1)
        controller.current = active
        controller.liveStatus = "Recording"
        XCTAssertFalse(controller.deleteFromLibrary(active))
        XCTAssertTrue(controller.deleteFromLibrary(past))
        XCTAssertEqual(controller.current?.id, active.id)
        XCTAssertEqual(controller.liveStatus, "Recording")
        XCTAssertTrue(controller.pendingMemoryDeletion)
        XCTAssertEqual(try store.load().map(\.id), [active.id])
        XCTAssertNil(controller.companionAttachment(for: past))
    }

    func testRealSocketControllerSaveRestartAndDelete() async throws {
        let directory = try temporaryDirectory()
        let fixture = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("Backend/memory_fixture.py")
        let configFile = directory.appendingPathComponent("config.json")
        func launch() throws -> Process {
            try? FileManager.default.removeItem(at: configFile)
            let process = Process()
            let python = ProcessInfo.processInfo.environment["VOICE_TEST_PYTHON"] ?? "/usr/bin/env"
            process.executableURL = URL(fileURLWithPath: python)
            process.arguments = (python == "/usr/bin/env" ? ["python3"] : []) + [fixture.path, directory.path]
            process.standardOutput = FileHandle.nullDevice
            process.standardError = FileHandle.standardError
            try process.run()
            return process
        }
        var process = try launch()
        defer { if process.isRunning { process.terminate() }; process.waitUntilExit() }
        try await waitUntil { FileManager.default.fileExists(atPath: configFile.path) || !process.isRunning }
        XCTAssertTrue(process.isRunning)
        let config = try JSONDecoder().decode(RelayConfiguration.self, from: Data(contentsOf: configFile))
        let owner = try XCTUnwrap(config.memoryOwnerID)
        let box = MemoryOutbox(directory: directory.appendingPathComponent("outbox"), owner: owner)
        let sync = MemorySync(outbox: box, transport: MemorySocketTransport(configuration: { config }))
        let store = SessionStore(directory: directory.appendingPathComponent("sessions"))
        let controller = SessionController(store: store, memorySync: sync, makeConnection: { MemoryFixtureRecording() }, prepareRecording: {})
        controller.startRecording()
        try await waitUntil { !controller.isActive }
        let id = try XCTUnwrap(controller.current?.id)
        try await waitUntil { try box.entry(id.uuidString)?.acknowledged == true }
        let entry = try XCTUnwrap(box.entry(id.uuidString))
        XCTAssertEqual(entry.operation.source?.passages.count, 1)
        XCTAssertEqual(entry.operation.source?.completed, false)
        XCTAssertEqual(try store.load().first?.transcript.segments.count, 2)
        let reportFile = directory.appendingPathComponent("report.json")
        try await waitUntil { FileManager.default.fileExists(atPath: reportFile.path) }
        let report = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: reportFile)) as? [String: Any])
        XCTAssertEqual((report["sources"] as? [[String: Any]])?.first?["revision"] as? Int, 1)
        XCTAssertEqual((report["usage"] as? [Any])?.count, 0)
        process.terminate(); process.waitUntilExit()
        process = try launch()
        try await waitUntil { FileManager.default.fileExists(atPath: configFile.path) || !process.isRunning }
        let restarted = try JSONDecoder().decode(RelayConfiguration.self, from: Data(contentsOf: configFile))
        XCTAssertEqual(restarted.memoryOwnerID, owner)
        let nextSync = MemorySync(outbox: box, transport: MemorySocketTransport(configuration: { restarted }))
        let relaunched = SessionController(store: store, memorySync: nextSync, prepareRecording: {})
        XCTAssertEqual(relaunched.sessions.first?.id, id)
        relaunched.current = relaunched.sessions.first
        relaunched.deleteCurrent()
        try await waitUntil { try box.entry(id.uuidString)?.acknowledged == true && box.entry(id.uuidString)?.operation.operation == "delete" }
        XCTAssertTrue(try store.load().isEmpty)
        try await waitUntil {
            let report = try JSONSerialization.jsonObject(with: Data(contentsOf: reportFile)) as? [String: Any]
            return (report?["sources"] as? [[String: Any]])?.first?["deleted"] as? Int == 1
        }
    }
}
