import Foundation

extension SessionController {
    static func forApp() -> SessionController {
        #if DEBUG
        let arguments = ProcessInfo.processInfo.arguments
        if arguments.contains("--ui-testing"), (arguments.contains("--recording-ui-fixture") || arguments.contains("--long-transcript-ui-fixture")) {
            let longTranscript = arguments.contains("--long-transcript-ui-fixture")
            let controller = SessionController(makeConnection: { RecordingUIFixture(longTranscript: longTranscript) }, prepareRecording: {})
            controller.recordingLimit = longTranscript ? LiveTranscriber.recordingLimit : .seconds(6)
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
    private let longTranscript: Bool
    init(longTranscript: Bool) { self.longTranscript = longTranscript }
    private var stopped = false
    private var cancelled = false

    func run(onReady: (Duration) -> Void, onFinishing: @escaping (RecordingStopReason) -> Void,
             onEvent: (GrokEvent) throws -> Void) async throws {
        let limit = longTranscript ? LiveTranscriber.recordingLimit : .seconds(6)
        onReady(limit)
        if longTranscript {
            // Accelerated five-minute transcript volume, not five minutes of captured audio.
            for turn in 0..<60 {
                let text = "Simulated turn \(turn + 1). This is fixture text for checking a growing conversation."
                let words = text.split(separator: " ").enumerated().map { index, word in
                    TranscriptWord(text: String(word), start: Double(turn * 5) + Double(index) * 0.3,
                                   end: Double(turn * 5) + Double(index + 1) * 0.3, speaker: turn % 2)
                }
                try onEvent(GrokEvent(type: "transcript.partial", text: text, words: words,
                                     start: Double(turn * 5), duration: 5, is_final: true))
                try await Task.sleep(for: .milliseconds(10))
            }
        } else {
            try onEvent(JSONDecoder().decode(GrokEvent.self, from: Data(
            "{\"type\":\"transcript.partial\",\"text\":\"Simulated recording for UI verification. Microphone off.\",\"start\":0,\"duration\":1}".utf8)))
        }
        let started = ContinuousClock.now
        while !stopped && started.duration(to: .now) < limit {
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
