import Foundation

/// One hardware session with independently stoppable, bounded consumers.
@MainActor
final class SharedMicrophone {
    static let shared = SharedMicrophone()
    private let capture: any AudioCapture
    private var consumers: [UUID: AsyncThrowingStream<Data, Error>.Continuation] = [:]
    private var pump: Task<Void, Never>?
    private var generation = UUID()

    init(capture: any AudioCapture = MicrophoneCapture()) { self.capture = capture }

    func subscribe(_ id: UUID) throws -> AsyncThrowingStream<Data, Error> {
        guard consumers[id] == nil else { throw CaptureFailure.serviceBusy }
        let audio = consumers.isEmpty ? try capture.start() : nil
        let (stream, continuation) = AsyncThrowingStream<Data, Error>.makeStream(bufferingPolicy: .bufferingOldest(50))
        consumers[id] = continuation
        if let audio {
            let current = UUID(); generation = current
            pump = Task {
                do {
                    for try await frame in audio {
                        guard !Task.isCancelled, generation == current else { return }
                        for (id, consumer) in consumers {
                            switch consumer.yield(frame) {
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
        consumers.removeValue(forKey: id)?.finish(throwing: error)
        if consumers.isEmpty {
            generation = UUID(); pump?.cancel(); pump = nil; capture.stop()
        }
    }

    private func finishAll(error: Error) {
        let old = consumers; consumers.removeAll()
        generation = UUID(); pump = nil; capture.stop()
        for consumer in old.values { consumer.finish(throwing: error) }
    }
}

@MainActor
final class SharedMicrophoneCapture: AudioCapture {
    private let hub: SharedMicrophone
    private let id = UUID()
    private var active = false
    init(hub: SharedMicrophone = .shared) { self.hub = hub }
    func start() throws -> AsyncThrowingStream<Data, Error> {
        let stream = try hub.subscribe(id); active = true; return stream
    }
    func stop() { if active { active = false; hub.unsubscribe(id) } }
}
