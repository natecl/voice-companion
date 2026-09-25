import XCTest

@MainActor
private final class FixtureAnswer: AnswerConnection {
    var cancelled = false
    var stall = false
    var badReference = false
    var past: ConversationPassage?
    var invalidated = false
    var requested: ConversationQuestion?
    func run(_ question: ConversationQuestion, onEvent: (AnswerEvent) throws -> Void) async throws {
        requested = question
        if let past {
            try onEvent(AnswerEvent(type: "context", sources: [past], memory_status: "available"))
        }
        try onEvent(AnswerEvent(type: "delta", text: past == nil ? "Noon [[p1]]." : "Morning [[m1]]."))
        if invalidated { throw AskFailure.memoryContextChanged }
        if stall { try await Task.sleep(for: .seconds(20)) }
        try Task.checkCancellation()
        try onEvent(AnswerEvent(type: "done", references: [badReference ? "p99" : (past == nil ? "p1" : "m1")]))
    }
    func cancel() { cancelled = true }
}

@MainActor
final class ConversationAnswerTests: XCTestCase {
    private func waitUntil(_ predicate: () -> Bool) async throws {
        for _ in 0..<200 {
            if predicate() { return }
            try await Task.sleep(for: .milliseconds(5))
        }
        XCTFail("Answer state did not settle")
    }
    private func exercise(_ body: (SessionController, FixtureAnswer, SessionStore) async throws -> Void) async throws {
        let path = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: path) }
        let store = SessionStore(directory: path)
        let connection = FixtureAnswer()
        let controller = SessionController(store: store, makeAnswerConnection: { connection })
        var session = CaptureSession(id: UUID(), createdAt: Date())
        session.completed = true
        session.transcript.segments = [TranscriptSegment(start: 0, duration: 1, text: "We meet at noon.", words: [], isFinal: true)]
        controller.current = session
        try await body(controller, connection, store)
    }
    func testAnswerAndSnapshotSurviveReloadAndDeleteTogether() async throws {
        try await exercise { controller, connection, store in
            controller.ask("What time?")
            try await waitUntil { !controller.isAnswering }
            XCTAssertEqual(connection.requested?.passages.first?.text, "We meet at noon.")
            let saved = try XCTUnwrap(store.load().first)
            XCTAssertEqual(saved.answers?.first?.state, .completed)
            XCTAssertEqual(saved.answers?.first?.references, ["p1"])
            XCTAssertEqual(saved.answers?.first?.question.passages.first?.text, "We meet at noon.")
            controller.deleteCurrent()
            XCTAssertTrue(try store.load().isEmpty)
        }
    }
    func testBackgroundCancelsAnswerAndPreservesPartialText() async throws {
        try await exercise { controller, connection, store in
            connection.stall = true
            controller.ask("What time?")
            try await waitUntil { connection.requested != nil }
            controller.didEnterBackground()
            try await waitUntil { !controller.isAnswering }
            XCTAssertTrue(connection.cancelled)
            let answer = try XCTUnwrap(store.load().first?.answers?.first)
            XCTAssertEqual(answer.state, .cancelled)
            XCTAssertEqual(answer.text, "Noon [[p1]].")
            XCTAssertTrue(answer.notice?.contains("foreground") == true)
        }
    }
    func testUnknownSourcesCannotMarkAnswerComplete() async throws {
        try await exercise { controller, connection, store in
            connection.badReference = true
            controller.ask("What time?")
            try await waitUntil { !controller.isAnswering }
            XCTAssertEqual(try store.load().first?.answers?.first?.state, .failed)
        }
    }
    func testRelaunchMarksUnfinishedAnswerIncomplete() async throws {
        try await exercise { controller, connection, store in
            connection.stall = true
            controller.ask("What time?")
            try await waitUntil { connection.requested != nil }
            let reloaded = try XCTUnwrap(store.load().first?.answers?.first)
            XCTAssertEqual(reloaded.state, .failed)
            controller.cancelAnswer()
            try await waitUntil { !controller.isAnswering }
        }
    }
    func testRejectsEmptyAndOversizedContextWithoutProvider() async throws {
        try await exercise { controller, connection, store in
            controller.ask(" ")
            XCTAssertNil(connection.requested)
            controller.current?.transcript.segments = [TranscriptSegment(start: 0, duration: 1, text: String(repeating: "x", count: 13000), words: [], isFinal: true)]
            controller.ask("Summarize")
            XCTAssertNil(connection.requested)
            XCTAssertNotNil(controller.answerErrorMessage)
            XCTAssertTrue(try store.load().isEmpty)
        }
    }

    func testPastSourcesPersistAndDeletionRemovesDerivedAnswer() async throws {
        try await exercise { controller, connection, store in
            let previous = CaptureSession(id: UUID(), createdAt: Date())
            try store.save(previous)
            connection.past = ConversationPassage(id: "m1", start: 2, text: "Maya prefers mornings.",
                session_id: previous.id.uuidString, revision: 1, captured_at: previous.createdAt.timeIntervalSince1970)
            controller.ask("What does Maya prefer?")
            try await waitUntil { !controller.isAnswering }
            let saved = try XCTUnwrap(store.load().first(where: { $0.id == controller.current?.id }))
            XCTAssertEqual(saved.answers?.first?.references, ["m1"])
            XCTAssertEqual(saved.answers?.first?.pastSources?.first?.session_id, previous.id.uuidString)
            try store.delete(previous.id)
            XCTAssertEqual(try store.load().first?.answers?.count, 0)
        }
    }
    func testInvalidationClearsPartialPastAnswer() async throws {
        try await exercise { controller, connection, store in
            connection.past = ConversationPassage(id: "m1", start: 2, text: "Old fact.",
                session_id: UUID().uuidString, revision: 1, captured_at: 100)
            connection.invalidated = true
            controller.ask("What was said?")
            try await waitUntil { !controller.isAnswering }
            let answer = try XCTUnwrap(store.load().first?.answers?.first)
            XCTAssertEqual(answer.state, .failed)
            XCTAssertEqual(answer.text, "")
            XCTAssertNil(answer.pastSources)
        }
    }

    func testInitialSaveFailureDoesNotStartOrDisplayPendingAnswer() async throws {
        try await exercise { controller, connection, store in
            // A file at the store's directory makes persistence fail deterministically.
            try Data().write(to: store.directory)
            controller.ask("What time?")
            XCTAssertFalse(controller.isAnswering)
            XCTAssertNil(connection.requested)
            XCTAssertTrue(controller.current?.answers?.isEmpty ?? true)
            XCTAssertNotNil(controller.answerErrorMessage)
        }
    }
}
