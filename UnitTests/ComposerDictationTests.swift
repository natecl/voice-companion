import XCTest

@MainActor
private final class DictationStub: DictationRecognizing {
    let events = AsyncThrowingStream<DictationEvent, Error>.makeStream()
    var failure: Error?
    var finished = false
    var cancelled = false
    func start() async throws -> AsyncThrowingStream<DictationEvent, Error> {
        if let failure { throw failure }; return events.stream
    }
    func finish() { finished = true }
    func cancel() { cancelled = true; events.continuation.finish() }
}

@MainActor
final class ComposerDictationTests: XCTestCase {
    private func settle() async { for _ in 0..<20 { await Task.yield() } }

    func testStopAppendsOnlyFinalRevisionAndDoesNotSend() async {
        let speech = DictationStub(); let composer = ComposerDictation(makeRecognizer: { speech })
        var draft = "Already typed:"; var sends = 0
        composer.start { text, send in draft = ComposerDictation.appending(text, to: draft); if send { sends += 1 } }
        await settle()
        speech.events.continuation.yield(.init(text: "What day", isFinal: false)); await settle()
        XCTAssertEqual(composer.text, "What day"); XCTAssertEqual(draft, "Already typed:")
        composer.finish(send: false)
        speech.events.continuation.yield(.init(text: "What day is the appointment?", isFinal: true)); await settle()
        XCTAssertEqual(draft, "Already typed: What day is the appointment?")
        XCTAssertEqual(sends, 0); XCTAssertFalse(composer.isActive)
    }

    func testEmptyFinalAfterVisibleSpeechPreservesDraftAndNeverSends() async {
        for send in [false, true] {
            let speech = DictationStub(); let composer = ComposerDictation(makeRecognizer: { speech })
            var draft = "Already typed:"; var sends = 0
            composer.start { text, shouldSend in
                draft = ComposerDictation.appending(text, to: draft)
                if shouldSend { sends += 1 }
            }
            await settle()
            speech.events.continuation.yield(.init(text: "Tomorrow I want to take a walk and call Maya.", isFinal: false))
            await settle()
            speech.events.continuation.yield(.init(text: "  ", isFinal: false))
            await settle()
            XCTAssertEqual(composer.text, "Tomorrow I want to take a walk and call Maya.")
            composer.finish(send: send)
            speech.events.continuation.yield(.init(text: "", isFinal: true))
            await settle()
            XCTAssertEqual(draft, "Already typed: Tomorrow I want to take a walk and call Maya.")
            XCTAssertEqual(sends, 0)
            XCTAssertNotNil(composer.notice)
        }
    }

    func testSendWaitsForFinalWordsAndSendsOnce() async {
        let speech = DictationStub(); let composer = ComposerDictation(makeRecognizer: { speech })
        var results: [(String, Bool)] = []
        composer.start { results.append(($0, $1)) }; await settle()
        speech.events.continuation.yield(.init(text: "What did", isFinal: false)); await settle()
        composer.finish(send: true); composer.finish(send: true)
        XCTAssertTrue(results.isEmpty); XCTAssertTrue(speech.finished)
        speech.events.continuation.yield(.init(text: "What did Maya say?", isFinal: true)); await settle()
        XCTAssertEqual(results.count, 1); XCTAssertEqual(results.first?.0, "What did Maya say?"); XCTAssertEqual(results.first?.1, true)
    }

    func testFailureAndNavigationNeverSendPartial() async {
        for interrupted in [false, true] {
            let speech = DictationStub(); let composer = ComposerDictation(makeRecognizer: { speech })
            var results: [(String, Bool)] = []
            composer.start { results.append(($0, $1)) }; await settle()
            speech.events.continuation.yield(.init(text: "Keep these words", isFinal: false)); await settle()
            composer.finish(send: true)
            if interrupted { composer.interrupt() }
            else { speech.events.continuation.finish(throwing: DictationFailure.interrupted) }
            await settle()
            XCTAssertEqual(results.count, 1); XCTAssertEqual(results.first?.0, "Keep these words"); XCTAssertEqual(results.first?.1, false)
            XCTAssertNotNil(composer.notice)
        }
    }

    func testFinalizationTimeoutPreservesDraftWithoutSend() async throws {
        let speech = DictationStub()
        let composer = ComposerDictation(finalizationLimit: .milliseconds(10), makeRecognizer: { speech })
        var send: Bool?; var text: String?
        composer.start { text = $0; send = $1 }; await settle()
        speech.events.continuation.yield(.init(text: "Still here", isFinal: false)); await settle()
        composer.finish(send: true)
        try await Task.sleep(for: .milliseconds(50))
        XCTAssertEqual(text, "Still here"); XCTAssertEqual(send, false); XCTAssertTrue(speech.cancelled)
    }

    func testDiscardCancelsPendingSendAndIgnoresLateFinal() async {
        let speech = DictationStub(); let composer = ComposerDictation(makeRecognizer: { speech })
        var completions = 0
        composer.start { _, _ in completions += 1 }; await settle()
        speech.events.continuation.yield(.init(text: "Discard these words", isFinal: false)); await settle()
        composer.finish(send: true)
        composer.discard()
        speech.events.continuation.yield(.init(text: "Late final", isFinal: true)); await settle()
        XCTAssertEqual(completions, 0)
        XCTAssertEqual(composer.text, "")
        XCTAssertFalse(composer.isActive)
        XCTAssertTrue(speech.cancelled)
        XCTAssertNil(composer.notice)
    }

    func testDeniedPermissionKeepsExistingDraftAndDoesNotSend() async {
        let speech = DictationStub(); speech.failure = DictationFailure.permission
        let composer = ComposerDictation(makeRecognizer: { speech })
        var draft = "Keep my draft"; var sent = false
        composer.start { text, send in draft = ComposerDictation.appending(text, to: draft); sent = send }
        await settle()
        XCTAssertFalse(composer.isActive); XCTAssertFalse(sent)
        XCTAssertEqual(draft, "Keep my draft"); XCTAssertNotNil(composer.notice)
    }

    func testOldCallbackCannotAppendToNewDictation() async {
        let first = DictationStub(); let second = DictationStub(); var calls = 0
        let composer = ComposerDictation(makeRecognizer: { calls += 1; return calls == 1 ? first : second })
        var results: [String] = []
        composer.start { text, _ in results.append(text) }; await settle()
        composer.interrupt()
        composer.start { text, _ in results.append(text) }; await settle()
        first.events.continuation.yield(.init(text: "Stale text", isFinal: true))
        second.events.continuation.yield(.init(text: "New text", isFinal: true)); await settle()
        XCTAssertEqual(results, ["", "New text"])
    }

    func testNaturalFinalAndEmptySpeechDoNotAutoSend() async {
        for text in ["A sentence", ""] {
            let speech = DictationStub(); let composer = ComposerDictation(makeRecognizer: { speech })
            var send: Bool?
            composer.start { _, value in send = value }; await settle()
            speech.events.continuation.yield(.init(text: text, isFinal: true)); await settle()
            XCTAssertEqual(send, false)
        }
    }
}

@MainActor
private final class MicrophoneStub: AudioCapture {
    var starts = 0; var stops = 0
    var events = AsyncThrowingStream<Data, Error>.makeStream()
    func start() throws -> AsyncThrowingStream<Data, Error> {
        starts += 1; events = AsyncThrowingStream<Data, Error>.makeStream(); return events.stream
    }
    func stop() { stops += 1; events.continuation.finish() }
}

@MainActor
final class SharedMicrophoneTests: XCTestCase {
    func testDictationStopDoesNotStopMeetingAndReverse() async throws {
        for stopMeetingFirst in [false, true] {
            let hardware = MicrophoneStub(); let hub = SharedMicrophone(capture: hardware)
            let meeting = SharedMicrophoneCapture(hub: hub); let dictation = SharedMicrophoneCapture(hub: hub)
            var meetingStream = try meeting.start().makeAsyncIterator()
            var dictationStream = try dictation.start().makeAsyncIterator()
            XCTAssertEqual(hardware.starts, 1)
            hardware.events.continuation.yield(Data([1, 2]))
            let a = try await meetingStream.next(); let b = try await dictationStream.next()
            XCTAssertEqual(a, b)
            if stopMeetingFirst { meeting.stop() } else { dictation.stop() }
            XCTAssertEqual(hardware.stops, 0)
            hardware.events.continuation.yield(Data([3, 4]))
            let next = try await (stopMeetingFirst ? dictationStream.next() : meetingStream.next())
            XCTAssertEqual(next, Data([3, 4]))
            meeting.stop(); dictation.stop(); XCTAssertEqual(hardware.stops, 1)
        }
    }

    func testHardwareInterruptionReachesBothConsumersAndCanRestart() async throws {
        let hardware = MicrophoneStub(); let hub = SharedMicrophone(capture: hardware)
        let first = SharedMicrophoneCapture(hub: hub); let second = SharedMicrophoneCapture(hub: hub)
        var a = try first.start().makeAsyncIterator(); var b = try second.start().makeAsyncIterator()
        hardware.events.continuation.finish(throwing: CaptureFailure.interrupted)
        do { _ = try await a.next(); XCTFail("Missing interruption") } catch {}
        do { _ = try await b.next(); XCTFail("Missing interruption") } catch {}
        first.stop(); second.stop()
        _ = try first.start(); XCTAssertEqual(hardware.starts, 2); first.stop()
    }
}
