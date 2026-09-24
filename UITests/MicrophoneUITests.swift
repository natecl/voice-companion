#if os(macOS)
import XCTest

/// Opt-in hardware regression check. No relay or paid provider is involved.
@MainActor
final class MicrophoneUITests: XCTestCase {
    func testAudioCallbackRunsAndStopsWithoutUpload() {
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--microphone-check"]
        app.launch()
        let result = app.staticTexts["microphoneCheck"]
        let completed = NSPredicate(format: "label CONTAINS %@ OR value CONTAINS %@", "Capture stopped", "Capture stopped")
        let expectation = XCTNSPredicateExpectation(predicate: completed, object: result)
        XCTAssertEqual(XCTWaiter.wait(for: [expectation], timeout: 12), .completed)
        let text = result.value as? String ?? result.label
        XCTAssertFalse(text.contains(": 0 PCM bytes"))
        XCTAssertTrue(text.contains("No upload"))
        app.terminate()
    }
}
#endif
