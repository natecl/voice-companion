import XCTest

@MainActor
private final class ControlledConnection: RecordingConnection {
    var started = false
    var stopped = false
    var cancelled = false
    var finish: CheckedContinuation<Void, Error>?
    var finishing: ((RecordingStopReason) -> Void)?

    func run(onReady: (Duration) -> Void, onFinishing: @escaping (RecordingStopReason) -> Void,
             onEvent: (GrokEvent) throws -> Void) async throws {
        started = true
        onReady(.seconds(55))
        // The fixture is delivered through the real controller reducer and disk store.
        try onEvent(JSONDecoder().decode(GrokEvent.self, from: Data(
            "{\"type\":\"transcript.partial\",\"text\":\"Received words\",\"start\":0,\"duration\":1}".utf8)))
        finishing = onFinishing
        try await withCheckedThrowingContinuation { finish = $0 }
    }
    func stop() { stopped = true; finishing?(.user); finish?.resume(); finish = nil }
    func cancel() { cancelled = true; finish?.resume(throwing: CancellationError()); finish = nil }
    func fail() { finish?.resume(throwing: CaptureFailure.connectionEnded); finish = nil }
}


/// Delivers a receive that was already in flight when cancellation occurred.
/// The callback remains within run's lifetime; no escaping callback trickery.
@MainActor
private final class LateAccountRecording: RecordingConnection {
    var waiting: CheckedContinuation<Void, Never>?
    var cancelled = false
    func run(onReady: (Duration) -> Void, onFinishing: @escaping (RecordingStopReason) -> Void,
             onEvent: (GrokEvent) throws -> Void) async throws {
        onReady(.seconds(300))
        try onEvent(GrokEvent(type: "transcript.partial", text: "Before sign-out", words: [],
                             start: 0, duration: 1, is_final: true))
        await withCheckedContinuation { waiting = $0 }
        // Model an already-delivered receive resuming despite task cancellation.
        try onEvent(GrokEvent(type: "transcript.partial", text: "Late private words", words: [],
                             start: 2, duration: 1, is_final: true))
        throw CancellationError()
    }
    func stop() { release() }
    func cancel() { cancelled = true }
    func release() { waiting?.resume(); waiting = nil }
}

@MainActor
private final class CaptureIsolationMemory: MemoryTransport {
    var operations: [MemoryOperation] = []
    func send(_ operation: MemoryOperation) async throws { operations.append(operation) }
}

@MainActor
final class RecordingLifecycleTests: XCTestCase {
    private func waitUntil(_ predicate: () -> Bool) async {
        for _ in 0..<200 {
            if predicate() { return }
            try? await Task.sleep(for: .milliseconds(5))
        }
        XCTFail("Recording state did not settle")
    }
    private func withController(background: Bool = false, _ body: (SessionController, ControlledConnection, SessionStore) async throws -> Void) async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = SessionStore(directory: directory)
        let connection = ControlledConnection()
        let controller = SessionController(store: store, allowsBackgroundRecording: background, makeConnection: { connection }, prepareRecording: {})
        try await body(controller, connection, store)
    }
    func testSignOutDuringCaptureRejectsLateEventsAndPreservesOwnerStorage() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let ownerA = UUID().uuidString, ownerB = UUID().uuidString
        let pathA = directory.appendingPathComponent(ownerA)
        let pathB = directory.appendingPathComponent(ownerB)
        let storeA = SessionStore(directory: pathA.appendingPathComponent("sessions"), expectedOwner: ownerA)
        let storeB = SessionStore(directory: pathB.appendingPathComponent("sessions"), expectedOwner: ownerB)
        let boxA = MemoryOutbox(directory: pathA.appendingPathComponent("outbox"), owner: ownerA)
        let boxB = MemoryOutbox(directory: pathB.appendingPathComponent("outbox"), owner: ownerB)
        let transportA = CaptureIsolationMemory(), transportB = CaptureIsolationMemory()
        let connection = LateAccountRecording()
        defer { connection.release() }
        let controllerA = SessionController(store: storeA,
            memorySync: MemorySync(outbox: boxA, transport: transportA),
            makeConnection: { connection }, prepareRecording: {})
        controllerA.startRecording()
        await waitUntil { connection.waiting != nil }
        XCTAssertEqual(try storeA.load().first?.transcript.segments.map(\.text), ["Before sign-out"])
        controllerA.endAccountSession()
        XCTAssertTrue(connection.cancelled)
        let interrupted = try XCTUnwrap(storeA.load().first)
        XCTAssertEqual(interrupted.memoryOwnerID, ownerA)
        XCTAssertFalse(interrupted.completed)
        XCTAssertTrue(interrupted.endReason?.contains("signed out") == true)
        let controllerB = SessionController(store: storeB,
            memorySync: MemorySync(outbox: boxB, transport: transportB), prepareRecording: {})
        connection.release()
        await waitUntil { !controllerA.isActive }
        let saved = try XCTUnwrap(storeA.load().first)
        XCTAssertEqual(saved.transcript.segments.map(\.text), interrupted.transcript.segments.map(\.text), "An in-flight event after sign-out must not change saved owner content")
        XCTAssertEqual(saved.memoryOwnerID, ownerA)
        XCTAssertEqual(saved.endReason, interrupted.endReason)
        XCTAssertFalse(saved.completed)
        XCTAssertEqual(saved.memoryTerminal, true)
        let queued = try XCTUnwrap(boxA.entry(saved.id.uuidString))
        XCTAssertEqual(queued.operation.owner, ownerA)
        XCTAssertFalse(queued.acknowledged)
        XCTAssertFalse(String(decoding: try JSONEncoder().encode(queued), as: UTF8.self).contains("Late private words"))
        XCTAssertTrue(transportA.operations.isEmpty, "Sign-out must stop networking while preserving the interrupted outbox")
        XCTAssertTrue(controllerB.sessions.isEmpty)
        XCTAssertTrue(try storeB.load().isEmpty)
        XCTAssertTrue(try boxB.entries().isEmpty)
        XCTAssertTrue(transportB.operations.isEmpty)
        let reopened = SessionController(store: storeA)
        XCTAssertEqual(reopened.sessions.first?.transcript.segments.map(\.text), ["Before sign-out"])
    }

    func testSignOutDuringPreparationPreservesPreviouslyOpenedOwnerRecording() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let owner = UUID().uuidString
        let store = SessionStore(directory: directory.appendingPathComponent("sessions"), expectedOwner: owner)
        let box = MemoryOutbox(directory: directory.appendingPathComponent("outbox"), owner: owner)
        let transport = CaptureIsolationMemory()
        var previous = CaptureSession(id: UUID(), createdAt: .now, source: "microphone")
        previous.memoryOwnerID = owner; previous.memoryTerminal = true; previous.completed = true
        previous.transcript.segments = [TranscriptSegment(start: 0, duration: 1, text: "Saved owner words", words: [], isFinal: true)]
        try store.save(previous)
        let connection = ControlledConnection()
        var preparing = false
        let sync = MemorySync(outbox: box, transport: transport)
        sync.shutdown() // Preserve constructor recovery locally without a network task.
        let controller = SessionController(store: store, memorySync: sync,
            makeConnection: { connection }, prepareRecording: {
                preparing = true
                try await Task.sleep(for: .seconds(10))
            })
        controller.current = try XCTUnwrap(store.load().first)
        let sessionFile = directory.appendingPathComponent("sessions").appendingPathComponent(previous.id.uuidString + ".json")
        let before = try Data(contentsOf: sessionFile)
        let outboxBefore = try box.entry(previous.id.uuidString)?.operation
        controller.startRecording()
        await waitUntil { preparing }
        controller.endAccountSession()
        await waitUntil { !controller.isActive }
        XCTAssertFalse(connection.started)
        XCTAssertEqual(try store.load().count, 1)
        XCTAssertEqual(try Data(contentsOf: sessionFile), before)
        XCTAssertEqual(try box.entry(previous.id.uuidString)?.operation, outboxBefore)
        XCTAssertTrue(transport.operations.isEmpty)
        XCTAssertEqual(SessionController(store: store).sessions.first?.transcript.segments.map(\.text), ["Saved owner words"])
    }

    func testActiveBackgroundCapturePreservesConnectionUntilExplicitStop() async throws {
        try await withController(background: true) { controller, connection, store in
            controller.startRecording()
            await waitUntil { connection.finish != nil }
            controller.didEnterBackground()
            XCTAssertFalse(connection.cancelled)
            XCTAssertEqual(controller.liveStatus, "Recording")
            XCTAssertEqual(try store.load().first?.transcript.segments.first?.text, "Received words")
            controller.stop()
            await waitUntil { !controller.isActive }
            XCTAssertTrue(connection.stopped)
            XCTAssertEqual(try store.load().first?.completed, true)
        }
    }

    func testBackgroundDuringPreparationCancelsWithoutStartingCapture() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let connection = ControlledConnection()
        let controller = SessionController(store: SessionStore(directory: directory), allowsBackgroundRecording: true,
            makeConnection: { connection }, prepareRecording: { try await Task.sleep(for: .seconds(10)) })
        controller.startRecording()
        controller.didEnterBackground()
        await waitUntil { !controller.isActive }
        XCTAssertFalse(connection.started)
    }

    func testBackgroundDuringPreparationPreservesPreviouslyOpenedRecording() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = SessionStore(directory: directory)
        var previous = CaptureSession(id: UUID(), createdAt: Date(), source: "microphone")
        // Replay saved synthetic provider events through the production reducer before saving.
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
        let events = try JSONDecoder().decode([ReplayEvent].self,
            from: Data(contentsOf: root.appendingPathComponent("Fixtures/transcript-events.json")))
        for item in events {
            if let segment = item.event.segment { previous.transcript.apply(segment) }
        }
        previous.completed = true
        previous.memoryTerminal = true
        previous.recordingSeconds = 12
        try store.save(previous)
        let file = directory.appendingPathComponent(previous.id.uuidString + ".json")
        let before = try Data(contentsOf: file)
        let connection = ControlledConnection()
        var preparing = false
        let controller = SessionController(store: store, allowsBackgroundRecording: true,
            makeConnection: { connection }, prepareRecording: {
                preparing = true
                try await Task.sleep(for: .seconds(10))
            })
        controller.current = try XCTUnwrap(store.load().first)
        controller.startRecording()
        await waitUntil { preparing }
        controller.didEnterBackground()
        XCTAssertEqual(try Data(contentsOf: file), before, "Interruption must not rewrite an older recording")
        await waitUntil { !controller.isActive }
        XCTAssertFalse(connection.started)
        XCTAssertEqual(try store.load().count, 1)
        XCTAssertEqual(try Data(contentsOf: file), before)
        let reopened = SessionController(store: store)
        let saved = try XCTUnwrap(reopened.sessions.first)
        XCTAssertTrue(saved.completed)
        XCTAssertNil(saved.endReason)
        XCTAssertEqual(saved.transcript.segments.map(\.text), previous.transcript.segments.map(\.text))
    }

    func testBackgroundPersistsBeforeCancellationAndSurvivesReload() async throws {
        try await withController { controller, connection, store in
            controller.startRecording()
            await waitUntil { connection.finish != nil }
            controller.didEnterBackground()
            XCTAssertTrue(connection.cancelled)
            let immediate = try XCTUnwrap(store.load().first)
            XCTAssertFalse(immediate.completed)
            XCTAssertTrue(immediate.endReason?.contains("left the foreground") == true)
            XCTAssertEqual(immediate.transcript.segments.first?.text, "Received words")
            await waitUntil { !controller.isActive }
            let reopened = SessionController(store: store)
            XCTAssertEqual(reopened.sessions.first?.endReason, immediate.endReason)
        }
    }
    func testNetworkFailurePreservesTextAndClearsRecording() async throws {
        try await withController { controller, connection, store in
            controller.startRecording()
            await waitUntil { connection.finish != nil }
            connection.fail()
            await waitUntil { !controller.isActive }
            let saved = try XCTUnwrap(store.load().first)
            XCTAssertFalse(saved.completed)
            XCTAssertNotNil(saved.endReason)
            XCTAssertEqual(saved.transcript.segments.first?.text, "Received words")
        }
    }
    func testExplicitStopFinalizesAndSaves() async throws {
        try await withController { controller, connection, store in
            controller.startRecording()
            await waitUntil { connection.finish != nil }
            controller.stop()
            XCTAssertTrue(connection.stopped)
            await waitUntil { !controller.isActive }
            let saved = try XCTUnwrap(store.load().first)
            XCTAssertTrue(saved.completed)
            XCTAssertNil(saved.stopNotice)
            let elapsed = try XCTUnwrap(saved.recordingSeconds)
            XCTAssertGreaterThan(elapsed, 0)
            try await Task.sleep(for: .milliseconds(20))
            XCTAssertEqual(controller.elapsedRecordingSeconds, elapsed)
        }
    }
    func testStopDuringPermissionWaitNeverCreatesConnection() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = SessionStore(directory: directory)
        let connection = ControlledConnection()
        let controller = SessionController(store: store, makeConnection: { connection }, prepareRecording: {
            try await Task.sleep(for: .seconds(10))
        })
        controller.startRecording()
        controller.stop()
        await waitUntil { !controller.isActive }
        XCTAssertFalse(connection.started)
        XCTAssertTrue(try store.load().isEmpty)
    }
    func testDeniedPermissionNeverStartsConnectionOrCreatesSession() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = SessionStore(directory: directory)
        let connection = ControlledConnection()
        let controller = SessionController(store: store, makeConnection: { connection }, prepareRecording: {
            throw NSError(domain: "PermissionDenied", code: 1)
        })
        controller.startRecording()
        await waitUntil { !controller.isActive }
        XCTAssertFalse(connection.started)
        XCTAssertNotNil(controller.errorMessage)
        XCTAssertTrue(try store.load().isEmpty)
    }
}
