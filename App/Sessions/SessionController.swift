import Foundation
import Observation
import OSLog

@MainActor @Observable
final class SessionController {
    var sessions: [CaptureSession] = []
    var current: CaptureSession?
    var isReplaying = false
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
        guard !isReplaying else { return }
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

    func stop() {
        task?.cancel()
        task = nil
        isReplaying = false
        do { try persist() }
        catch { errorMessage = "Could not save session: \(error.localizedDescription)" }
        reload()
        logger.info("replay_stopped")
    }

    func close() { if isReplaying { stop() }; current = nil; reload() }
    func deleteCurrent() {
        guard let current, !isReplaying else { return }
        do { try store.delete(current.id); self.current = nil; reload() }
        catch { errorMessage = "Could not delete session: \(error.localizedDescription)" }
    }
    private func persist() throws { if let current { try store.save(current) } }
}
