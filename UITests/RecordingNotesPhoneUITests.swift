import XCTest

#if os(iOS)
@MainActor
final class RecordingNotesPhoneUITests: XCTestCase {
    func testManyPassagesKeepNotesReadable() throws {
        continueAfterFailure = false
        let config = try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"])
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(config.utf8)) as? [String: Any])
        let owner = try XCTUnwrap(object["memoryOwnerID"] as? String)
        let segments: [[String: Any]] = (0..<8).map { index in
            ["start": index * 3, "duration": 2, "text": "Layout regression example passage \(index).", "words": [], "isFinal": true]
        }
        let samples: [[String: Any]] = [["id": UUID().uuidString, "createdAt": Date().timeIntervalSinceReferenceDate,
            "completed": true, "source": "microphone", "recordingSeconds": 24,
            "memoryOwnerID": owner, "memoryTerminal": true, "transcript": ["segments": segments]]]
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--companion-ui-fixture", "--experience-gallery"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = config
        app.launchEnvironment["VOICE_UI_SESSION_FIXTURE"] = String(data: try JSONSerialization.data(withJSONObject: samples), encoding: .utf8)
        app.launch(); defer { app.terminate() }
        app.buttons["notesNavigation"].tap()
        XCTAssertTrue(app.buttons["savedSession"].firstMatch.waitForExistence(timeout: 5))
        app.buttons["savedSession"].firstMatch.tap()
        let paragraph = app.staticTexts["notesText"].firstMatch
        XCTAssertTrue(paragraph.waitForExistence(timeout: 15))
        XCTAssertFalse(app.buttons["notesPassage"].firstMatch.exists)
        XCTAssertGreaterThan(paragraph.frame.width, app.frame.width * 0.70)
        XCTAssertGreaterThanOrEqual(paragraph.frame.minX, 16)
        XCTAssertLessThanOrEqual(paragraph.frame.maxX, app.frame.width - 16)
        let title = app.staticTexts["notesTitle"]
        XCTAssertGreaterThanOrEqual(title.frame.minX, 16)
        XCTAssertLessThanOrEqual(title.frame.maxX, app.frame.width - 16)
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "Readable note with eight source passages"
        screenshot.lifetime = .keepAlways; add(screenshot)
        paragraph.press(forDuration: 0.8)
        XCTAssertTrue(app.buttons["notesPassage"].firstMatch.waitForExistence(timeout: 5))
        app.buttons["notesPassage"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["notesSupportingPassage"].waitForExistence(timeout: 5))
    }

    func testNotesSupportingPassageRelaunchAndDeletion() throws {
        continueAfterFailure = false
        let config = try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"])
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--companion-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = config
        app.launch()
        defer { app.terminate() }
        app.buttons["notesNavigation"].tap()
        let existingCount = app.buttons.matching(identifier: "savedSession").count
        app.buttons["agentNavigation"].tap()
        app.buttons["startRecording"].tap()
        XCTAssertTrue(app.buttons["stopRecording"].waitForExistence(timeout: 5))
        app.buttons["stopRecording"].tap()
        // Saved notes open automatically when capture finishes.
        XCTAssertTrue(app.staticTexts["notesText"].firstMatch.waitForExistence(timeout: 15))
        XCTAssertEqual(app.staticTexts["notesTitle"].label, "Maya’s swimming")
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "Recording notes — actual native app and local service, synthetic input"
        screenshot.lifetime = .keepAlways; add(screenshot)
        app.staticTexts["notesText"].firstMatch.press(forDuration: 0.8)
        app.buttons["notesPassage"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["notesSupportingPassage"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.staticTexts["notesSupportingPassage"].label, "Maya enjoys swimming.")
        app.terminate()
        app.launchArguments = ["--ui-testing", "--companion-ui-fixture"]
        app.launch()
        app.buttons["notesNavigation"].tap()
        XCTAssertTrue(app.buttons["savedSession"].firstMatch.waitForExistence(timeout: 5))
        app.buttons["savedSession"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["notesTitle"].waitForExistence(timeout: 10))
        app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "Recording options")).firstMatch.tap()
        app.buttons["deleteSession"].tap(); app.alerts.buttons["confirmDeleteSession"].firstMatch.tap()
        XCTAssertEqual(app.buttons.matching(identifier: "savedSession").count, existingCount)
    }
}
#endif
