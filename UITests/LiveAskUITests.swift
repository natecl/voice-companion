import XCTest

@MainActor
final class LiveAskUITests: XCTestCase {
    func testAskDuringRecordingShowsCutoffAndStopRemainsIndependent() {
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--live-ask-ui-fixture"]
        app.launch()
        app.buttons["startRecording"].tap()
        XCTAssertTrue(app.staticTexts["liveAskNotice"].waitForExistence(timeout: 5))
        let field = app.descendants(matching: .any).matching(identifier: "askQuestion").firstMatch
        field.tap(); field.typeText("When is the appointment?")
        app.buttons["submitQuestion"].tap()
        XCTAssertTrue(app.staticTexts["answerCutoff"].waitForExistence(timeout: 3))
        XCTAssertEqual(app.staticTexts["answerCutoff"].label, "Transcript snapshot through 2.0s")
        XCTAssertTrue(app.buttons["stopRecording"].isEnabled)
        XCTAssertTrue(app.buttons["cancelAnswer"].exists)
        app.buttons["stopRecording"].tap()
        XCTAssertTrue(app.buttons["answerSource"].waitForExistence(timeout: 6))
        XCTAssertFalse(app.buttons["stopRecording"].exists)
        app.buttons["answerSource"].tap()
        XCTAssertTrue(app.staticTexts["The appointment is Tuesday at ten."].waitForExistence(timeout: 3))
        app.buttons["Done"].tap()
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Live Ask cutoff and independent Stop — fixture, microphone off"
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
