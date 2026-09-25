import XCTest

@MainActor
private final class LiveAskRecording: RecordingConnection {
    let events = AsyncThrowingStream<GrokEvent, Error>.makeStream()
    var stopped = false
    var cancelled = false
    var finishing: ((RecordingStopReason) -> Void)?
    func run(onReady: (Duration) -> Void, onFinishing: @escaping (RecordingStopReason) -> Void,
             onEvent: (GrokEvent) throws -> Void) async throws {
        finishing = onFinishing
        onReady(.seconds(300))
        for try await event in events.stream { try onEvent(event) }
    }
    func emit(_ text: String, start: Double = 0, duration: Double = 2, final: Bool = false) {
        events.continuation.yield(GrokEvent(type: "transcript.partial", text: text, words: [], start: start, duration: duration, is_final: final))
    }
    func stop() { stopped = true; finishing?(.user); events.continuation.finish() }
    func cancel() { cancelled = true; events.continuation.finish(throwing: CancellationError()) }
}

@MainActor
private final class LiveAskAnswer: AnswerConnection {
    let events = AsyncThrowingStream<AnswerEvent, Error>.makeStream()
    var requested: ConversationQuestion?
    var calls = 0
    var cancelled = false
    func run(_ question: ConversationQuestion, onEvent: (AnswerEvent) throws -> Void) async throws {
        calls += 1; requested = question
        for try await event in events.stream { try onEvent(event) }
    }
    func complete() {
        events.continuation.yield(AnswerEvent(type: "delta", text: "Tuesday [[p1]]."))
        events.continuation.yield(AnswerEvent(type: "done", references: ["p1"]))
        events.continuation.finish()
    }
    func cancel() { cancelled = true; events.continuation.finish(throwing: CancellationError()) }
}

@MainActor
final class LiveAskTests: XCTestCase {
    private func until(_ predicate: () -> Bool) async throws {
        for _ in 0..<200 {
            if predicate() { return }
            try await Task.sleep(for: .milliseconds(5))
        }
        XCTFail("Live Ask state did not settle")
    }
    private func exercise(_ body: (SessionController, LiveAskRecording, LiveAskAnswer, SessionStore) async throws -> Void) async throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = SessionStore(directory: directory)
        let recording = LiveAskRecording(); let answer = LiveAskAnswer()
        let controller = SessionController(store: store, allowsBackgroundRecording: true,
            makeAnswerConnection: { answer }, makeConnection: { recording }, prepareRecording: {})
        controller.startRecording()
        try await until { controller.liveStatus == "Recording" }
        XCTAssertFalse(controller.canAsk)
        recording.emit("The appointment is Tuesday.")
        try await until { controller.canAsk }
        try await body(controller, recording, answer, store)
        if controller.isAnswering { controller.cancelAnswer(); try await until { !controller.isAnswering } }
        if controller.liveStatus != nil { controller.stop(); try await until { controller.liveStatus == nil } }
    }
    func testSnapshotSurvivesTranscriptRevisionLaterSpeechAndReload() async throws {
        try await exercise { controller, recording, answer, store in
            controller.ask("When is the appointment?")
            try await until { answer.requested != nil }
            recording.emit("The appointment is Wednesday.", final: true)
            recording.emit("Bring the blue folder.", start: 3, duration: 2, final: true)
            try await until { controller.current?.transcript.segments.count == 2 }
            answer.complete()
            try await until { !controller.isAnswering }
            XCTAssertEqual(controller.liveStatus, "Recording")
            XCTAssertFalse(recording.stopped)
            controller.stop(); try await until { !controller.isActive }
            let saved = try XCTUnwrap(store.load().first)
            XCTAssertEqual(saved.transcript.segments.first?.text, "The appointment is Wednesday.")
            let qa = try XCTUnwrap(saved.answers?.first)
            XCTAssertEqual(qa.question.passages.count, 1)
            XCTAssertEqual(qa.question.passages.first?.text, "The appointment is Tuesday.")
            XCTAssertEqual(qa.transcriptCutoffSeconds, 2)
            XCTAssertEqual(qa.capturedWhileRecording, true)
            XCTAssertEqual(qa.includedInterimText, true)
            XCTAssertEqual(qa.state, .completed)
            XCTAssertEqual(qa.references, ["p1"])
        }
    }
    func testStopCaptureDoesNotCancelAnswer() async throws {
        try await exercise { controller, recording, answer, store in
            controller.ask("When?"); try await until { answer.requested != nil }
            controller.stop()
            XCTAssertTrue(recording.stopped)
            XCTAssertFalse(answer.cancelled)
            try await until { controller.liveStatus == nil }
            XCTAssertTrue(controller.isAnswering)
            answer.complete(); try await until { !controller.isAnswering }
            XCTAssertEqual(try store.load().first?.answers?.first?.state, .completed)
        }
    }
    func testCancelAnswerDoesNotStopCaptureOrAllowDuplicateAsk() async throws {
        try await exercise { controller, recording, answer, store in
            controller.ask("When?"); try await until { answer.requested != nil }
            controller.ask("A duplicate?")
            XCTAssertEqual(answer.calls, 1)
            controller.cancelAnswer(); try await until { !controller.isAnswering }
            XCTAssertFalse(recording.cancelled); XCTAssertFalse(recording.stopped)
            XCTAssertEqual(controller.liveStatus, "Recording")
            recording.emit("Later words.", start: 3)
            try await until { controller.current?.transcript.segments.count == 2 }
            XCTAssertEqual(try store.load().first?.answers?.first?.state, .cancelled)
        }
    }
    func testRecordingFailureRemainsVisibleWhileAnswerCompletes() async throws {
        try await exercise { controller, recording, answer, store in
            controller.ask("When?"); try await until { answer.requested != nil }
            recording.events.continuation.finish(throwing: CaptureFailure.connectionEnded)
            try await until { controller.liveStatus == nil }
            XCTAssertFalse(answer.cancelled)
            answer.complete(); try await until { !controller.isAnswering }
            let saved = try XCTUnwrap(store.load().first)
            XCTAssertFalse(saved.completed)
            XCTAssertNotNil(saved.endReason); XCTAssertNotNil(controller.errorMessage)
            XCTAssertEqual(saved.answers?.first?.state, .completed)
        }
    }
    func testAnswerFailureLeavesCaptureRunning() async throws {
        try await exercise { controller, recording, answer, store in
            controller.ask("When?"); try await until { answer.requested != nil }
            answer.events.continuation.finish(throwing: AskFailure.unavailable)
            try await until { !controller.isAnswering }
            XCTAssertEqual(controller.liveStatus, "Recording")
            XCTAssertFalse(recording.cancelled)
            XCTAssertEqual(try store.load().first?.answers?.first?.state, .failed)
        }
    }
    func testBackgroundCancelsOnlyAnswerWhenCaptureSupportsBackground() async throws {
        try await exercise { controller, recording, answer, store in
            controller.ask("When?"); try await until { answer.requested != nil }
            controller.didEnterBackground(); try await until { !controller.isAnswering }
            XCTAssertTrue(answer.cancelled); XCTAssertFalse(recording.cancelled)
            XCTAssertEqual(controller.liveStatus, "Recording")
            XCTAssertEqual(try store.load().first?.answers?.first?.state, .cancelled)
        }
    }
}
