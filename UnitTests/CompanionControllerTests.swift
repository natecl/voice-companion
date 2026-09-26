import Foundation
import XCTest

@MainActor
private final class UnavailableCompanion: CompanionConnection {
    var commands: [CompanionCommand] = []
    func run(_ command: CompanionCommand, onEvent: (CompanionEvent) throws -> Void) async throws {
        commands.append(command)
        throw AskFailure.unavailable
    }
    func cancel() {}
}

@MainActor
private final class SavedThenOfflineCompanion: CompanionConnection {
    var asks = 0
    func run(_ command: CompanionCommand, onEvent: (CompanionEvent) throws -> Void) async throws {
        guard case .ask(let question) = command else { throw AskFailure.unavailable }
        asks += 1
        for value: [String: Any] in [
            ["type":"accepted", "question_id":question.question_id, "conversation_id":"main"],
            ["type":"context", "sources":[]],
            ["type":"delta", "text":"Saved answer"],
            ["type":"done", "question_id":question.question_id, "references":[], "saved":true]
        ] {
            try onEvent(JSONDecoder().decode(CompanionEvent.self, from: JSONSerialization.data(withJSONObject: value)))
        }
    }
    func cancel() {}
}

@MainActor
final class CompanionControllerTests: XCTestCase {
    private func idle(_ controller: CompanionController) async throws {
        for _ in 0..<100 {
            if !controller.isBusy { return }
            try await Task.sleep(for: .milliseconds(10))
        }
        XCTFail("Controller remained busy")
    }
    func testExplicitRecoveryPreservesRequestAndNeverAutomaticallyRetries() async throws {
        let socket = UnavailableCompanion()
        let controller = CompanionController(owner: "owner", makeConnection: { socket })
        controller.draft = "Original question"
        controller.useMemory = false
        controller.send()
        try await idle(controller)
        XCTAssertEqual(socket.commands.count, 1)
        let original = try XCTUnwrap(controller.response?.request)
        XCTAssertEqual(controller.response?.state, .uncertain)
        controller.draft = "A different unsent question"
        controller.useMemory = true
        controller.recoverUncertainResponse()
        try await idle(controller)
        XCTAssertEqual(socket.commands.count, 2)
        guard case .ask(let recovered) = socket.commands.last else { return XCTFail("Expected Ask") }
        XCTAssertEqual(recovered.question_id, original.question_id)
        XCTAssertEqual(recovered.question, original.question)
        XCTAssertFalse(recovered.memory)
        XCTAssertEqual(controller.draft, "A different unsent question")
    }
    func testSavedAnswerSurvivesReadFailureWithoutAnotherGeneration() async throws {
        let socket = SavedThenOfflineCompanion()
        let controller = CompanionController(owner: "owner", makeConnection: { socket })
        controller.draft = "Question"
        controller.send()
        try await idle(controller)
        XCTAssertEqual(controller.response?.state, .saved)
        XCTAssertEqual(controller.response?.text, "Saved answer")
        XCTAssertNotNil(controller.notice)
        controller.recoverUncertainResponse()
        XCTAssertEqual(socket.asks, 1)
        XCTAssertFalse(controller.isBusy)
    }
    func testInvalidInputAndDifferentOwnerCapturePreserveDraftWithoutNetwork() throws {
        let socket = UnavailableCompanion()
        let controller = CompanionController(owner: "owner", makeConnection: { socket })
        controller.draft = "  "
        controller.send()
        XCTAssertEqual(controller.draft, "  ")
        var capture = CaptureSession(id: UUID(), createdAt: Date())
        capture.memoryOwnerID = "someone-else"
        controller.draft = "What was said?"
        controller.send(live: capture)
        XCTAssertTrue(socket.commands.isEmpty)
        XCTAssertEqual(controller.draft, "What was said?")
        XCTAssertNotNil(controller.notice)
    }
}
