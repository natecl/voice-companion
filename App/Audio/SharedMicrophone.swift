import Foundation
import Observation

/// One hardware session with independently stoppable, bounded consumers.
@Observable @MainActor
final class SharedMicrophone {
    enum Purpose { case meeting, dictation }
    private var purposes: [UUID: Purpose] = [:]
    var meetingAudioPaused: Bool { purposes.values.contains(.dictation) }
    static let shared = SharedMicrophone()
    private let capture: any AudioCapture
    private var consumers: [UUID: AsyncThrowingStream<Data, Error>.Continuation] = [:]
    private var pump: Task<Void, Never>?
    private var generation = UUID()

    init(capture: any AudioCapture = MicrophoneCapture()) { self.capture = capture }

    func subscribe(_ id: UUID, purpose: Purpose = .meeting) throws -> AsyncThrowingStream<Data, Error> {
        guard consumers[id] == nil else { throw CaptureFailure.serviceBusy }
        let audio = consumers.isEmpty ? try capture.start() : nil
        let (stream, continuation) = AsyncThrowingStream<Data, Error>.makeStream(bufferingPolicy: .bufferingOldest(50))
        consumers[id] = continuation
        purposes[id] = purpose
        if let audio {
            let current = UUID(); generation = current
            pump = Task {
                do {
                    for try await frame in audio {
                        guard !Task.isCancelled, generation == current else { return }
                        let paused = meetingAudioPaused
                        for (id, consumer) in consumers {
                            // Silence preserves provider timing without sending private composer audio.
                            let output = paused && purposes[id] == .meeting
                                ? Data(count: frame.count) : frame
                            switch consumer.yield(output) {
                            case .dropped: unsubscribe(id, error: CaptureFailure.overflow)
                            case .terminated: unsubscribe(id)
                            case .enqueued: break
                            @unknown default: unsubscribe(id, error: CaptureFailure.unavailable)
                            }
                        }
                    }
                    if generation == current { finishAll(error: CaptureFailure.interrupted) }
                } catch { if generation == current { finishAll(error: error) } }
            }
        }
        return stream
    }

    func unsubscribe(_ id: UUID, error: Error? = nil) {
        purposes.removeValue(forKey: id)
        consumers.removeValue(forKey: id)?.finish(throwing: error)
        if consumers.isEmpty {
            generation = UUID(); pump?.cancel(); pump = nil; capture.stop()
        }
    }

    private func finishAll(error: Error) {
        let old = consumers; consumers.removeAll(); purposes.removeAll()
        generation = UUID(); pump = nil; capture.stop()
        for consumer in old.values { consumer.finish(throwing: error) }
    }
}

@MainActor
final class SharedMicrophoneCapture: AudioCapture {
    private let hub: SharedMicrophone
    private let id = UUID()
    private let purpose: SharedMicrophone.Purpose
    private var active = false
    init(hub: SharedMicrophone = .shared, purpose: SharedMicrophone.Purpose = .meeting) {
        self.hub = hub; self.purpose = purpose
    }
    func start() throws -> AsyncThrowingStream<Data, Error> {
        let stream = try hub.subscribe(id, purpose: purpose); active = true; return stream
    }
    func stop() { if active { active = false; hub.unsubscribe(id) } }
}
