import XCTest

@MainActor
private final class HistoryStub: CompanionConnection {
    let events = AsyncThrowingStream<CompanionEvent, Error>.makeStream()
    func run(_ command: CompanionCommand, onEvent: (CompanionEvent) throws -> Void) async throws {
        for try await event in events.stream { try onEvent(event) }
    }
    func cancel() { events.continuation.finish(throwing: CancellationError()) }
}

@MainActor
final class CompanionRefreshTests: XCTestCase {
    private func settle() async { for _ in 0..<30 { await Task.yield() } }
    func testRefreshKeepsVisibleHistoryAndDraftUntilReplacementThenReportsSuccess() async throws {
        let first = HistoryStub(); let second = HistoryStub(); var calls = 0
        let chat = CompanionController(owner: "test") { calls += 1; return calls == 1 ? first : second }
        let event = try JSONDecoder().decode(CompanionEvent.self, from: Data(#"{"type":"history","conversation_id":"main","turns":[{"id":"one","sequence":1,"question":"Hello","state":"complete","answer":"Hi","created_at":0,"citations":[]}]}"#.utf8))
        chat.refresh(); first.events.continuation.yield(event); first.events.continuation.finish(); await settle()
        XCTAssertEqual(chat.turns.count, 1)
        chat.draft = "Keep this"
        chat.refresh(userInitiated: true); await settle()
        XCTAssertEqual(chat.turns.count, 1); XCTAssertTrue(chat.isRefreshing)
        XCTAssertEqual(chat.refreshStatus, "Refreshing conversation…")
        second.events.continuation.yield(event); second.events.continuation.finish(); await settle()
        XCTAssertFalse(chat.isRefreshing); XCTAssertEqual(chat.draft, "Keep this")
        XCTAssertEqual(chat.refreshStatus, "Conversation is up to date.")
    }
    func testFailedRefreshClearsUnvalidatedHistoryButKeepsDraftAndShowsError() async throws {
        let first = HistoryStub(); let socket = HistoryStub(); var calls = 0
        let chat = CompanionController(owner: "test") { calls += 1; return calls == 1 ? first : socket }
        let event = try JSONDecoder().decode(CompanionEvent.self, from: Data(#"{"type":"history","conversation_id":"main","turns":[{"id":"one","sequence":1,"question":"Hello","state":"complete","answer":"Hi","created_at":0,"citations":[]}]}"#.utf8))
        chat.refresh(); first.events.continuation.yield(event); first.events.continuation.finish(); await settle()
        XCTAssertEqual(chat.turns.count, 1)
        chat.draft = "Keep this"
        chat.refresh(userInitiated: true); await settle()
        socket.events.continuation.finish(throwing: CompanionFailure.unavailable); await settle()
        XCTAssertTrue(chat.turns.isEmpty); XCTAssertFalse(chat.isRefreshing)
        XCTAssertEqual(chat.draft, "Keep this"); XCTAssertNotNil(chat.notice); XCTAssertNil(chat.refreshStatus)
    }
}
