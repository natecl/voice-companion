import XCTest

#if os(iOS)
/// Run with the fictional local companion_fixture.py service described in the cache map.
@MainActor
final class RecordingNotesCacheUITests: XCTestCase {
    private func app(stage: String = #function) throws -> XCUIApplication {
        let requested = try? String(contentsOfFile: "/tmp/voice-note-cache-qa/stage.txt", encoding: .utf8)
        guard requested?.trimmingCharacters(in: .whitespacesAndNewlines) == stage.replacingOccurrences(of: "()", with: "") else {
            throw XCTSkip("Run the explicit fictional cache fixture stage from docs/qa/note-cache/README.md.")
        }
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--companion-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = try String(contentsOfFile: "/tmp/voice-note-cache-qa/config.json", encoding: .utf8)
        return app
    }
    private func capture(_ app: XCUIApplication, _ name: String) {
        let image = XCTAttachment(screenshot: app.screenshot()); image.name = name; image.lifetime = .keepAlways; add(image)
    }
    func testPopulateCache() throws {
        continueAfterFailure = false
        let app = try app(); app.launch(); defer { app.terminate() }
        app.buttons["startRecording"].tap()
        XCTAssertTrue(app.buttons["stopRecording"].waitForExistence(timeout: 5))
        app.buttons["stopRecording"].tap()
        XCTAssertTrue(app.staticTexts["notesText"].firstMatch.waitForExistence(timeout: 20))
        XCTAssertEqual(app.staticTexts["notesText"].firstMatch.label, "Maya enjoys swimming.")
        capture(app, "cache-online-populated")
    }
    func testReopenSavedCache() throws {
        continueAfterFailure = false
        let app = try app(); app.launch(); defer { app.terminate() }
        app.buttons["notesNavigation"].tap()
        XCTAssertTrue(app.buttons["savedSession"].firstMatch.waitForExistence(timeout: 5))
        app.buttons["savedSession"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["notesText"].firstMatch.waitForExistence(timeout: 3))
        XCTAssertEqual(app.staticTexts["notesText"].firstMatch.label, "Maya enjoys swimming.")
        capture(app, "cache-relaunch-immediate")
        XCTAssertTrue(app.staticTexts["notesRefreshStatus"].waitForExistence(timeout: 15))
        XCTAssertEqual(app.staticTexts["notesText"].firstMatch.label, "Maya enjoys swimming.")
        capture(app, "cache-offline-failed-refresh-preserved")
    }
    func testBackgroundUpdate() throws {
        continueAfterFailure = false
        let app = try app(); app.launch(); defer { app.terminate() }
        app.buttons["notesNavigation"].tap()
        XCTAssertTrue(app.buttons["savedSession"].firstMatch.waitForExistence(timeout: 5))
        app.buttons["savedSession"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["notesText"].firstMatch.waitForExistence(timeout: 3))
        capture(app, "cache-before-refresh")
        let updated = app.staticTexts.matching(NSPredicate(format: "identifier == %@ AND label == %@", "notesText", "Maya enjoys swimming. Updated saved fixture.")).firstMatch
        XCTAssertTrue(updated.waitForExistence(timeout: 10))
        capture(app, "cache-after-background-update")
    }
    func testOutdatedSource() throws {
        continueAfterFailure = false
        let app = try app(); app.launch(); defer { app.terminate() }
        app.buttons["notesNavigation"].tap()
        XCTAssertTrue(app.buttons["savedSession"].firstMatch.waitForExistence(timeout: 5))
        app.buttons["savedSession"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["notesStatus"].waitForExistence(timeout: 10))
        XCTAssertEqual(app.staticTexts["notesStatus"].label, "The transcript changed. These notes are no longer current.")
        XCTAssertFalse(app.staticTexts["notesText"].firstMatch.exists)
        capture(app, "cache-outdated-source-hidden")
    }

    func testOwnerIsolation() throws {
        continueAfterFailure = false
        let app = try app()
        var config = try JSONSerialization.jsonObject(with: Data(app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"]!.utf8)) as! [String: Any]
        config["memoryOwnerID"] = UUID().uuidString
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = String(decoding: try JSONSerialization.data(withJSONObject: config), as: UTF8.self)
        app.launch(); defer { app.terminate() }
        app.buttons["notesNavigation"].tap()
        XCTAssertFalse(app.buttons["savedSession"].firstMatch.exists)
        XCTAssertFalse(app.staticTexts["notesText"].firstMatch.exists)
        capture(app, "cache-other-owner-empty-library")
    }
    func testDeleteCachedRecording() throws {
        continueAfterFailure = false
        let app = try app(); app.launch(); defer { app.terminate() }
        app.buttons["notesNavigation"].tap()
        XCTAssertTrue(app.buttons["savedSession"].firstMatch.waitForExistence(timeout: 5))
        app.buttons["savedSession"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["notesText"].firstMatch.waitForExistence(timeout: 10))
        capture(app, "cache-before-delete")
        app.buttons["Recording options"].tap()
        app.buttons["deleteSession"].tap()
        app.buttons["confirmDeleteSession"].firstMatch.tap()
        XCTAssertFalse(app.staticTexts["notesText"].firstMatch.exists)
        Thread.sleep(forTimeInterval: 1) // Let the existing navigation transition finish for inspection.
        capture(app, "cache-after-delete")
    }

}
#endif
