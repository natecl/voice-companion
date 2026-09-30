import Foundation

@MainActor
final class LiveTranscriber: RecordingConnection {
    private var socket: URLSessionWebSocketTask?
    private var session: URLSession?
    nonisolated static let recordingLimit: Duration = .seconds(300)

    struct Timeouts {
        var ready: Duration = .seconds(10)
        var recording: Duration = LiveTranscriber.recordingLimit
        var finalization: Duration = .seconds(12)
    }
    private let microphone: any AudioCapture
    private let configuration: () throws -> RelayConfiguration
    private let timeouts: Timeouts
    private var sender: Task<Void, Error>?
    private var deadline: Task<Void, Never>?
    private var stopped = false
    private var stopRequested = false
    private var onFinishing: ((RecordingStopReason) -> Void)?
    private var sendingError: Error?
    private var timeoutError: CaptureFailure?

    init(microphone: any AudioCapture = SharedMicrophoneCapture(),
         configuration: @escaping () throws -> RelayConfiguration = { try RelayConfiguration.load() },
         timeouts: Timeouts = Timeouts()) {
        self.microphone = microphone
        self.configuration = configuration
        self.timeouts = timeouts
    }

    func run(onReady: (Duration) -> Void, onFinishing: @escaping (RecordingStopReason) -> Void, onEvent: (GrokEvent) throws -> Void) async throws {
        self.onFinishing = onFinishing
        defer { cleanup() }
        let config = try await configuration().forRequest()
        var request = URLRequest(url: config.url)
        request.setValue("Bearer " + config.token, forHTTPHeaderField: "Authorization")
        request.timeoutInterval = 10
        let session = try config.makeSession()
        self.session = session
        let socket = session.webSocketTask(with: request)
        self.socket = socket
        socket.resume()
        deadline = Task {
            try? await Task.sleep(for: timeouts.ready)
            if !Task.isCancelled { timeoutError = .connectionTimedOut; socket.cancel() }
        }
        let ready = try await receive(socket)
        guard ready.type == "transcript.created", !stopRequested else { throw CaptureFailure.connectionEnded }
        deadline?.cancel()
        let audio = try microphone.start()
        onReady(timeouts.recording)
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
            try? await Task.sleep(for: timeouts.recording)
            if !Task.isCancelled { finish(reason: .developmentLimit) }
        }
        while true {
            let event = try await receive(socket)
            if event.type == "error" { throw CaptureFailure.connectionEnded }
            if event.type == "transcript.done" {
                guard stopRequested else { throw CaptureFailure.connectionEnded }
                try await sender?.value
                return
            }
            try onEvent(event)
        }
    }

    func stop() { finish(reason: .user) }

    private func finish(reason: RecordingStopReason) {
        guard !stopped else { return }
        stopped = true
        onFinishing?(reason)
        stopRequested = true
        microphone.stop()
        if sender == nil { socket?.cancel(); return }
        deadline?.cancel()
        deadline = Task {
            try? await Task.sleep(for: timeouts.finalization)
            if !Task.isCancelled { timeoutError = .finalizationTimedOut; socket?.cancel() }
        }
    }

    func cancel() {
        stopRequested = true
        stopped = true
        cleanup()
    }

    private func receive(_ socket: URLSessionWebSocketTask) async throws -> GrokEvent {
        let message: URLSessionWebSocketTask.Message
        do { message = try await socket.receive() }
        catch {
            if let status = (socket.response as? HTTPURLResponse)?.statusCode {
                if status == 401 || status == 403 { throw CaptureFailure.accessExpired }
                if status == 503 { throw CaptureFailure.authorizationUnavailable }
            }
            throw (timeoutError as Error?) ?? sendingError ?? error
        }
        let data: Data
        switch message {
        case .data(let bytes): data = bytes
        case .string(let text): data = Data(text.utf8)
        @unknown default: throw CaptureFailure.connectionEnded
        }
        let event = try JSONDecoder().decode(GrokEvent.self, from: data)
        if event.type == "error" {
            // Only known relay codes become user-facing messages; never display arbitrary provider text.
            switch event.message {
            case "unauthorized": throw CaptureFailure.accessExpired
            case "daily_limit": throw CaptureFailure.dailyLimit
            case "budget_limit": throw CaptureFailure.budgetLimit
            case "busy": throw CaptureFailure.serviceBusy
            case "authorization_unavailable": throw CaptureFailure.authorizationUnavailable
            default: throw CaptureFailure.connectionEnded
            }
        }
        return event
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
