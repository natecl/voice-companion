import Foundation
import Observation

/// Main chat has its own lifetime; capture/navigation never owns this task or draft.
@MainActor @Observable
final class CompanionController {
    struct Response {
        enum State { case streaming, saved, uncertain }
        let request: CompanionQuestion
        var text = ""
        var sources: [CompanionEvidence] = []
        var references: [String] = []
        var memoryStatus: String?
        var state: State = .streaming
    }

    let owner: String
    var draft = ""
    var attachment: CompanionAttachment?
    var useMemory = true
    private(set) var turns: [CompanionTurn] = []
    private(set) var response: Response?
    private(set) var conversationID: String?
    private(set) var nextBefore: Int?
    private(set) var isBusy = false
    private(set) var notice: String?
    private let makeConnection: () -> any CompanionConnection
    private var connection: (any CompanionConnection)?
    private var task: Task<Void, Never>?

    init(owner: String, makeConnection: @escaping () -> any CompanionConnection) {
        self.owner = owner
        self.makeConnection = makeConnection
    }

    /// Every operation rechecks the configured owner before opening a socket.
    convenience init(owner: String) {
        self.init(owner: owner, makeConnection: {
            CompanionSocketConnection(configuration: {
                let config = try RelayConfiguration.load()
                guard config.memoryOwnerID == owner else { throw AskFailure.accessExpired }
                return config
            })
        })
    }

    func send(live: CaptureSession? = nil, revision: Int = 1) {
        guard !isBusy else { return }
        do {
            if let live, live.memoryOwnerID != owner { throw AskFailure.accessExpired }
            let question = try CompanionQuestion(question: draft, memory: useMemory, attachment: attachment,
                live: live.map { MemorySource(live: $0, revision: revision) })
            begin(question)
            draft = ""
        } catch { notice = error.localizedDescription }
    }

    /// Explicit user recovery only. Reuse the entire original request, including its cutoff.
    func recoverUncertainResponse() {
        guard !isBusy, let response, response.state == .uncertain else { return }
        begin(response.request)
    }

    private func begin(_ question: CompanionQuestion) {
        notice = nil
        response = Response(request: question)
        isBusy = true
        let socket = makeConnection()
        connection = socket
        task = Task {
            defer { connection = nil; isBusy = false; task = nil }
            do {
                try await socket.run(.ask(question)) { event in
                    switch event.type {
                    case "accepted": self.conversationID = event.conversation_id
                    case "context":
                        self.response?.sources = event.sources ?? []
                        self.response?.memoryStatus = event.memory_status
                        if event.memory_status == "unavailable" { self.notice = "Some earlier conversations weren’t available for this answer. You can still continue chatting." }
                    case "delta": self.response?.text += event.text ?? ""
                    case "done":
                        self.response?.references = event.references ?? []
                        self.response?.state = .saved
                    case "existing":
                        self.conversationID = event.conversation_id
                        if let turn = event.turn {
                            self.replace(turn)
                            self.response = nil
                            if turn.state == .pending { self.notice = "This question is still being processed. Refresh the chat to check its status." }
                        }
                    default: break
                    }
                }
                try Task.checkCancellation()
                // Read-only refresh gets durable citation locations and any source invalidations.
                try await readHistory(before: nil)
            } catch {
                if error as? AskFailure == .accessExpired {
                    turns = []
                    response = nil
                }
                if response?.state != .saved {
                    response?.state = .uncertain
                    if error as? AskFailure == .memoryContextChanged || error as? AskFailure == .accessExpired {
                        response?.text = ""
                        response?.sources = []
                        response?.references = []
                    }
                }
                notice = error is CancellationError
                    ? "Answer interrupted. Refresh the chat to check what was saved."
                    : error.localizedDescription
            }
        }
    }

    func refresh() { load(before: nil) }
    func loadEarlier() {
        guard let nextBefore else { return }
        load(before: nextBefore)
    }
    private func load(before: Int?) {
        guard !isBusy else { return }
        isBusy = true
        notice = nil
        // Don't leave old answers presented as current if server revalidation fails.
        if before == nil { turns = []; nextBefore = nil }
        task = Task {
            defer { connection = nil; isBusy = false; task = nil }
            do { try await readHistory(before: before) }
            catch { notice = error is CancellationError ? "Chat refresh interrupted." : error.localizedDescription }
        }
    }
    private func readHistory(before: Int?) async throws {
        let socket = makeConnection()
        connection = socket
        try await socket.run(.history(before: before)) { event in
            guard let page = event.turns else { throw CompanionFailure.invalidResponse }
            self.conversationID = event.conversation_id
            if before == nil { self.turns = page.sorted { $0.sequence < $1.sequence } }
            else { for turn in page { self.replace(turn) } }
            self.nextBefore = event.next_before
            if let id = self.response?.request.question_id, page.contains(where: { $0.id == id }) { self.response = nil }
        }
    }
    private func replace(_ turn: CompanionTurn) {
        turns.removeAll { $0.id == turn.id }
        turns.append(turn)
        turns.sort { $0.sequence < $1.sequence }
    }
    func cancel() {
        connection?.cancel()
        task?.cancel()
    }
    func clearForSourceDeletion() {
        cancel()
        turns = []
        response = nil
        nextBefore = nil
    }
    func didEnterBackground() { cancel() }
    func didBecomeActive() { refresh() }
}
