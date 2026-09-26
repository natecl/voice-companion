import XCTest

#if os(iOS)
@MainActor
final class CompanionPhoneUITests: XCTestCase {
    func testCompanionAndCaptureNavigation() throws {
        continueAfterFailure = false
        let config = try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"], "Launch with the isolated local companion fixture configuration")
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--companion-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = config
        app.launch()
        defer { app.terminate() }
        let field = app.descendants(matching: .any).matching(identifier: "companionDraft").firstMatch
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        app.buttons["startRecording"].tap()
        XCTAssertTrue(app.buttons["showActiveRecording"].waitForExistence(timeout: 5))
        field.tap(); field.typeText("What does Maya enjoy?")
        app.buttons["sendCompanion"].tap()
        XCTAssertTrue(app.buttons["companionSource"].firstMatch.waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["stopRecording"].isEnabled)
        app.buttons["companionSource"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["citedPassage"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.staticTexts["citedPassage"].label, "Maya enjoys swimming.")
        XCTAssertTrue(app.buttons["stopRecording"].isEnabled)
        app.buttons["backToCompanion"].tap()
        app.buttons["stopRecording"].tap()
        app.buttons["companionSource"].firstMatch.tap()
        XCTAssertTrue(app.buttons["askAboutRecording"].waitForExistence(timeout: 5))
        app.buttons["askAboutRecording"].tap()
        XCTAssertTrue(app.staticTexts["chatAttachment"].exists)
        app.buttons["removeAttachment"].tap()
        let image = XCTAttachment(screenshot: app.screenshot())
        image.name = "iPhone companion navigation — synthetic capture and local service"
        image.lifetime = .keepAlways
        add(image)
        app.terminate()
        app.launchArguments = ["--ui-testing", "--companion-ui-fixture"]
        app.launch()
        XCTAssertTrue(app.buttons["companionSource"].firstMatch.waitForExistence(timeout: 5))
    }
}
#endif
