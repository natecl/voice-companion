import Foundation

struct ProactiveEvent: Decodable {
    let type: String
    let enabled: Bool?
    let turn_id: String?
}

@MainActor
protocol ProactiveConnection: AnyObject {
    func run(capture: String, onEvent: (ProactiveEvent) throws -> Void) async throws
    func observe(_ source: MemorySource) async throws
    func quiet(capture: String) async throws
    func cancel()
}

@MainActor
final class ProactiveSocketConnection: ProactiveConnection {
    private let configuration: () throws -> RelayConfiguration
    private var socket: URLSessionWebSocketTask?
    private var session: URLSession?
    init(configuration: @escaping () throws -> RelayConfiguration) { self.configuration = configuration }
    func run(capture: String, onEvent: (ProactiveEvent) throws -> Void) async throws {
        let config = try configuration()
        guard var parts = URLComponents(url: config.url, resolvingAgainstBaseURL: false) else { throw CompanionFailure.invalidRequest }
        parts.path = "/proactive"
        guard let url = parts.url else { throw CompanionFailure.invalidRequest }
        var request = URLRequest(url: url)
        request.setValue("Bearer " + config.token, forHTTPHeaderField: "Authorization")
        let session = try config.makeSession(); self.session = session
        let socket = session.webSocketTask(with: request); self.socket = socket
        socket.maximumMessageSize = 4000
        defer { cancel() }
        socket.resume()
        try await withTaskCancellationHandler {
            try await send(["operation": "open", "capture": capture])
            while !Task.isCancelled {
                let raw = try await socket.receive()
                let data: Data
                switch raw {
                case .string(let value): data = Data(value.utf8)
                case .data(let value): data = value
                @unknown default: throw CompanionFailure.invalidResponse
                }
                let event = try JSONDecoder().decode(ProactiveEvent.self, from: data)
                guard ["ready", "quiet", "silence", "contribution", "existing", "unavailable", "cancelled"].contains(event.type),
                      event.type != "contribution" || event.turn_id != nil else { throw CompanionFailure.invalidResponse }
                try Task.checkCancellation()
                try onEvent(event)
            }
        } onCancel: { socket.cancel(with: .goingAway, reason: nil) }
    }
    private func send(_ payload: [String: String]) async throws {
        guard let socket else { throw CompanionFailure.invalidRequest }
        let data = try JSONEncoder().encode(payload)
        try await socket.send(.string(String(decoding: data, as: UTF8.self)))
    }
    func observe(_ source: MemorySource) async throws {
        struct Update: Encodable { let operation = "observe"; let live: MemorySource }
        guard let socket else { throw CompanionFailure.invalidRequest }
        let data = try JSONEncoder().encode(Update(live: source))
        guard data.count <= 64000 else { throw AskFailure.contextTooLarge }
        try await socket.send(.string(String(decoding: data, as: UTF8.self)))
    }
    func quiet(capture: String) async throws { try await send(["operation": "quiet", "capture": capture]) }
    func cancel() {
        socket?.cancel(with: .goingAway, reason: nil); socket = nil
        session?.invalidateAndCancel(); session = nil
    }
}
