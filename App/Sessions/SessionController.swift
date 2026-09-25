import Foundation
import Observation
import OSLog

@MainActor @Observable
final class SessionController {
    var sessions: [CaptureSession] = []
    var current: CaptureSession?
    var isReplaying = false
    var liveStatus: String?
    var isActive: Bool { isReplaying || liveStatus != nil }
    var isAnswering = false
    var answerErrorMessage: String?
    var canAsk: Bool {
        !isReplaying && !isAnswering && (liveStatus == nil || liveStatus == "Recording") &&
        current?.transcript.segments.isEmpty == false
    }
    private var answerTask: Task<Void, Never>?
    private var answerConnection: (any AnswerConnection)?
    private let makeAnswerConnection: () -> any AnswerConnection
    private var recordingStarted: ContinuousClock.Instant?
    var recordingLimit = LiveTranscriber.recordingLimit

    var elapsedRecordingSeconds: Double {
        guard let recordingStarted else { return current?.recordingSeconds ?? 0 }
        let parts = recordingStarted.duration(to: .now).components
        return Double(parts.seconds) + Double(parts.attoseconds) / 1e18
    }

    private func freezeRecordingTime() {
        guard recordingStarted != nil else { return }
        let elapsed = elapsedRecordingSeconds
        current?.recordingSeconds = elapsed
        recordingStarted = nil
    }

    private let finalizationTask = RecordingFinalizationTask()
    private let allowsBackgroundRecording: Bool
    nonisolated static var platformSupportsBackgroundRecording: Bool {
        #if os(iOS)
        true
        #else
        false
        #endif
    }

    private var live: (any RecordingConnection)?
    private let makeConnection: () -> any RecordingConnection
    private let prepareRecording: () async throws -> Void
    var errorMessage: String?
    private var task: Task<Void, Never>?
    private let store: SessionStore
    private let logger = Logger(subsystem: "ai.voicecompanion.app", category: "session")

    init(store: SessionStore? = nil,
         allowsBackgroundRecording: Bool = SessionController.platformSupportsBackgroundRecording,
         makeAnswerConnection: @escaping () -> any AnswerConnection = { LunaAnswerConnection() },
         makeConnection: @escaping () -> any RecordingConnection = { LiveTranscriber() },
         prepareRecording: @escaping () async throws -> Void = {
             let access = MicrophoneAccess()
             await access.request()
             guard access.state == .allowed else {
                 throw CaptureFailure.permissionDenied
             }
             _ = try RelayConfiguration.load()
         }) {
        self.makeAnswerConnection = makeAnswerConnection
        self.allowsBackgroundRecording = allowsBackgroundRecording
        self.makeConnection = makeConnection
        self.prepareRecording = prepareRecording
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let folder = ProcessInfo.processInfo.arguments.contains("--ui-testing") ? "VoiceCompanion-QA" : "VoiceCompanion"
        self.store = store ?? SessionStore(directory: base.appendingPathComponent(folder).appendingPathComponent("sessions"))
        reload()
    }

    func reload() {
        do { sessions = try store.load() }
        catch { errorMessage = "Could not load saved sessions: \(error.localizedDescription)" }
    }

    func startReplay() {
        guard !isActive, !isAnswering else { return }
        errorMessage = nil
        answerErrorMessage = nil
        current = CaptureSession(id: UUID(), createdAt: Date())
        isReplaying = true
        logger.info("replay_started")
        task = Task {
            do {
                guard let url = Bundle.main.url(forResource: "transcript-events", withExtension: "json") else {
                    throw CocoaError(.fileNoSuchFile)
                }
                let events = try JSONDecoder().decode([ReplayEvent].self, from: Data(contentsOf: url))
                var previous = 0.0
                for item in events {
                    try await Task.sleep(for: .seconds(max(0, item.elapsed - previous)))
                    try Task.checkCancellation()
                    previous = item.elapsed
                    if let segment = item.event.segment {
                        current?.transcript.apply(segment)
                        try persist()
                    }
                }
                current?.completed = true
                try persist()
                isReplaying = false
                reload()
                logger.info("replay_completed")
            } catch is CancellationError {
                // stop() owns preservation and the visible incomplete state.
            } catch {
                isReplaying = false
                errorMessage = "Replay failed: \(error.localizedDescription)"
                reload()
            }
        }
    }

    func startRecording() {
        guard !isActive, !isAnswering else { return }
        errorMessage = nil
        answerErrorMessage = nil
        liveStatus = "Connecting…"
        task = Task {
            do {
                try await prepareRecording()
                try Task.checkCancellation()
                current = CaptureSession(id: UUID(), createdAt: Date(), source: "microphone")
                try persist()
                let connection = makeConnection()
                live = connection
                try await connection.run(onReady: { limit in
                    self.recordingLimit = limit
                    self.recordingStarted = .now
                    self.liveStatus = "Recording"
                    self.logger.info("microphone_recording_started")
                }, onFinishing: { reason in
                    self.beginFinalizationAllowance()
                    self.freezeRecordingTime()
                    if reason == .developmentLimit {
                        self.current?.stopNotice = "Stopped automatically at the development recording limit (\(self.recordingLimit.components.seconds) seconds)."
                    }
                    self.liveStatus = "Finishing…"
                }, onEvent: { event in
                    if let segment = event.segment {
                        self.current?.transcript.apply(segment)
                        try self.persist()
                    }
                })
                let completed = current?.endReason == nil
                current?.completed = completed
                try persist()
                logger.info("microphone_recording_completed")
            } catch {
                freezeRecordingTime()
                current?.completed = false
                let reason = current?.endReason ?? "Recording ended: \(error.localizedDescription)"
                current?.endReason = reason
                errorMessage = reason
                do { try persist() }
                catch { errorMessage = "Could not save received text: \(error.localizedDescription)" }
            }
            finalizationTask.end()
            live = nil
            liveStatus = nil
            reload()
        }
    }

    private func beginFinalizationAllowance() {
        finalizationTask.begin { [weak self] in
            self?.interrupt(reason: "Recording finalization was interrupted by the system. Received text is saved; the transcript may be incomplete.")
        }
    }

    func didEnterBackground() {
        if isAnswering { cancelAnswer(notice: AskFailure.interrupted.localizedDescription) }
        if allowsBackgroundRecording && liveStatus == "Recording" {
            // The active audio session owns background execution; no silent audio or retry loop.
            do { try persist() }
            catch { interrupt(reason: "Recording stopped because received text could not be saved.") }
        } else if allowsBackgroundRecording && liveStatus == "Finishing…" {
            beginFinalizationAllowance()
        } else if isActive {
            interrupt(reason: "Recording stopped because the app left the foreground before background capture was active. Received text is saved; the transcript may be incomplete.")
        }
    }

    func stop() {
        if liveStatus != nil {
            liveStatus = "Finishing…"
            if let live { live.stop() } else { task?.cancel() }
            return
        }
        task?.cancel()
        task = nil
        isReplaying = false
        do { try persist() }
        catch { errorMessage = "Could not save session: \(error.localizedDescription)" }
        reload()
        logger.info("replay_stopped")
    }

    func interrupt(reason: String) {
        guard liveStatus != nil else { if isReplaying { stop() }; return }
        freezeRecordingTime()
        current?.completed = false
        current?.endReason = reason
        errorMessage = reason
        // Persist before suspension. Never depend on a final network event in the background.
        do { try persist() }
        catch { errorMessage = "Could not save received text: \(error.localizedDescription)" }
        liveStatus = "Stopping…"
        live?.cancel()
        task?.cancel()
    }

    func close() { guard liveStatus == nil, !isAnswering else { return }; if isReplaying { stop() }; current = nil; answerErrorMessage = nil; reload() }
    func deleteCurrent() {
        guard let current, !isActive, !isAnswering else { return }
        do { try store.delete(current.id); self.current = nil; reload() }
        catch { errorMessage = "Could not delete session: \(error.localizedDescription)" }
    }
    func ask(_ text: String) {
        guard canAsk, let session = current else { return }
        answerErrorMessage = nil
        do {
            let question = try ConversationQuestion(question: text, transcript: session.transcript)
            var answer = ConversationAnswer(id: UUID(), createdAt: Date(), question: question)
            answer.transcriptCutoffSeconds = session.transcript.receivedThroughSeconds
            answer.capturedWhileRecording = liveStatus == "Recording"
            answer.includedInterimText = session.transcript.segments.contains { !$0.isFinal }
            var updated = session
            if updated.answers == nil { updated.answers = [] }
            updated.answers?.append(answer)
            try store.save(updated)
            current = updated
            isAnswering = true
            let connection = makeAnswerConnection()
            answerConnection = connection
            answerTask = Task {
                var lastSave = ContinuousClock.now
                do {
                    try await connection.run(question) { event in
                        guard !Task.isCancelled, self.current?.id == session.id,
                              let index = self.current?.answers?.firstIndex(where: { $0.id == answer.id }),
                              self.current?.answers?[index].state == .streaming else { throw CancellationError() }
                        if event.type == "delta", let text = event.text {
                            self.current?.answers?[index].text += text
                            if lastSave.duration(to: .now) >= .milliseconds(500) {
                                try self.persist()
                                lastSave = .now
                            }
                        } else if event.type == "done" {
                            let refs = event.references ?? []
                            guard refs.allSatisfy({ ref in question.passages.contains(where: { $0.id == ref }) }),
                                  self.current?.answers?[index].text.isEmpty == false else { throw AskFailure.invalidReferences }
                            self.current?.answers?[index].references = refs
                            self.current?.answers?[index].state = .completed
                        }
                    }
                    guard current?.answers?.last?.state == .completed else { throw AskFailure.unavailable }
                } catch {
                    if let index = current?.answers?.firstIndex(where: { $0.id == answer.id }), current?.answers?[index].state == .streaming {
                        current?.answers?[index].state = .failed
                        current?.answers?[index].notice = error.localizedDescription
                    }
                }
                do { try persist() }
                catch { answerErrorMessage = "Could not save the answer: \(error.localizedDescription)" }
                answerConnection = nil
                isAnswering = false
                reload()
            }
        } catch { answerErrorMessage = error.localizedDescription }
    }

    func cancelAnswer(notice: String = "Answer cancelled. Partial text is saved.") {
        guard isAnswering else { return }
        if let index = current?.answers?.indices.last {
            current?.answers?[index].state = .cancelled
            current?.answers?[index].notice = notice
        }
        answerConnection?.cancel()
        answerTask?.cancel()
        do { try persist() }
        catch { answerErrorMessage = "Could not save the partial answer: \(error.localizedDescription)" }
    }

    private func persist() throws { if let current { try store.save(current) } }
}
