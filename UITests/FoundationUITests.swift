import XCTest

@MainActor
final class FoundationUITests: XCTestCase {
    func testReplayPersistsAcrossRelaunch() {
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing"]
        app.launch()
        app.buttons["replaySample"].tap()
        XCTAssertTrue(app.staticTexts["sessionStatus"].waitForExistence(timeout: 5))
        let saved = NSPredicate(format: "label == %@ OR value == %@", "Saved", "Saved")
        let completion = XCTNSPredicateExpectation(predicate: saved, object: app.staticTexts["sessionStatus"])
        XCTAssertEqual(XCTWaiter.wait(for: [completion], timeout: 25), .completed)
        XCTAssertEqual(app.descendants(matching: .any).matching(identifier: "transcriptSegment").count, 1)
        let shot = XCTAttachment(screenshot: app.screenshot())
        shot.name = "Final replay transcript"
        shot.lifetime = .keepAlways
        add(shot)
        app.terminate()
        app.launch()
        app.buttons.matching(identifier: "savedSession").firstMatch.tap()
        XCTAssertTrue(app.staticTexts["sessionStatus"].label == "Saved" || app.staticTexts["sessionStatus"].value as? String == "Saved")
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@ OR value CONTAINS %@", "vaccination record", "vaccination record")).firstMatch.exists)
        app.buttons["deleteSession"].tap()
        XCTAssertTrue(app.buttons["replaySample"].exists)
    }

    func testStopPreservesIncompleteSession() {
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing"]
        app.launch()
        app.buttons["replaySample"].tap()
        let partial = app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@ OR value CONTAINS %@", "appointment", "appointment" )).firstMatch
        XCTAssertTrue(partial.waitForExistence(timeout: 8))
        app.buttons["stopReplay"].tap()
        XCTAssertTrue(app.staticTexts["sessionStatus"].label == "Incomplete · saved" || app.staticTexts["sessionStatus"].value as? String == "Incomplete · saved")
        app.buttons["closeSession"].tap()
        app.buttons.matching(identifier: "savedSession").firstMatch.tap()
        XCTAssertTrue(app.staticTexts["sessionStatus"].label == "Incomplete · saved" || app.staticTexts["sessionStatus"].value as? String == "Incomplete · saved")
        XCTAssertTrue(partial.exists)
        app.buttons["deleteSession"].tap()
    }
}
