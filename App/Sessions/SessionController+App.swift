import Foundation

extension SessionController {
    static func forApp() -> SessionController {
        #if DEBUG
        let arguments = ProcessInfo.processInfo.arguments
        if arguments.contains("--ui-testing"), arguments.contains("--live-ask-ui-fixture") {
            let directory = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("VoiceCompanion-Live-Ask-QA")
            return SessionController(store: SessionStore(directory: directory),
                makeAnswerConnection: { AnswerUIFixture(delay: .seconds(3)) },
                makeConnection: { LiveAskUIRecording() }, prepareRecording: {})
        }
        if arguments.contains("--ui-testing"), arguments.contains("--ask-ui-fixture") {
            let directory = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("VoiceCompanion-Ask-QA")
            let store = SessionStore(directory: directory)
            let controller = SessionController(store: store, makeAnswerConnection: { AnswerUIFixture() })
            if let saved = controller.sessions.first { controller.current = saved }
            else {
                var session = CaptureSession(id: UUID(), createdAt: Date())
                session.completed = true
                session.transcript.segments = [TranscriptSegment(start: 0, duration: 2,
                    text: "The appointment is Tuesday at ten.", words: [], isFinal: true)]
                controller.current = session
            }
            return controller
        }
        if arguments.contains("--ui-testing"), (arguments.contains("--recording-ui-fixture") || arguments.contains("--long-transcript-ui-fixture") || arguments.contains("--empty-recording-ui-fixture")) {
            let longTranscript = arguments.contains("--long-transcript-ui-fixture")
            let emptyTranscript = arguments.contains("--empty-recording-ui-fixture")
            let controller = SessionController(allowsBackgroundRecording: false, makeConnection: { RecordingUIFixture(longTranscript: longTranscript, emptyTranscript: emptyTranscript) }, prepareRecording: {})
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
    private let emptyTranscript: Bool
    init(longTranscript: Bool, emptyTranscript: Bool) {
        self.longTranscript = longTranscript
        self.emptyTranscript = emptyTranscript
    }
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
        } else if !emptyTranscript {
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

#if DEBUG
@MainActor
private final class AnswerUIFixture: AnswerConnection {
    let delay: Duration
    init(delay: Duration = .milliseconds(500)) { self.delay = delay }
    func run(_ question: ConversationQuestion, onEvent: (AnswerEvent) throws -> Void) async throws {
        try onEvent(AnswerEvent(type: "delta", text: "Tuesday at ten"))
        try await Task.sleep(for: delay)
        try Task.checkCancellation()
        try onEvent(AnswerEvent(type: "delta", text: " [[p1]]."))
        try onEvent(AnswerEvent(type: "done", references: ["p1"]))
    }
    func cancel() {}
}

@MainActor
private final class LiveAskUIRecording: RecordingConnection {
    private var stopped = false
    func run(onReady: (Duration) -> Void, onFinishing: @escaping (RecordingStopReason) -> Void,
             onEvent: (GrokEvent) throws -> Void) async throws {
        onReady(.seconds(300))
        try onEvent(GrokEvent(type: "transcript.partial", text: "The appointment is Tuesday at ten.", words: [], start: 0, duration: 2, is_final: false))
        while !stopped { try await Task.sleep(for: .milliseconds(50)) }
        onFinishing(.user)
    }
    func stop() { stopped = true }
    func cancel() { stopped = true }
}
#endif
