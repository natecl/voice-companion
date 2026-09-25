import Foundation

struct ConversationPassage: Codable, Identifiable, Equatable {
    let id: String
    let start: Double
    let text: String
}

struct ConversationQuestion: Codable {
    let question: String
    let passages: [ConversationPassage]

    init(question: String, transcript: Transcript) throws {
        let question = question.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !question.isEmpty, question.count <= 1000 else { throw AskFailure.invalidQuestion }
        self.question = question
        self.passages = transcript.segments.enumerated().map {
            ConversationPassage(id: "p\($0.offset + 1)", start: $0.element.start, text: $0.element.text)
        }
        guard !passages.isEmpty else { throw AskFailure.noTranscript }
        guard passages.count <= 200, try JSONEncoder().encode(self).count <= 12000 else { throw AskFailure.contextTooLarge }
    }
}

struct ConversationAnswer: Codable, Identifiable {
    enum State: String, Codable { case streaming, completed, cancelled, failed }
    let id: UUID
    let createdAt: Date
    let question: ConversationQuestion
    var text = ""
    var references: [String] = []
    var state: State = .streaming
    var notice: String?
    // Optional for compatibility with saved answers from before live Ask.
    var transcriptCutoffSeconds: Double?
    var capturedWhileRecording: Bool?
    var includedInterimText: Bool?
}

struct AnswerEvent: Decodable {
    let type: String
    var text: String?
    var references: [String]?
    var message: String?
}

enum AskFailure: LocalizedError {
    case invalidQuestion, noTranscript, contextTooLarge, unavailable, invalidReferences, dailyLimit, budgetLimit, busy, accessExpired, interrupted
    var errorDescription: String? {
        switch self {
        case .invalidQuestion: "Enter a question of at most 1,000 characters."
        case .noTranscript: "This session has no transcript to ask about yet."
        case .contextTooLarge: "This conversation is too long for the current Ask limit. Nothing was silently removed."
        case .unavailable: "The answer could not finish. Any partial response is saved; you can try again."
        case .invalidReferences: "The answer included an invalid source reference. Treat this partial response as unverified."
        case .dailyLimit: "Today's Ask limit has been reached. Try again after midnight UTC."
        case .budgetLimit: "The internal trial's answer budget has been reached."
        case .busy: "Another answer is being generated. Wait for it to finish."
        case .accessExpired: "Ask access has expired or was revoked. Renew the internal service credential."
        case .interrupted: "Answer generation stopped when the app left the foreground. Partial text is saved."
        }
    }
    static func server(_ code: String?) -> Self {
        switch code {
        case "invalid_question": .invalidQuestion
        case "context_too_large": .contextTooLarge
        case "invalid_references": .invalidReferences
        case "daily_limit": .dailyLimit
        case "budget_limit": .budgetLimit
        case "busy": .busy
        case "unauthorized": .accessExpired
        default: .unavailable
        }
    }
}

@MainActor
protocol AnswerConnection: AnyObject {
    func run(_ question: ConversationQuestion, onEvent: (AnswerEvent) throws -> Void) async throws
    func cancel()
}

@MainActor
final class LunaAnswerConnection: AnswerConnection {
    private var socket: URLSessionWebSocketTask?
    private var session: URLSession?
    private let configuration: () throws -> RelayConfiguration
    init(configuration: @escaping () throws -> RelayConfiguration = { try RelayConfiguration.load() }) {
        self.configuration = configuration
    }
    func run(_ question: ConversationQuestion, onEvent: (AnswerEvent) throws -> Void) async throws {
        defer { cancel() }
        let config = try configuration()
        var parts = URLComponents(url: config.url, resolvingAgainstBaseURL: false)!
        parts.path = "/ask"
        var request = URLRequest(url: parts.url!)
        request.setValue("Bearer " + config.token, forHTTPHeaderField: "Authorization")
        request.timeoutInterval = 10
        let session = try config.makeSession()
        self.session = session
        let socket = session.webSocketTask(with: request)
        self.socket = socket
        socket.resume()
        let deadline = Task {
            try? await Task.sleep(for: .seconds(25))
            if !Task.isCancelled { socket.cancel() }
        }
        defer { deadline.cancel() }
        do {
            let data = try JSONEncoder().encode(question)
            try await socket.send(.string(String(decoding: data, as: UTF8.self)))
            while true {
                try Task.checkCancellation()
                let message = try await socket.receive()
                let data: Data
                switch message {
                case .string(let text): data = Data(text.utf8)
                case .data(let bytes): data = bytes
                @unknown default: throw AskFailure.unavailable
                }
                let event = try JSONDecoder().decode(AnswerEvent.self, from: data)
                if event.type == "error" { throw AskFailure.server(event.message) }
                try onEvent(event)
                if event.type == "done" { return }
            }
        } catch {
            if (socket.response as? HTTPURLResponse)?.statusCode == 401 { throw AskFailure.accessExpired }
            if error is AskFailure || error is CancellationError { throw error }
            throw AskFailure.unavailable
        }
    }
    func cancel() {
        socket?.cancel(with: .goingAway, reason: nil)
        socket = nil
        session?.invalidateAndCancel()
        session = nil
    }
}
