import XCTest
import Speech

@MainActor
final class DictationCallbackTests: XCTestCase {
    func testAuthorizationReturnsFromBackgroundQueueForAllowAndDeny() async {
        for status in [SFSpeechRecognizerAuthorizationStatus.authorized, .denied] {
            let received = await withCheckedContinuation { continuation in
                let callback = AppleDictationRecognizer.authorizationHandler(continuation)
                DispatchQueue.global().async { callback(status) }
            }
            XCTAssertEqual(received, status)
        }
    }

    func testRecognitionErrorFromBackgroundQueueFinishesStream() async {
        let (stream, continuation) = AsyncThrowingStream<DictationEvent, Error>.makeStream()
        let callback = AppleDictationRecognizer.resultHandler(continuation)
        DispatchQueue.global().async {
            callback(nil, nil) // A callback without a result or error is not completion.
            callback(nil, DictationFailure.unavailable)
        }
        do {
            for try await _ in stream { XCTFail("Unexpected recognition text") }
            XCTFail("Expected interruption")
        } catch {
            XCTAssertEqual(error.localizedDescription, DictationFailure.interrupted.localizedDescription)
        }
    }
}
