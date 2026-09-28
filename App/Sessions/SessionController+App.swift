import Foundation

extension SessionController {
    static func forApp() -> SessionController {
        #if DEBUG
        let arguments = ProcessInfo.processInfo.arguments
        if arguments.contains("--ui-testing"), (arguments.contains("--memory-ui-fixture") || arguments.contains("--companion-ui-fixture")) {
            // Test handoff must not read another app's private container.
            let fixtureJSON = ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"] ?? ""
            guard let config = try? JSONDecoder().decode(RelayConfiguration.self, from: Data(fixtureJSON.utf8)),
                  config.url.scheme == "ws", config.url.host == "127.0.0.1", config.url.path == "/stt",
                  let owner = config.memoryOwnerID, UUID(uuidString: owner) != nil else {
                let controller = SessionController(prepareRecording: { throw CaptureFailure.noRelay })
                controller.errorMessage = "Local memory fixture configuration is unavailable."
                return controller
            }
            let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("VoiceCompanion-Memory-QA").appendingPathComponent(owner)
            let sync = MemorySync(outbox: MemoryOutbox(directory: base.appendingPathComponent("outbox"), owner: owner),
                                  transport: MemorySocketTransport(configuration: { config }))
            let store = SessionStore(directory: base.appendingPathComponent("sessions"))
            if arguments.contains("--experience-gallery"),
               let raw = ProcessInfo.processInfo.environment["VOICE_UI_SESSION_FIXTURE"] {
                do {
                    let samples = try JSONDecoder().decode([CaptureSession].self, from: Data(raw.utf8))
                    guard samples.allSatisfy({ $0.memoryOwnerID == owner && $0.completed }) else { throw CaptureFailure.noRelay }
                    if try store.load().isEmpty { for sample in samples { try store.save(sample) } }
                } catch {
                    let controller = SessionController(store: store, prepareRecording: { throw CaptureFailure.noRelay })
                    controller.errorMessage = "The isolated gallery fixture could not be loaded."
                    return controller
                }
            }
            return SessionController(store: store, memorySync: sync,
                makeConnection: { () -> any RecordingConnection in
                    if arguments.contains("--companion-ui-fixture") { return CompanionUIRecording() }
                    return MemoryUIRecording()
                }, prepareRecording: {})
        }
        if arguments.contains("--ui-testing"), arguments.contains("--live-ask-ui-fixture") {
            let directory = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("VoiceCompanion-Live-Ask-QA")
            return SessionController(store: SessionStore(directory: directory),
                makeAnswerConnection: { AnswerUIFixture(delay: .seconds(3)) },
                makeConnection: { LiveAskUIRecording() }, prepareRecording: {})
        }
        if arguments.contains("--ui-testing"), arguments.contains("--ask-ui-fixture") {
            let directory = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
                .appendingPathComponent(arguments.contains("--recall-ui-fixture") ? "VoiceCompanion-Recall-QA" : "VoiceCompanion-Ask-QA")
            let store = SessionStore(directory: directory)
            let controller = SessionController(store: store, makeAnswerConnection: { AnswerUIFixture(past: arguments.contains("--recall-ui-fixture")) })
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
        if ProcessInfo.processInfo.arguments.contains("--ui-testing") { return SessionController() }
        if let config = try? RelayConfiguration.load(), let owner = config.memoryOwnerID,
           UUID(uuidString: owner) != nil {
            let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
                .appendingPathComponent("VoiceCompanion")
            let outbox = MemoryOutbox(directory: base.appendingPathComponent("memory-outbox").appendingPathComponent(owner), owner: owner)
            let sync = MemorySync(outbox: outbox, transport: MemorySocketTransport())
            sync.observeNetwork()
            return SessionController(memorySync: sync)
        }
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
    let past: Bool
    init(delay: Duration = .milliseconds(500), past: Bool = false) { self.delay = delay; self.past = past }
    func run(_ question: ConversationQuestion, onEvent: (AnswerEvent) throws -> Void) async throws {
        if past {
            let source = ConversationPassage(id: "m1", start: 4, text: "Maya prefers morning meetings.",
                session_id: "7D4027F4-E752-4F01-AEAA-2AE1D857839C", revision: 1, captured_at: 1790337600)
            try onEvent(AnswerEvent(type: "context", sources: [source], memory_status: "available"))
        }
        try onEvent(AnswerEvent(type: "delta", text: past ? "Maya prefers mornings" : "Tuesday at ten"))
        try await Task.sleep(for: delay)
        try Task.checkCancellation()
        try onEvent(AnswerEvent(type: "delta", text: past ? " [[m1]]." : " [[p1]]."))
        try onEvent(AnswerEvent(type: "done", references: [past ? "m1" : "p1"]))
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

#if DEBUG
@MainActor
private final class MemoryUIRecording: RecordingConnection {
    func run(onReady: (Duration) -> Void, onFinishing: @escaping (RecordingStopReason) -> Void,
             onEvent: (GrokEvent) throws -> Void) async throws {
        onReady(.seconds(300))
        try onEvent(GrokEvent(type: "transcript.partial", text: "Synthetic appointment Tuesday at ten. Microphone off.", words: [], start: 0, duration: 2, is_final: true))
        onFinishing(.user)
    }
    func stop() {}
    func cancel() {}
}
#endif

#if DEBUG
@MainActor
private final class CompanionUIRecording: RecordingConnection {
    private var stopped = false
    func run(onReady: (Duration) -> Void, onFinishing: @escaping (RecordingStopReason) -> Void,
             onEvent: (GrokEvent) throws -> Void) async throws {
        onReady(.seconds(300))
        try onEvent(GrokEvent(type: "transcript.partial", text: "Maya enjoys swimming.", words: [], start: 0, duration: 2, is_final: false))
        var continuation = ""
        while !stopped {
            try await Task.sleep(for: .milliseconds(250))
            if !stopped {
                continuation += " More simulated speech."
                try onEvent(GrokEvent(type: "transcript.partial", text: continuation, words: [], start: 2, duration: 1, is_final: false))
            }
        }
        onFinishing(.user)
        if !continuation.isEmpty {
            try onEvent(GrokEvent(type: "transcript.partial", text: continuation, words: [], start: 2, duration: 1, is_final: true))
        }
        try onEvent(GrokEvent(type: "transcript.partial", text: "Maya enjoys swimming.", words: [], start: 0, duration: 2, is_final: true))
    }
    func stop() { stopped = true }
    func cancel() { stopped = true }
}
#endif
