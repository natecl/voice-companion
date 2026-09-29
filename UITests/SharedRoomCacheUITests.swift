import XCTest
#if os(iOS)
/// Explicit staged loopback fixture: see docs/qa/note-cache/README.md.
@MainActor final class SharedRoomCacheUITests: XCTestCase {
    private func launch(stage: String = #function) throws -> XCUIApplication {
        let requested = try? String(contentsOfFile: "/tmp/voice-note-cache-qa/stage.txt", encoding: .utf8)
        guard requested?.trimmingCharacters(in: .whitespacesAndNewlines) == stage.replacingOccurrences(of: "()", with: "") else {
            throw XCTSkip("Run the explicit note_cache_fixture.py stage first.")
        }
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--shared-room-ui", "--companion-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = try String(contentsOfFile: "/tmp/voice-note-cache-qa/config.json", encoding: .utf8)
        app.launch()
        XCTAssertTrue(app.webViews.buttons["Open notes"].waitForExistence(timeout: 10))
        return app
    }
    private func openNote(_ app: XCUIApplication) {
        let web = app.webViews.firstMatch
        web.buttons["Open notes"].tap()
        let card = web.buttons.containing(NSPredicate(format: "label CONTAINS 'Maya’s' OR label CONTAINS 'Recorded conversation'")).firstMatch
        XCTAssertTrue(card.waitForExistence(timeout: 8))
        card.tap()
        XCTAssertTrue(web.buttons["Talk about this"].waitForExistence(timeout: 5))
    }
    private func shot(_ app: XCUIApplication, _ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
    func testSharedCachePopulate() throws {
        let app = try launch(); defer { app.terminate() }
        let web = app.webViews.firstMatch
        web.buttons["Invite Ellis into the conversation"].tap()
        XCTAssertTrue(web.buttons["End recording"].waitForExistence(timeout: 8))
        web.buttons["End recording"].tap()
        XCTAssertTrue(web.buttons["Invite Ellis into the conversation"].waitForExistence(timeout: 8))
        openNote(app)
        XCTAssertTrue(web.staticTexts["Maya enjoys swimming."].waitForExistence(timeout: 20))
        shot(app, "shared-cache-online")
    }
    func testSharedCacheOffline() throws {
        let app = try launch(); defer { app.terminate() }
        openNote(app)
        XCTAssertTrue(app.webViews.staticTexts["Maya enjoys swimming."].waitForExistence(timeout: 3))
        shot(app, "shared-cache-offline-immediate")
        // Stopped loopback fails immediately; retain the visible cached result afterward too.
        Thread.sleep(forTimeInterval: 3)
        XCTAssertTrue(app.webViews.staticTexts["Maya enjoys swimming."].exists)
        if app.webViews.buttons["Dismiss message"].exists { app.webViews.buttons["Dismiss message"].tap() }
        shot(app, "shared-cache-offline-preserved")
    }
    func testSharedCacheUpdate() throws {
        let app = try launch(); defer { app.terminate() }
        openNote(app)
        XCTAssertTrue(app.webViews.staticTexts["Maya enjoys swimming."].waitForExistence(timeout: 3))
        shot(app, "shared-cache-before-update")
        try Data().write(to: URL(fileURLWithPath: "/tmp/voice-note-cache-qa/release-update"))
        XCTAssertTrue(app.webViews.staticTexts["Maya enjoys swimming. Updated saved fixture."].waitForExistence(timeout: 10))
        XCTAssertTrue(app.webViews.staticTexts["Maya’s updated swimming note"].exists)
        shot(app, "shared-cache-after-update")
    }
    func testSharedCacheRemoteDelete() throws {
        let app = try launch(); defer { app.terminate() }
        openNote(app)
        XCTAssertTrue(app.webViews.staticTexts["This recording is no longer available."].waitForExistence(timeout: 10))
        XCTAssertFalse(app.webViews.staticTexts["Maya enjoys swimming."].exists)
        XCTAssertTrue(app.webViews.staticTexts["Recorded conversation"].exists)
        shot(app, "shared-cache-remote-delete")
    }
    func testSharedCacheLocalDelete() throws {
        let app = try launch(); defer { app.terminate() }
        let web = app.webViews.firstMatch
        web.buttons["Open notes"].tap()
        let card = web.buttons.containing(NSPredicate(format: "label CONTAINS 'Maya’s swimming'")).firstMatch
        XCTAssertTrue(card.waitForExistence(timeout: 8))
        card.swipeLeft(); web.buttons["Delete"].tap()
        let confirm = web.buttons["Delete note"]
        XCTAssertTrue(confirm.waitForExistence(timeout: 3)); confirm.tap()
        XCTAssertTrue(web.staticTexts["Your conversations will find a home here. Tap + with Ellis to capture your first conversation."].waitForExistence(timeout: 5))
        XCTAssertFalse(card.exists)
        shot(app, "shared-cache-local-delete")
    }
    func testSharedCacheStale() throws {
        let app = try launch(); defer { app.terminate() }
        openNote(app)
        XCTAssertTrue(app.webViews.staticTexts["The transcript changed. These notes are no longer current."].waitForExistence(timeout: 10))
        XCTAssertFalse(app.webViews.staticTexts["Maya enjoys swimming. Updated saved fixture."].exists)
        XCTAssertTrue(app.webViews.staticTexts["Recorded conversation"].exists)
        shot(app, "shared-cache-stale-removed")
    }
}
#endif
