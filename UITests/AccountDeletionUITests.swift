import XCTest
#if os(iOS)
@MainActor final class AccountDeletionUITests: XCTestCase {
    func testExistingProfileConfirmationAndRetryPresentation() {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchArguments = ["--account-deletion-ui-fixture"]
        app.launch(); defer { app.terminate() }
        let web = app.webViews.firstMatch
        XCTAssertTrue(web.buttons["Your profile"].waitForExistence(timeout: 10))
        web.buttons["Your profile"].tap()
        XCTAssertTrue(web.buttons["Delete account"].waitForExistence(timeout: 5))
        shot(app, "Account profile — existing rows")
        web.buttons["Delete account"].tap()
        XCTAssertTrue(web.staticTexts["This removes your recordings, notes, conversations and memories. You cannot undo this."].waitForExistence(timeout: 5))
        shot(app, "Account deletion — existing confirmation panel")
        web.buttons["Cancel"].tap()
        XCTAssertTrue(web.buttons["Your profile"].waitForExistence(timeout: 5))
        web.buttons["Your profile"].tap()
        web.buttons["Delete account"].tap()
        web.buttons["Delete account"].tap()
        XCTAssertTrue(app.buttons["Retry deletion"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["Continue with Google"].exists)
        shot(app, "Account deletion — pending retry")
        app.buttons["Retry deletion"].tap()
        let google = app.buttons["Continue with Google"]
        let apple = app.buttons["Continue with Apple"]
        XCTAssertTrue(google.waitForExistence(timeout: 5))
        XCTAssertTrue(apple.exists)
        XCTAssertLessThan(google.frame.minY, apple.frame.minY)
        shot(app, "Account deletion — provider recovery")
    }

    func testDisabledCapabilityHidesDeletion() {
        let app = XCUIApplication()
        app.launchArguments = ["--account-deletion-ui-fixture", "--deletion-ui-disabled"]
        app.launch(); defer { app.terminate() }
        let web = app.webViews.firstMatch
        XCTAssertTrue(web.buttons["Your profile"].waitForExistence(timeout: 10))
        web.buttons["Your profile"].tap()
        XCTAssertTrue(web.buttons["Sign out"].waitForExistence(timeout: 5))
        XCTAssertFalse(web.buttons["Delete account"].exists)
    }

    private func shot(_ app: XCUIApplication, _ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways
        add(attachment)
    }
}
#endif
