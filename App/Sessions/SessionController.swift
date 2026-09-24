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
    private var live: LiveTranscriber?
    var errorMessage: String?
    private var task: Task<Void, Never>?
    private let store: SessionStore
    private let logger = Logger(subsystem: "ai.voicecompanion.app", category: "session")

    init() {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let folder = ProcessInfo.processInfo.arguments.contains("--ui-testing") ? "VoiceCompanion-QA" : "VoiceCompanion"
        store = SessionStore(directory: base.appendingPathComponent(folder).appendingPathComponent("sessions"))
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
                _ = try RelayConfiguration.load()
                let access = MicrophoneAccess()
                await access.request()
                guard access.state == .allowed else {
                    throw NSError(domain: "Microphone", code: 1, userInfo: [NSLocalizedDescriptionKey: "Microphone permission is required. Enable it in system settings."])
                }
                try Task.checkCancellation()
                current = CaptureSession(id: UUID(), createdAt: Date(), source: "microphone")
                try persist()
                let connection = LiveTranscriber()
                live = connection
                try await connection.run(onReady: {
                    self.liveStatus = "Recording"
                    self.logger.info("microphone_recording_started")
                }, onEvent: { event in
                    if let segment = event.segment {
                        self.current?.transcript.apply(segment)
                        try self.persist()
                    }
                })
                current?.completed = true
                try persist()
                logger.info("microphone_recording_completed")
            } catch {
                current?.completed = false
                errorMessage = "Recording ended: \(error.localizedDescription)"
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

    func close() { guard liveStatus == nil else { return }; if isReplaying { stop() }; current = nil; reload() }
    func deleteCurrent() {
        guard let current, !isActive else { return }
        do { try store.delete(current.id); self.current = nil; reload() }
        catch { errorMessage = "Could not delete session: \(error.localizedDescription)" }
    }
    private func persist() throws { if let current { try store.save(current) } }
}
