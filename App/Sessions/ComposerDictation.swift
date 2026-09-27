import Foundation
import Observation

/// Partial hypotheses replace one another. Only one completed segment is appended to the draft.
@MainActor @Observable
final class ComposerDictation {
    enum State { case idle, starting, listening, finishing }
    private(set) var state: State = .idle
    private(set) var text = ""
    private(set) var notice: String?
    var isActive: Bool { state != .idle }
    private let makeRecognizer: () -> any DictationRecognizing
    private let limit: Duration
    private let finalizationLimit: Duration
    private var recognizer: (any DictationRecognizing)?
    private var task: Task<Void, Never>?
    private var deadline: Task<Void, Never>?
    private var completion: ((String, Bool) -> Void)?
    private var sendRequested = false
    private var generation = UUID()

    init(limit: Duration = .seconds(60), finalizationLimit: Duration = .seconds(5),
         makeRecognizer: @escaping () -> any DictationRecognizing = { AppleDictationRecognizer() }) {
        self.limit = limit; self.finalizationLimit = finalizationLimit; self.makeRecognizer = makeRecognizer
    }

    func start(completion: @escaping (String, Bool) -> Void) {
        guard !isActive else { return }
        state = .starting; text = ""; notice = nil; sendRequested = false
        self.completion = completion
        let current = UUID(); generation = current
        let recognizer = makeRecognizer(); self.recognizer = recognizer
        task = Task {
            do {
                let events = try await recognizer.start()
                guard generation == current, !Task.isCancelled else { recognizer.cancel(); return }
                state = .listening
                deadline = Task {
                    try? await Task.sleep(for: limit)
                    if !Task.isCancelled, generation == current { finish(send: false) }
                }
                for try await event in events {
                    guard generation == current, !Task.isCancelled else { return }
                    // Empty terminal/reset hypotheses must not erase speech the
                    // user already saw. Keep the draft, but do not auto-send an
                    // unconfirmed partial when final recognition is empty.
                    if event.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        if event.isFinal {
                            complete(success: text.isEmpty, message: text.isEmpty ? nil :
                                "Dictation could not confirm the final text. Your words are kept in the draft; review before sending.")
                            return
                        }
                        continue
                    }
                    text = event.text
                    if event.isFinal { complete(success: true); return }
                }
                if generation == current { complete(success: false, message: DictationFailure.interrupted.localizedDescription) }
            } catch {
                if generation == current { complete(success: false, message: error.localizedDescription) }
            }
        }
    }

    func finish(send: Bool) {
        guard state == .listening else { return }
        state = .finishing; sendRequested = send
        recognizer?.finish(); deadline?.cancel()
        let current = generation
        deadline = Task {
            try? await Task.sleep(for: finalizationLimit)
            if !Task.isCancelled, generation == current {
                complete(success: false, message: DictationFailure.timeout.localizedDescription)
            }
        }
    }

    /// Navigation, backgrounding and interruption must never turn into an automatic send.
    func interrupt() {
        guard isActive else { return }
        complete(success: false, message: text.isEmpty ? nil : "Dictation stopped. Captured text is in your draft.")
    }

    /// Explicit deletion discards this segment and any pending Send intent.
    func discard() {
        completion = nil
        text = ""
        complete(success: false)
    }

    private func complete(success: Bool, message: String? = nil) {
        let captured = text.trimmingCharacters(in: .whitespacesAndNewlines)
        let send = success && sendRequested && !captured.isEmpty
        let completion = completion; self.completion = nil
        generation = UUID(); state = .idle; sendRequested = false; text = ""; notice = message
        task?.cancel(); task = nil; deadline?.cancel(); deadline = nil
        recognizer?.cancel(); recognizer = nil
        completion?(captured, send)
    }

    static func appending(_ speech: String, to draft: String) -> String {
        guard !speech.isEmpty else { return draft }
        return draft + (draft.isEmpty || draft.last?.isWhitespace == true ? "" : " ") + speech
    }
}

extension ComposerDictation {
    static func forApp() -> ComposerDictation {
        #if DEBUG
        let args = ProcessInfo.processInfo.arguments
        if args.contains("--ui-testing"), args.contains("--companion-ui-fixture"), args.contains("--dictation-ui-fixture") {
            return ComposerDictation(makeRecognizer: { DictationUIFixture() })
        }
        #endif
        return ComposerDictation()
    }
}

#if DEBUG
@MainActor
private final class DictationUIFixture: DictationRecognizing {
    private let events = AsyncThrowingStream<DictationEvent, Error>.makeStream()
    func start() async throws -> AsyncThrowingStream<DictationEvent, Error> {
        events.continuation.yield(.init(text: "What does Maya", isFinal: false))
        return events.stream
    }
    func finish() {
        let final = ProcessInfo.processInfo.arguments.contains("--dictation-empty-final-fixture") ? "" : "What does Maya enjoy?"
        events.continuation.yield(.init(text: final, isFinal: true))
        events.continuation.finish()
    }
    func cancel() { events.continuation.finish() }
}
#endif
