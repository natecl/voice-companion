import XCTest

@MainActor
final class FoundationUITests: XCTestCase {
    func testReplayPersistsAcrossRelaunch() {
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing"]
        app.launch()
        app.buttons["replaySample"].tap()
        XCTAssertTrue(app.staticTexts["sessionStatus"].waitForExistence(timeout: 5))
        // Cached real provider events contain text before any speaker IDs arrive.
        let earlyText = app.staticTexts.containing(NSPredicate(format:
            "label CONTAINS %@ OR value CONTAINS %@", "The appointment is", "The appointment is")).firstMatch
        XCTAssertTrue(earlyText.waitForExistence(timeout: 4))
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format:
            "label CONTAINS %@ OR value CONTAINS %@", "Speaker pending", "Speaker pending")).firstMatch.exists)
        XCTAssertFalse(app.staticTexts.containing(NSPredicate(format:
            "label CONTAINS %@ OR value CONTAINS %@", "Speaker 1", "Speaker 1")).firstMatch.exists)
        let earlyShot = XCTAttachment(screenshot: app.screenshot())
        earlyShot.name = "Text visible before speaker labels (cached provider events)"
        earlyShot.lifetime = .keepAlways
        add(earlyShot)
        let saved = NSPredicate(format: "label == %@ OR value == %@", "Saved", "Saved")
        let completion = XCTNSPredicateExpectation(predicate: saved, object: app.staticTexts["sessionStatus"])
        XCTAssertEqual(XCTWaiter.wait(for: [completion], timeout: 25), .completed)
        XCTAssertEqual(app.descendants(matching: .any).matching(identifier: "transcriptSegment").count, 1)
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format:
            "label CONTAINS %@ OR value CONTAINS %@", "Speaker 1", "Speaker 1")).firstMatch.exists)
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format:
            "label CONTAINS %@ OR value CONTAINS %@", "Speaker 2", "Speaker 2")).firstMatch.exists)
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

    func testLongTranscriptKeepsStopVisibleAndReopensAllTurns() {
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--long-transcript-ui-fixture"]
        app.launch()
        app.buttons["startRecording"].tap()
        let segments = app.descendants(matching: .any).matching(identifier: "transcriptSegment")
        let populated = XCTNSPredicateExpectation(predicate: NSPredicate(format: "count == 60"), object: segments)
        XCTAssertEqual(XCTWaiter.wait(for: [populated], timeout: 10), .completed)
        XCTAssertTrue(app.buttons["stopRecording"].isHittable)
        let shot = XCTAttachment(screenshot: app.screenshot())
        shot.name = "Long transcript with visible Stop (accelerated fixture)"
        shot.lifetime = .keepAlways
        add(shot)
        app.buttons["stopRecording"].tap()
        let saved = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label == %@ OR value == %@", "Saved", "Saved"), object: app.staticTexts["sessionStatus"])
        XCTAssertEqual(XCTWaiter.wait(for: [saved], timeout: 5), .completed)
        app.terminate()
        app.launch()
        app.buttons.matching(identifier: "savedSession").firstMatch.tap()
        XCTAssertEqual(segments.count, 60)
        let lastTurn = app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@ OR value CONTAINS %@", "Simulated turn 60.", "Simulated turn 60.")).firstMatch
        XCTAssertTrue(lastTurn.exists)
        // XCTest scrolls the offscreen control into view; deletion touches only QA data.
        app.buttons["deleteSession"].tap()
        app.windows.buttons["confirmDeleteSession"].firstMatch.tap()
        XCTAssertTrue(app.buttons["replaySample"].exists)
    }

    func testEmptyRecordingSavesAndReopensWithoutText() {
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--empty-recording-ui-fixture"]
        app.launch()
        app.buttons["startRecording"].tap()
        XCTAssertTrue(app.buttons["stopRecording"].waitForExistence(timeout: 3))
        app.buttons["stopRecording"].tap()
        let saved = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label == %@ OR value == %@", "Saved", "Saved"), object: app.staticTexts["sessionStatus"])
        XCTAssertEqual(XCTWaiter.wait(for: [saved], timeout: 5), .completed)
        app.terminate()
        app.launch()
        app.buttons.matching(identifier: "savedSession").firstMatch.tap()
        XCTAssertEqual(app.descendants(matching: .any).matching(identifier: "transcriptSegment").count, 0)
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "label == %@ OR value == %@", "No transcript was received.", "No transcript was received.")).firstMatch.exists)
        let shot = XCTAttachment(screenshot: app.screenshot())
        shot.name = "Empty saved session"
        shot.lifetime = .keepAlways
        add(shot)
        app.buttons["deleteSession"].tap()
        app.windows.buttons["confirmDeleteSession"].firstMatch.tap()
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
