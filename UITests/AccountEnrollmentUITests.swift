import XCTest

@MainActor
final class AccountEnrollmentUITests: XCTestCase {
    func testFreshInstallShowsExistingGoogleThenAppleControls() {
        let app = XCUIApplication()
        app.launchArguments = ["--account-ui-check"]
        app.launch()
        let google = app.buttons["Continue with Google"]
        let apple = app.buttons["Continue with Apple"]
        XCTAssertTrue(google.waitForExistence(timeout: 10))
        XCTAssertTrue(apple.exists)
        XCTAssertTrue(app.staticTexts["Choose Google or Apple to sign in."].exists)
        XCTAssertTrue(google.isEnabled)
        XCTAssertTrue(apple.isEnabled)
        XCTAssertLessThan(google.frame.minY, apple.frame.minY)
        XCTAssertFalse(app.staticTexts["Design preview · sign-in is not connected."].exists)
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "Fresh account screen — existing components"
        screenshot.lifetime = .keepAlways
        add(screenshot)
    }
}
