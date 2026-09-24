import XCTest

@MainActor
private final class FixtureAudio: AudioCapture {
    var started = false
    var stopped = false
    private var continuation: AsyncThrowingStream<Data, Error>.Continuation?
    func start() throws -> AsyncThrowingStream<Data, Error> {
        started = true
        let (stream, continuation) = AsyncThrowingStream<Data, Error>.makeStream()
        self.continuation = continuation
        continuation.yield(Data(repeating: 0, count: 3200))
        return stream
    }
    func fail() { continuation?.finish(throwing: CaptureFailure.overflow) }
    func stop() { stopped = true; continuation?.finish(); continuation = nil }
}

/// Real URLSession WebSockets and the real controller/store; synthetic PCM, no microphone/API.
@MainActor
final class TransportFailureTests: XCTestCase {
    private func waitUntil(_ predicate: () -> Bool) async throws {
        for _ in 0..<500 {
            if predicate() { return }
            try await Task.sleep(for: .milliseconds(10))
        }
        throw NSError(domain: "FixtureTimeout", code: 1)
    }

    private func exercise(_ mode: String, action: String? = nil) async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let portFile = directory.appendingPathComponent("port")
        let reportFile = directory.appendingPathComponent("report.json")
        let fixture = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("Backend/transport_fixture.py")
        let process = Process()
        let python = ProcessInfo.processInfo.environment["VOICE_TEST_PYTHON"] ?? "/usr/bin/env"
        process.executableURL = URL(fileURLWithPath: python)
        process.arguments = (python == "/usr/bin/env" ? ["python3"] : []) + [fixture.path, portFile.path, reportFile.path]
        process.standardOutput = FileHandle.nullDevice
        process.standardError = FileHandle.standardError
        try process.run()
        defer { if process.isRunning { process.terminate() }; process.waitUntilExit() }
        try await waitUntil { FileManager.default.fileExists(atPath: portFile.path) || !process.isRunning }
        guard process.isRunning else {
            throw NSError(domain: "TransportFixture", code: 1, userInfo: [NSLocalizedDescriptionKey:
                "The local Python fixture exited before startup. Install Backend/requirements.txt and set TEST_RUNNER_VOICE_TEST_PYTHON to that Python executable."])
        }
        let port = try String(contentsOf: portFile, encoding: .utf8)
        let audio = FixtureAudio()
        let config = RelayConfiguration(url: URL(string: "ws://127.0.0.1:\(port)/\(mode)")!, token: "local-fixture", rootCertificate: nil)
        let connection = LiveTranscriber(microphone: audio, configuration: { config },
                                        timeouts: .init(ready: .seconds(1), recording: .seconds(2), finalization: .milliseconds(300)))
        defer { connection.cancel() }
        let store = SessionStore(directory: directory.appendingPathComponent("sessions"))
        let controller = SessionController(store: store, makeConnection: { connection }, prepareRecording: {})
        controller.startRecording()
        if mode == "stop-connecting" {
            try await waitUntil { FileManager.default.fileExists(atPath: reportFile.path) }
            controller.stop()
        } else if action != nil {
            try await waitUntil { controller.current?.transcript.segments.isEmpty == false }
            if action == "audio-failure" { audio.fail() }
            else if action == "cancel" { controller.interrupt(reason: "Fixture cancellation") }
            else { controller.stop() }
        }
        try await waitUntil { !controller.isActive }
        XCTAssertTrue(audio.stopped)
        XCTAssertEqual(audio.started, !["ready-timeout", "stop-connecting", "reject"].contains(mode))
        let saved = try XCTUnwrap(store.load().first)
        XCTAssertEqual(saved.completed, mode == "complete" && (action == "stop" || action == nil))
        if ["drop", "error", "final-timeout", "complete"].contains(mode) {
            XCTAssertEqual(saved.transcript.segments.first?.text, "Preserved fixture words")
        }
        if mode == "ready-timeout" { XCTAssertTrue(saved.endReason?.contains("did not become ready") == true) }
        if mode == "final-timeout" { XCTAssertTrue(saved.endReason?.contains("Final transcription results") == true) }
        if action == "audio-failure" { XCTAssertTrue(saved.endReason?.contains("could not be sent quickly enough") == true) }
        if mode == "complete", action == nil {
            XCTAssertEqual(saved.stopNotice, "Stopped automatically at the development recording limit (2 seconds).")
            XCTAssertGreaterThanOrEqual(try XCTUnwrap(saved.recordingSeconds), 2)
            XCTAssertNil(saved.endReason)
        } else { XCTAssertNil(saved.stopNotice) }
        if !saved.completed { XCTAssertNotNil(saved.endReason) }
        func report() -> [String: Any] {
            guard let data = try? Data(contentsOf: reportFile),
                  let result = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return [:] }
            return result
        }
        try await waitUntil { report()["closed"] as? Bool == true }
        if action == "stop" || (mode == "complete" && action == nil) {
            XCTAssertEqual(report()["audio_done"] as? Bool, true)
        }
        if !audio.started { XCTAssertEqual(report()["audio_bytes"] as? Int, 0) }
    }

    func testRejectedAuthorizationNeverStartsCapture() async throws { try await exercise("reject") }
    func testAudioStreamFailurePreservesItsReasonAndClosesSocket() async throws { try await exercise("complete", action: "audio-failure") }
    func testAbruptNetworkDropPreservesTextAndClosesCapture() async throws { try await exercise("drop") }
    func testProviderErrorPreservesTextAndClosesCapture() async throws { try await exercise("error") }
    func testReadyTimeoutNeverStartsCapture() async throws { try await exercise("ready-timeout") }
    func testStopDuringConnectionNeverStartsCapture() async throws { try await exercise("stop-connecting") }
    func testFinalizationTimeoutPreservesTextAndClosesSocket() async throws { try await exercise("final-timeout", action: "stop") }
    func testUnexpectedCompletionCannotHangWaitingForAudio() async throws { try await exercise("premature") }
    func testExplicitStopSendsDoneAndCompletes() async throws { try await exercise("complete", action: "stop") }
    func testAutoStopSendsDoneAndCompletes() async throws { try await exercise("complete") }
    func testCancellationClosesActiveSocketAndPreservesText() async throws { try await exercise("complete", action: "cancel") }
}
