import XCTest

#if os(iOS)
@MainActor
final class RecordingNotesPhoneUITests: XCTestCase {
    func testNotesSupportingPassageRelaunchAndDeletion() throws {
        continueAfterFailure = false
        let config = try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"])
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--companion-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = config
        app.launch()
        defer { app.terminate() }
        app.buttons["startRecording"].tap()
        XCTAssertTrue(app.buttons["stopRecording"].waitForExistence(timeout: 5))
        app.buttons["stopRecording"].tap()
        app.buttons["Recordings"].tap()
        XCTAssertTrue(app.buttons["savedSession"].firstMatch.waitForExistence(timeout: 5))
        app.buttons["savedSession"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["notesTitle"].waitForExistence(timeout: 15))
        XCTAssertEqual(app.staticTexts["notesTitle"].label, "Maya’s swimming")
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "Recording notes — actual native app and local service, synthetic input"
        screenshot.lifetime = .keepAlways; add(screenshot)
        app.buttons["notesPassage"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["notesSupportingPassage"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.staticTexts["notesSupportingPassage"].label, "Maya enjoys swimming.")
        app.terminate()
        app.launchArguments = ["--ui-testing", "--companion-ui-fixture"]
        app.launch()
        app.buttons["Recordings"].tap()
        XCTAssertTrue(app.buttons["savedSession"].firstMatch.waitForExistence(timeout: 5))
        app.buttons["savedSession"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["notesTitle"].waitForExistence(timeout: 10))
        app.buttons["deleteSession"].tap(); app.alerts.buttons["confirmDeleteSession"].firstMatch.tap()
        XCTAssertFalse(app.buttons["savedSession"].firstMatch.exists)
    }
}
#endif
