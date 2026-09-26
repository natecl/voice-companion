import Foundation

struct CompanionAttachment: Codable, Equatable {
    let session_id: String
    let revision: Int
}

struct CompanionQuestion: Encodable {
    let question_id: String
    let question: String
    let memory: Bool
    let attachment: CompanionAttachment?
    let live: MemorySource?

    init(id: UUID = UUID(), question: String, memory: Bool = true,
         attachment: CompanionAttachment? = nil, live: MemorySource? = nil) throws {
        let text = question.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, text.unicodeScalars.count <= 1000 else { throw AskFailure.invalidQuestion }
        guard live == nil || (live?.completed == false && live?.origin == nil),
              attachment == nil || attachment!.revision > 0 else { throw CompanionFailure.invalidRequest }
        self.question_id = id.uuidString
        self.question = text
        self.memory = memory
        self.attachment = attachment
        self.live = live
    }
    private enum CodingKeys: String, CodingKey { case operation, question_id, question, memory, attachment, live }
    func encode(to encoder: Encoder) throws {
        var values = encoder.container(keyedBy: CodingKeys.self)
        try values.encode("ask", forKey: .operation)
        try values.encode(question_id, forKey: .question_id)
        try values.encode(question, forKey: .question)
        try values.encode(memory, forKey: .memory)
        // Explicit nulls are part of the server contract.
        try values.encode(attachment, forKey: .attachment)
        try values.encode(live, forKey: .live)
    }
}

struct CompanionSourceLocation: Decodable, Equatable {
    let session_id: String
    let revision: Int
    let passage_id: String
    let text_start: Int
    let text_end: Int
    let snapshot_id: String?
}
struct CompanionCitation: Decodable, Equatable {
    let id: String
    let source: CompanionSourceLocation
}
struct CompanionEvidence: Decodable {
    let id: String
    let text: String
    let start: Double
    let session_id: String?
    let revision: Int?
    let passage_id: String?
    let captured_at: Double?
    let snapshot_id: String?
}
struct CompanionTurn: Decodable, Identifiable {
    enum State: String, Decodable { case pending, complete, failed, outdated, invalidated }
    let id: String
    let sequence: Int
    let question: String
    let state: State
    let answer: String?
    let created_at: Double
    let citations: [CompanionCitation]
}
struct CompanionEvent: Decodable {
    let type: String
    let question_id: String?
    let conversation_id: String?
    let text: String?
    let message: String?
    let sources: [CompanionEvidence]?
    let memory_status: String?
    let references: [String]?
    let saved: Bool?
    let turn: CompanionTurn?
    let turns: [CompanionTurn]?
    let next_before: Int?
    let turn_id: String?
    let source: CompanionEvidence?
}

enum CompanionCommand: Encodable {
    case ask(CompanionQuestion)
    case history(before: Int? = nil)
    case source(turnID: String, citationID: String)
    private enum CodingKeys: String, CodingKey { case operation, before, turn_id, citation_id }
    func encode(to encoder: Encoder) throws {
        switch self {
        case .source(let turnID, let citationID):
            var values = encoder.container(keyedBy: CodingKeys.self)
            try values.encode("source", forKey: .operation)
            try values.encode(turnID, forKey: .turn_id)
            try values.encode(citationID, forKey: .citation_id)
        case .ask(let question): try question.encode(to: encoder)
        case .history(let before):
            guard before == nil || before! > 0 else { throw CompanionFailure.invalidRequest }
            var values = encoder.container(keyedBy: CodingKeys.self)
            try values.encode("history", forKey: .operation)
            try values.encode(before, forKey: .before)
        }
    }
}

enum CompanionFailure: LocalizedError {
    case invalidRequest, invalidResponse, requestConflict, unavailable, sourceUnavailable
    var errorDescription: String? {
        switch self {
        case .sourceUnavailable: "This source was deleted, changed, or is no longer available."
        case .invalidRequest: "This chat request could not be sent."
        case .unavailable: "The companion connection could not finish. Refresh the chat to check what was saved."
        case .invalidResponse: "The companion connection ended without a verified saved answer. Reload the chat to check its status."
        case .requestConflict: "This question was already sent with different context. Reload the chat before asking again."
        }
    }
}

/// Validates ordering before an event is allowed to update presentation state.
struct CompanionEventSequence {
    let command: CompanionCommand
    private var accepted = false
    private var sources: Set<String>?
    private var receivedText = false
    mutating func accept(_ event: CompanionEvent) throws -> Bool {
        if event.type == "error" {
            switch event.message {
            case "source_unavailable": throw CompanionFailure.sourceUnavailable
            case "question_id_conflict": throw CompanionFailure.requestConflict
            case "chat_busy": throw AskFailure.busy
            case "companion_context_too_large": throw AskFailure.contextTooLarge
            case "invalid_question", "context_too_large", "invalid_references", "daily_limit", "budget_limit", "busy", "unauthorized", "memory_context_changed":
                throw AskFailure.server(event.message)
            default: throw CompanionFailure.unavailable
            }
        }
        switch command {
        case .source(let turnID, let citationID):
            guard event.type == "source", event.turn_id == turnID, let source = event.source,
                  source.id == citationID, source.session_id != nil, source.revision != nil,
                  source.passage_id != nil else { throw CompanionFailure.invalidResponse }
            return true
        case .history:
            guard event.type == "history", event.conversation_id != nil, event.turns != nil else {
                throw CompanionFailure.invalidResponse
            }
            return true
        case .ask(let request):
            switch event.type {
            case "existing":
                guard !accepted, let turn = event.turn, turn.id == request.question_id,
                      turn.question == request.question, event.conversation_id != nil else { throw CompanionFailure.invalidResponse }
                return true
            case "accepted":
                guard !accepted, event.question_id == request.question_id, event.conversation_id != nil else { throw CompanionFailure.invalidResponse }
                accepted = true
            case "context":
                guard accepted, sources == nil, let evidence = event.sources,
                      Set(evidence.map(\.id)).count == evidence.count else { throw CompanionFailure.invalidResponse }
                sources = Set(evidence.map(\.id))
            case "delta":
                guard sources != nil, let text = event.text else { throw CompanionFailure.invalidResponse }
                receivedText = receivedText || !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            case "done":
                guard receivedText, let sources, event.question_id == request.question_id, event.saved == true,
                      let references = event.references, Set(references).isSubset(of: sources) else { throw CompanionFailure.invalidResponse }
                return true
            default: throw CompanionFailure.invalidResponse
            }
            return false
        }
    }
}

@MainActor
protocol CompanionConnection: AnyObject {
    func run(_ command: CompanionCommand, onEvent: (CompanionEvent) throws -> Void) async throws
    func cancel()
}

@MainActor
final class CompanionSocketConnection: CompanionConnection {
    private var running = false
    private var socket: URLSessionWebSocketTask?
    private var session: URLSession?
    private let configuration: () throws -> RelayConfiguration
    init(configuration: @escaping () throws -> RelayConfiguration = { try RelayConfiguration.load() }) {
        self.configuration = configuration
    }
    func run(_ command: CompanionCommand, onEvent: (CompanionEvent) throws -> Void) async throws {
        guard !running else { throw AskFailure.busy }
        running = true
        defer { running = false }
        let data = try JSONEncoder().encode(command)
        guard data.count <= 64000 else { throw AskFailure.contextTooLarge }
        let config = try configuration()
        guard var parts = URLComponents(url: config.url, resolvingAgainstBaseURL: false) else { throw CompanionFailure.invalidRequest }
        parts.path = "/companion"
        guard let url = parts.url else { throw CompanionFailure.invalidRequest }
        var request = URLRequest(url: url)
        request.setValue("Bearer " + config.token, forHTTPHeaderField: "Authorization")
        request.timeoutInterval = 10
        let session = try config.makeSession()
        self.session = session
        let socket = session.webSocketTask(with: request)
        self.socket = socket
        socket.maximumMessageSize = 1_000_000
        defer { cancel() }
        socket.resume()
        let deadline = Task {
            try? await Task.sleep(for: .seconds(25))
            if !Task.isCancelled { socket.cancel() }
        }
        defer { deadline.cancel() }
        do {
            try await withTaskCancellationHandler {
                try Task.checkCancellation()
                try await socket.send(.string(String(decoding: data, as: UTF8.self)))
                var sequence = CompanionEventSequence(command: command)
                while true {
                    let message = try await socket.receive()
                    try Task.checkCancellation()
                    let bytes: Data
                    switch message {
                    case .string(let text): bytes = Data(text.utf8)
                    case .data(let data): bytes = data
                    @unknown default: throw CompanionFailure.invalidResponse
                    }
                    guard bytes.count <= 1_000_000 else { throw CompanionFailure.invalidResponse }
                    let event = try JSONDecoder().decode(CompanionEvent.self, from: bytes)
                    let terminal = try sequence.accept(event)
                    try onEvent(event)
                    if terminal { return }
                }
            } onCancel: { socket.cancel(with: .goingAway, reason: nil) }
        } catch {
            if Task.isCancelled { throw CancellationError() }
            if (socket.response as? HTTPURLResponse)?.statusCode == 401 { throw AskFailure.accessExpired }
            if error is AskFailure || error is CompanionFailure || error is CancellationError { throw error }
            throw CompanionFailure.unavailable
        }
    }
    func cancel() {
        socket?.cancel(with: .goingAway, reason: nil)
        socket = nil
        session?.invalidateAndCancel()
        session = nil
    }
}
