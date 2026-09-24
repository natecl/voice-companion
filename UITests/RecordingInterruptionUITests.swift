import XCTest

#if os(iOS)
/// Opt-in physical-device check. Uses one bounded real provider connection.
@MainActor
final class RecordingInterruptionUITests: XCTestCase {
    func testReplayStopsWhenAppEntersBackground() {
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing"]
        app.launch()
        app.buttons["replaySample"].tap()
        XCTAssertTrue(app.staticTexts["sessionStatus"].waitForExistence(timeout: 5))
        XCUIApplication(bundleIdentifier: "com.apple.springboard").activate()
        let background = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            app.state == .runningBackground || app.state == .runningBackgroundSuspended
        }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [background], timeout: 5), .completed)
        print("State after Home: \(app.state.rawValue)")
        let homeShot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        homeShot.name = "Device after Home"
        homeShot.lifetime = .keepAlways
        add(homeShot)
        app.activate()
        XCTAssertEqual(app.staticTexts["sessionStatus"].label, "Incomplete · saved")
        app.terminate()
    }

    func testBackgroundStopsAndPreservesIncompleteSession() {
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing"]
        app.launch()
        app.buttons["startRecording"].tap()
        let status = app.staticTexts["sessionStatus"]
        let recording = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label == %@", "Recording"), object: status)
        guard XCTWaiter.wait(for: [recording], timeout: 15) == .completed else {
            XCTFail("Real recording did not start")
            return
        }
        XCUIApplication(bundleIdentifier: "com.apple.springboard").activate()
        let background = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            app.state == .runningBackground || app.state == .runningBackgroundSuspended
        }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [background], timeout: 5), .completed)
        print("State after Home: \(app.state.rawValue)")
        let homeShot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        homeShot.name = "Device after Home"
        homeShot.lifetime = .keepAlways
        add(homeShot)
        app.activate()
        let stopped = XCTNSPredicateExpectation(predicate: NSPredicate(format: "label == %@", "Incomplete · saved"), object: status)
        XCTAssertEqual(XCTWaiter.wait(for: [stopped], timeout: 10), .completed)
        XCTAssertFalse(app.buttons["stopRecording"].exists)
        let reason = app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", "left the foreground")).firstMatch
        XCTAssertTrue(reason.exists)
        let shot = XCTAttachment(screenshot: app.screenshot())
        shot.name = "Background stopped recording"
        shot.lifetime = .keepAlways
        add(shot)
        app.terminate()
        app.launch()
        app.buttons.matching(identifier: "savedSession").firstMatch.tap()
        XCTAssertEqual(status.label, "Incomplete · saved")
        XCTAssertTrue(reason.exists)
        app.terminate()
    }
}
#endif
