import Foundation
import XCTest

@MainActor
final class CompanionConnectionTests: XCTestCase {
    func testExplicitNullsAndScalarLimit() throws {
        let request = try CompanionQuestion(question: "Hello")
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(request)) as? [String: Any])
        XCTAssertTrue(object["attachment"] is NSNull)
        XCTAssertTrue(object["live"] is NSNull)
        let history = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(CompanionCommand.history())) as? [String: Any])
        XCTAssertTrue(history["before"] is NSNull)
        XCTAssertThrowsError(try CompanionQuestion(question: String(repeating: "👨‍👩‍👧‍👦", count: 200)))
    }
    func testRejectsFalseCompletionAndOutOfOrderEvents() throws {
        let question = try CompanionQuestion(question: "Hello")
        var sequence = CompanionEventSequence(command: .ask(question))
        func event(_ data: [String: Any]) throws -> CompanionEvent {
            try JSONDecoder().decode(CompanionEvent.self, from: JSONSerialization.data(withJSONObject: data))
        }
        XCTAssertThrowsError(try sequence.accept(event(["type":"delta", "text":"early"])))
        XCTAssertFalse(try sequence.accept(event(["type":"accepted", "question_id":question.question_id, "conversation_id":"main"])))
        XCTAssertFalse(try sequence.accept(event(["type":"context", "sources":[]])))
        XCTAssertFalse(try sequence.accept(event(["type":"delta", "text":"Hello"])))
        XCTAssertThrowsError(try sequence.accept(event(["type":"done", "question_id":question.question_id, "saved":false, "references":[]])))
        XCTAssertThrowsError(try sequence.accept(event(["type":"done", "question_id":question.question_id, "saved":true, "references":["p999"]])))
        XCTAssertTrue(try sequence.accept(event(["type":"done", "question_id":question.question_id, "saved":true, "references":[]])))
    }
    func testLiveCutoffIncludesInterimWithoutChangingDurableEvidence() throws {
        var session = CaptureSession(id: UUID(), createdAt: Date())
        session.transcript.segments = [
            TranscriptSegment(start: 0, duration: 1, text: "Maya swims.", words: [], isFinal: true),
            TranscriptSegment(start: 1, duration: 1, text: "And paints", words: [], isFinal: false)]
        let live = MemorySource(live: session, revision: 1)
        session.transcript.segments[1] = TranscriptSegment(start: 1, duration: 1, text: "Revised words", words: [], isFinal: false)
        XCTAssertEqual(live.passages.map(\.text), ["Maya swims.", "And paints"])
        XCTAssertEqual(live.passages.map(\.id), ["p1", "p2"])
        XCTAssertFalse(live.completed)
        XCTAssertNil(live.origin)
        XCTAssertEqual(MemorySource(session, revision: 1).passages.count, 1)
    }
    func testRealServiceStreamDuplicateAndReopen() async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let fixture = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("Backend/companion_fixture.py")
        let process = Process()
        let python = ProcessInfo.processInfo.environment["VOICE_TEST_PYTHON"] ?? "/usr/bin/env"
        process.executableURL = URL(fileURLWithPath: python)
        process.arguments = (python == "/usr/bin/env" ? ["python3"] : []) + [fixture.path, directory.path]
        process.standardOutput = FileHandle.nullDevice
        try process.run()
        defer { if process.isRunning { process.terminate() }; process.waitUntilExit() }
        let configFile = directory.appendingPathComponent("config.json")
        for _ in 0..<500 {
            if FileManager.default.fileExists(atPath: configFile.path) || !process.isRunning { break }
            try await Task.sleep(for: .milliseconds(10))
        }
        let config = try JSONDecoder().decode(RelayConfiguration.self, from: Data(contentsOf: configFile))
        let question = try CompanionQuestion(question: "Hello", memory: false)
        let connection = CompanionSocketConnection(configuration: { config })
        var events: [CompanionEvent] = []
        try await connection.run(.ask(question)) { events.append($0) }
        XCTAssertEqual(events.map(\.type), ["accepted", "context", "delta", "done"])
        XCTAssertEqual(events.last?.saved, true)
        events = []
        try await connection.run(.ask(question)) { events.append($0) }
        XCTAssertEqual(events.map(\.type), ["existing"])
        XCTAssertEqual(events.first?.turn?.state, .complete)
        let reopened = CompanionSocketConnection(configuration: { config })
        events = []
        try await reopened.run(.history()) { events.append($0) }
        XCTAssertEqual(events.first?.turns?.count, 1)
        XCTAssertEqual(events.first?.turns?.first?.answer, "Hello from the saved companion.")
        var capture = CaptureSession(id: UUID(), createdAt: Date())
        capture.captureTimezone = "UTC"
        capture.transcript.segments = [TranscriptSegment(start: 0, duration: 1, text: "Maya swims.", words: [], isFinal: false)]
        let liveQuestion = try CompanionQuestion(question: "What does Maya do?", live: MemorySource(live: capture, revision: 1))
        events = []
        try await reopened.run(.ask(liveQuestion)) { events.append($0) }
        XCTAssertEqual(events.last?.references, ["p1"])
        events = []
        try await reopened.run(.history()) { events.append($0) }
        let liveTurn = try XCTUnwrap(events.first?.turns?.first(where: { $0.id == liveQuestion.question_id }))
        XCTAssertNotNil(liveTurn.citations.first?.source.snapshot_id)
        XCTAssertEqual(liveTurn.citations.first?.source.session_id, capture.id.uuidString)
        let owner = try XCTUnwrap(config.memoryOwnerID)
        let controller = CompanionController(owner: owner, makeConnection: { CompanionSocketConnection(configuration: { config }) })
        controller.draft = "A new companion question"
        controller.send()
        controller.draft = "An unsent follow-up"
        for _ in 0..<500 {
            if !controller.isBusy { break }
            try await Task.sleep(for: .milliseconds(10))
        }
        XCTAssertFalse(controller.isBusy)
        XCTAssertNil(controller.notice)
        XCTAssertNil(controller.response)
        XCTAssertEqual(controller.turns.last?.question, "A new companion question")
        XCTAssertEqual(controller.draft, "An unsent follow-up")
        let restored = CompanionController(owner: owner, makeConnection: { CompanionSocketConnection(configuration: { config }) })
        restored.refresh()
        for _ in 0..<500 {
            if !restored.isBusy { break }
            try await Task.sleep(for: .milliseconds(10))
        }
        XCTAssertEqual(restored.turns.map(\.id), controller.turns.map(\.id))
        print("Companion controller QA: send -> durable history -> draft preserved -> new controller restored")
        let stalled = try CompanionQuestion(question: "Wait forever", memory: false)
        let task = Task {
            try await reopened.run(.ask(stalled)) { event in
                if event.type == "delta" { reopened.cancel() }
            }
        }
        do { try await task.value; XCTFail("Cancelled socket must not complete") } catch { }
        print("Companion socket QA: stream/save, duplicate recovery, reopened history, frozen live citation, cancellation verified")
    }
}
