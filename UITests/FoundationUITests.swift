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
        XCTAssertTrue(app.windows.buttons["Cancel"].firstMatch.waitForExistence(timeout: 3))
        let confirmation = XCTAttachment(screenshot: app.screenshot())
        confirmation.name = "Delete confirmation"
        confirmation.lifetime = .keepAlways
        add(confirmation)
        app.windows.buttons["Cancel"].firstMatch.tap()
        app.terminate()
        app.launch()
        app.buttons.matching(identifier: "savedSession").firstMatch.tap()
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@ OR value CONTAINS %@", "vaccination record", "vaccination record")).firstMatch.exists)
        app.buttons["deleteSession"].tap()
        app.windows.buttons["confirmDeleteSession"].firstMatch.tap()
        XCTAssertTrue(app.buttons["replaySample"].exists)
    }

    func testRecordingTimerAndAutomaticStopNoticeSurviveRelaunch() {
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--recording-ui-fixture"]
        app.launch()
        XCTAssertTrue(app.staticTexts["recordingLimit"].exists)
        app.buttons["startRecording"].tap()
        let elapsed = app.staticTexts["recordingElapsed"]
        let ticking = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label == %@ OR value == %@", "0:01 elapsed", "0:01 elapsed"), object: elapsed)
        XCTAssertEqual(XCTWaiter.wait(for: [ticking], timeout: 4), .completed)
        let recording = XCTAttachment(screenshot: app.screenshot())
        recording.name = "Recording timer (simulated input)"
        recording.lifetime = .keepAlways
        add(recording)
        XCTAssertTrue(app.staticTexts["stopNotice"].waitForExistence(timeout: 8))
        let notice = app.staticTexts["stopNotice"]
        XCTAssertTrue(notice.label.contains("6 seconds") || (notice.value as? String)?.contains("6 seconds") == true)
        XCTAssertTrue(app.staticTexts["sessionStatus"].label == "Saved" || app.staticTexts["sessionStatus"].value as? String == "Saved")
        let stoppedTime = elapsed.label
        app.terminate()
        app.launch()
        app.buttons.matching(identifier: "savedSession").firstMatch.tap()
        XCTAssertTrue(app.staticTexts["stopNotice"].exists)
        XCTAssertEqual(app.staticTexts["recordingElapsed"].label, stoppedTime)
        let saved = XCTAttachment(screenshot: app.screenshot())
        saved.name = "Automatic stop explanation after relaunch"
        saved.lifetime = .keepAlways
        add(saved)
        app.buttons["deleteSession"].tap()
        app.windows.buttons["confirmDeleteSession"].firstMatch.tap()
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
        app.windows.buttons["confirmDeleteSession"].firstMatch.tap()
    }
}
