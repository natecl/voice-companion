import Foundation

@MainActor
final class LiveTranscriber: RecordingConnection {
    private var socket: URLSessionWebSocketTask?
    private var session: URLSession?
    private let microphone = MicrophoneCapture()
    private var sender: Task<Void, Error>?
    private var deadline: Task<Void, Never>?
    private var stopped = false
    private var stopRequested = false
    private var onFinishing: (() -> Void)?
    private var sendingError: Error?

    func run(onReady: () -> Void, onFinishing: @escaping () -> Void, onEvent: (GrokEvent) throws -> Void) async throws {
        self.onFinishing = onFinishing
        defer { cleanup() }
        let config = try RelayConfiguration.load()
        var request = URLRequest(url: config.url)
        request.setValue("Bearer " + config.token, forHTTPHeaderField: "Authorization")
        request.timeoutInterval = 10
        let session = try config.makeSession()
        self.session = session
        let socket = session.webSocketTask(with: request)
        self.socket = socket
        socket.resume()
        deadline = Task { try? await Task.sleep(for: .seconds(10)); if !Task.isCancelled { socket.cancel() } }
        let ready = try await receive(socket)
        guard ready.type == "transcript.created", !stopRequested else { throw CaptureFailure.connectionEnded }
        deadline?.cancel()
        let audio = try microphone.start()
        onReady()
        sender = Task {
            do {
                for try await frame in audio {
                    try Task.checkCancellation()
                    try await socket.send(.data(frame))
                }
                try await socket.send(.string("{\"type\":\"audio.done\"}"))
            } catch {
                self.sendingError = error
                self.microphone.stop()
                socket.cancel()
                throw error
            }
        }
        // Development sessions are bounded; auto-stop still flushes final text.
        deadline = Task {
            try? await Task.sleep(for: .seconds(55))
            if !Task.isCancelled { stop() }
        }
        while true {
            let event: GrokEvent
            do { event = try await receive(socket) }
            catch { throw sendingError ?? error }
            if event.type == "error" { throw CaptureFailure.connectionEnded }
            if event.type == "transcript.done" {
                guard stopRequested else { throw CaptureFailure.connectionEnded }
                try await sender?.value
                return
            }
            try onEvent(event)
        }
    }

    func stop() {
        guard !stopped else { return }
        stopped = true
        onFinishing?()
        stopRequested = true
        microphone.stop()
        if sender == nil { socket?.cancel(); return }
        deadline?.cancel()
        deadline = Task {
            try? await Task.sleep(for: .seconds(12))
            if !Task.isCancelled { socket?.cancel() }
        }
    }

    func cancel() {
        stopRequested = true
        stopped = true
        cleanup()
    }

    private func receive(_ socket: URLSessionWebSocketTask) async throws -> GrokEvent {
        let message = try await socket.receive()
        let data: Data
        switch message {
        case .data(let bytes): data = bytes
        case .string(let text): data = Data(text.utf8)
        @unknown default: throw CaptureFailure.connectionEnded
        }
        return try JSONDecoder().decode(GrokEvent.self, from: data)
    }

    private func cleanup() {
        microphone.stop()
        sender?.cancel()
        deadline?.cancel()
        socket?.cancel(with: .normalClosure, reason: nil)
        socket = nil
        session?.invalidateAndCancel()
        session = nil
        onFinishing = nil
    }
}
