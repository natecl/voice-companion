import XCTest

@MainActor
final class AskUITests: XCTestCase {
    func testAskSourcesAndHistorySurviveRelaunch() {
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--ask-ui-fixture"]
        app.launch()
        let field = app.descendants(matching: .any).matching(identifier: "askQuestion").firstMatch
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        field.tap()
        field.typeText("When is the appointment?")
        app.buttons["submitQuestion"].tap()
        let source = app.buttons.matching(identifier: "answerSource").firstMatch
        XCTAssertTrue(source.waitForExistence(timeout: 5))
        source.tap()
        XCTAssertTrue(app.staticTexts["The appointment is Tuesday at ten."].waitForExistence(timeout: 3))
        app.buttons["Done"].tap()
        let shot = XCTAttachment(screenshot: app.screenshot())
        shot.name = "Saved conversation Ask with source (fixture, no provider call)"
        shot.lifetime = .keepAlways
        add(shot)
        app.terminate()
        app.launch()
        XCTAssertTrue(app.staticTexts.matching(identifier: "answerText").firstMatch.waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons.matching(identifier: "answerSource").firstMatch.exists)
    }
}
