import Foundation

struct RecordingNotes: Decodable {
    struct Bullet: Decodable { let text: String; let passages: [String] }
    struct Section: Decodable { let heading: String; let items: [Bullet] }
    let title: String
    let overview: Bullet
    let sections: [Section]
}
struct RecordingNotesResult: Decodable {
    let revision: Int
    let generation_version: String
    let state: String
    let incomplete: Bool
    let notes: RecordingNotes?
    let error: String?
}

/// One bounded request; reads never generate notes. Cancellation closes the socket.
@MainActor
final class RecordingNotesConnection {
    private let configuration: () throws -> RelayConfiguration
    init(configuration: @escaping () throws -> RelayConfiguration) { self.configuration = configuration }
    func read(_ attachment: CompanionAttachment, retry: Bool = false) async throws -> RecordingNotesResult? {
        let config = try configuration()
        guard var parts = URLComponents(url: config.url, resolvingAgainstBaseURL: false) else { throw CompanionFailure.invalidRequest }
        parts.path = "/notes"
        guard let url = parts.url else { throw CompanionFailure.invalidRequest }
        var request = URLRequest(url: url)
        request.setValue("Bearer " + config.token, forHTTPHeaderField: "Authorization")
        request.timeoutInterval = 10
        let session = try config.makeSession()
        let socket = session.webSocketTask(with: request)
        socket.maximumMessageSize = 32000
        defer { socket.cancel(with: .goingAway, reason: nil); session.invalidateAndCancel() }
        socket.resume()
        let deadline = Task {
            try? await Task.sleep(for: .seconds(10))
            if !Task.isCancelled { socket.cancel() }
        }
        defer { deadline.cancel() }
        return try await withTaskCancellationHandler {
            try Task.checkCancellation()
            let data = try JSONSerialization.data(withJSONObject: ["operation": retry ? "retry" : "read", "session_id": attachment.session_id, "revision": attachment.revision])
            try await socket.send(.string(String(decoding: data, as: UTF8.self)))
            let message = try await socket.receive()
            try Task.checkCancellation()
            let bytes: Data
            switch message {
            case .string(let text): bytes = Data(text.utf8)
            case .data(let data): bytes = data
            @unknown default: throw CompanionFailure.invalidResponse
            }
            struct Response: Decodable {
                let type: String
                let session_id: String?
                let revision: Int?
                let result: RecordingNotesResult?
            }
            let response = try JSONDecoder().decode(Response.self, from: bytes)
            guard response.type == "notes", response.session_id == attachment.session_id,
                  response.revision == attachment.revision,
                  response.result == nil || response.result?.state == "outdated" || response.result?.revision == attachment.revision else { throw CompanionFailure.sourceUnavailable }
            return response.result
        } onCancel: { socket.cancel(with: .goingAway, reason: nil) }
    }
}
