import XCTest

@MainActor
private final class ControlledConnection: RecordingConnection {
    var started = false
    var stopped = false
    var cancelled = false
    var finish: CheckedContinuation<Void, Error>?
    var finishing: (() -> Void)?

    func run(onReady: () -> Void, onFinishing: @escaping () -> Void,
             onEvent: (GrokEvent) throws -> Void) async throws {
        started = true
        onReady()
        // The fixture is delivered through the real controller reducer and disk store.
        try onEvent(JSONDecoder().decode(GrokEvent.self, from: Data(
            "{\"type\":\"transcript.partial\",\"text\":\"Received words\",\"start\":0,\"duration\":1}".utf8)))
        finishing = onFinishing
        try await withCheckedThrowingContinuation { finish = $0 }
    }
    func stop() { stopped = true; finishing?(); finish?.resume(); finish = nil }
    func cancel() { cancelled = true; finish?.resume(throwing: CancellationError()); finish = nil }
    func fail() { finish?.resume(throwing: CaptureFailure.connectionEnded); finish = nil }
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
    private func withController(_ body: (SessionController, ControlledConnection, SessionStore) async throws -> Void) async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = SessionStore(directory: directory)
        let connection = ControlledConnection()
        let controller = SessionController(store: store, makeConnection: { connection }, prepareRecording: {})
        try await body(controller, connection, store)
    }
    func testBackgroundPersistsBeforeCancellationAndSurvivesReload() async throws {
        try await withController { controller, connection, store in
            controller.startRecording()
            await waitUntil { connection.finish != nil }
            controller.interrupt(reason: "App left foreground")
            XCTAssertTrue(connection.cancelled)
            let immediate = try XCTUnwrap(store.load().first)
            XCTAssertFalse(immediate.completed)
            XCTAssertEqual(immediate.endReason, "App left foreground")
            XCTAssertEqual(immediate.transcript.segments.first?.text, "Received words")
            await waitUntil { !controller.isActive }
            let reopened = SessionController(store: store)
            XCTAssertEqual(reopened.sessions.first?.endReason, "App left foreground")
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
            XCTAssertTrue(try XCTUnwrap(store.load().first).completed)
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
