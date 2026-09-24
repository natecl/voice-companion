import Foundation

@MainActor
final class LiveTranscriber {
    private var socket: URLSessionWebSocketTask?
    private var session: URLSession?
    private let microphone = MicrophoneCapture()
    private var sender: Task<Void, Error>?
    private var deadline: Task<Void, Never>?
    private var stopped = false
    private var stopRequested = false

    func run(onReady: () -> Void, onEvent: (GrokEvent) throws -> Void) async throws {
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
        defer { cleanup() }
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
            let event = try await receive(socket)
            if event.type == "error" { throw CaptureFailure.connectionEnded }
            if event.type == "transcript.done" {
                try await sender?.value
                return
            }
            try onEvent(event)
        }
    }

    func stop() {
        guard !stopped else { return }
        stopped = true
        stopRequested = true
        microphone.stop()
        if sender == nil { socket?.cancel(); return }
        deadline?.cancel()
        deadline = Task {
            try? await Task.sleep(for: .seconds(12))
            if !Task.isCancelled { socket?.cancel() }
        }
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
    }
}
