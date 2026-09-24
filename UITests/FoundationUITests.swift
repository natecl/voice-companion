import XCTest

final class FoundationUITests: XCTestCase {
    func testSessionNavigation() {
        let app = XCUIApplication()
        app.launch()
        let newSession = app.buttons["newSession"]
        XCTAssertTrue(newSession.waitForExistence(timeout: 10))
        newSession.tap()
        XCTAssertTrue(app.staticTexts["transcriptPlaceholder"].waitForExistence(timeout: 5))
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "Session foundation"
        screenshot.lifetime = .keepAlways
        add(screenshot)
        app.buttons["closeSession"].tap()
        XCTAssertTrue(newSession.waitForExistence(timeout: 5))
    }
}
