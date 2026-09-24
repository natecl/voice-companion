import Foundation

extension SessionController {
    static func forApp() -> SessionController {
        #if DEBUG
        let arguments = ProcessInfo.processInfo.arguments
        if arguments.contains("--ui-testing"), arguments.contains("--recording-ui-fixture") {
            let controller = SessionController(makeConnection: { RecordingUIFixture() }, prepareRecording: {})
            controller.recordingLimit = .seconds(6)
            return controller
        }
        #endif
        return SessionController()
    }
}

#if DEBUG
/// Exercises recording presentation through the real controller/store, without audio or network.
@MainActor
private final class RecordingUIFixture: RecordingConnection {
    private var stopped = false
    private var cancelled = false

    func run(onReady: (Duration) -> Void, onFinishing: @escaping (RecordingStopReason) -> Void,
             onEvent: (GrokEvent) throws -> Void) async throws {
        onReady(.seconds(6))
        try onEvent(JSONDecoder().decode(GrokEvent.self, from: Data(
            "{\"type\":\"transcript.partial\",\"text\":\"Simulated recording for UI verification. Microphone off.\",\"start\":0,\"duration\":1}".utf8)))
        let started = ContinuousClock.now
        while !stopped && started.duration(to: .now) < .seconds(6) {
            try await Task.sleep(for: .milliseconds(100))
        }
        try Task.checkCancellation()
        if cancelled { throw CancellationError() }
        onFinishing(stopped ? .user : .developmentLimit)
    }
    func stop() { stopped = true }
    func cancel() { cancelled = true; stopped = true }
}
#endif
