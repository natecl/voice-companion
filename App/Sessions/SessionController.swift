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

    private var live: (any RecordingConnection)?
    private let makeConnection: () -> any RecordingConnection
    private let prepareRecording: () async throws -> Void
    var errorMessage: String?
    private var task: Task<Void, Never>?
    private let store: SessionStore
    private let logger = Logger(subsystem: "ai.voicecompanion.app", category: "session")

    init(store: SessionStore? = nil,
         makeConnection: @escaping () -> any RecordingConnection = { LiveTranscriber() },
         prepareRecording: @escaping () async throws -> Void = {
             _ = try RelayConfiguration.load()
             let access = MicrophoneAccess()
             await access.request()
             guard access.state == .allowed else {
                 throw NSError(domain: "Microphone", code: 1, userInfo: [NSLocalizedDescriptionKey: "Microphone permission is required. Enable it in system settings."])
             }
         }) {
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
        guard !isActive else { return }
        errorMessage = nil
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
        guard !isActive else { return }
        errorMessage = nil
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
            live = nil
            liveStatus = nil
            reload()
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

    func close() { guard liveStatus == nil else { return }; if isReplaying { stop() }; current = nil; reload() }
    func deleteCurrent() {
        guard let current, !isActive else { return }
        do { try store.delete(current.id); self.current = nil; reload() }
        catch { errorMessage = "Could not delete session: \(error.localizedDescription)" }
    }
    private func persist() throws { if let current { try store.save(current) } }
}
