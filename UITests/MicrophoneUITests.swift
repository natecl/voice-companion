import XCTest

/// Opt-in hardware regression check. No relay or paid provider is involved.
@MainActor
final class MicrophoneUITests: XCTestCase {
    /// Run only after the founder disables this app's microphone permission in system settings.
    func testDeniedPermissionShowsRecoveryWithoutCreatingSession() {
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing"]
        app.launch()
        XCTAssertTrue(app.buttons["startRecording"].waitForExistence(timeout: 5))
        let originalCount = app.buttons.matching(identifier: "savedSession").count
        for _ in 0..<2 {
            app.buttons["startRecording"].tap()
            let denied = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label CONTAINS %@ OR value CONTAINS %@", "Microphone access is off", "Microphone access is off"), object: app.staticTexts["sessionError"])
            XCTAssertEqual(XCTWaiter.wait(for: [denied], timeout: 5), .completed)
            XCTAssertTrue(app.buttons["startRecording"].isEnabled)
            XCTAssertFalse(app.buttons["stopRecording"].exists)
            XCTAssertEqual(app.buttons.matching(identifier: "savedSession").count, originalCount)
        }
        let shot = XCTAttachment(screenshot: app.screenshot())
        shot.name = "Actual OS microphone permission denied"
        shot.lifetime = .keepAlways
        add(shot)
        app.terminate()
    }

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
        XCTAssertFalse(app.buttons["startRecording"].exists)
        XCTAssertFalse(app.buttons["replaySample"].exists)
        app.terminate()
    }
}
