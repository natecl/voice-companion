import XCTest

#if os(iOS)
@MainActor
final class CompanionPhoneUITests: XCTestCase {
    func testExperienceGalleryAndAttachmentPicker() throws {
        continueAfterFailure = false
        let config = try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"])
        let configObject = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(config.utf8)) as? [String: Any])
        let owner = try XCTUnwrap(configObject["memoryOwnerID"] as? String)
        let calendar = Calendar.current
        let today = calendar.startOfDay(for: Date())
        let summaries = ["Test the first version with five people.", "A simple direction for the launch.", "A few places to explore and things to try.", "Keep capture simple and chat close by."]
        let minutes = [12, 18, 6, 24]
        let dates = [today.addingTimeInterval(37440), today.addingTimeInterval(29700), today.addingTimeInterval(-22680), today.addingTimeInterval(-35400)]
        let samples: [[String: Any]] = summaries.enumerated().map { index, summary in
            ["id": UUID().uuidString, "createdAt": dates[index].timeIntervalSinceReferenceDate,
             "completed": true, "source": "microphone", "recordingSeconds": minutes[index] * 60,
             "memoryOwnerID": owner, "memoryTerminal": true,
             "transcript": ["segments": [["start": 0, "duration": 2, "text": summary, "words": [], "isFinal": true]]]]
        }
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--companion-ui-fixture", "--experience-gallery"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = config
        app.launchEnvironment["VOICE_UI_SESSION_FIXTURE"] = String(data: try JSONSerialization.data(withJSONObject: samples), encoding: .utf8)
        app.launch(); defer { app.terminate() }
        XCTAssertTrue(app.buttons["homeNavigation"].waitForExistence(timeout: 5))
        app.buttons["homeNavigation"].tap()
        XCTAssertEqual(app.buttons.matching(identifier: "savedSession").count, 4)
        // Open the first note to wait on actual fixture generation, then refresh library titles.
        app.buttons["savedSession"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["notesTitle"].waitForExistence(timeout: 15))
        snapshot(app, "Polished notes")
        app.buttons["Close recording"].tap()
        XCTAssertTrue(app.staticTexts["Product planning"].waitForExistence(timeout: 5))
        snapshot(app, "Polished Home — four synthetic recordings")
        app.buttons["Attachments and message options"].tap()
        app.buttons["chooseRecordingAttachment"].tap()
        XCTAssertTrue(app.buttons["attachRecordingRow"].firstMatch.waitForExistence(timeout: 5))
        snapshot(app, "Recording attachment picker")
        app.buttons["attachRecordingRow"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["chatAttachment"].waitForExistence(timeout: 5))
        app.buttons["removeAttachment"].tap()
        app.buttons["agentNavigation"].tap()
        snapshot(app, "Polished Agent")
        app.buttons["Account"].tap()
        snapshot(app, "Account")
        app.buttons["Sign-up preview"].tap()
        snapshot(app, "Sign-up preview")
        app.navigationBars.buttons.firstMatch.tap()
        app.buttons["Plan preview"].tap()
        snapshot(app, "Pricing preview")
    }

    private func snapshot(_ app: XCUIApplication, _ name: String) {
        let image = XCTAttachment(screenshot: app.screenshot())
        image.name = name; image.lifetime = .keepAlways; add(image)
    }

    func testHomeSearchSharedDraftAndTranscriptSheet() throws {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--companion-ui-fixture", "--dictation-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"])
        app.launch()
        defer { app.terminate() }
        let draft = app.descendants(matching: .any).matching(identifier: "companionDraft").firstMatch
        XCTAssertTrue(draft.waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["startDictation"].exists)
        XCTAssertFalse(app.buttons["sendCompanion"].exists)
        draft.tap(); draft.typeText("Keep this thought")
        XCTAssertTrue(app.buttons["sendCompanion"].exists)
        XCTAssertFalse(app.buttons["startDictation"].exists)
        snapshot(app, "Agent composer with send")
        app.buttons["homeNavigation"].tap()
        XCTAssertEqual(draft.value as? String, "Keep this thought")
        XCTAssertTrue(app.buttons["sendCompanion"].exists)
        XCTAssertFalse(app.buttons["startDictation"].exists)
        snapshot(app, "Home composer with send")
        app.buttons["startRecording"].tap()
        XCTAssertTrue(app.buttons["showActiveRecording"].waitForExistence(timeout: 5))
        app.buttons["showActiveRecording"].tap()
        XCTAssertTrue(app.staticTexts["transcriptSegment"].firstMatch.waitForExistence(timeout: 5))
        XCTAssertEqual(app.buttons.matching(identifier: "stopRecording").count, 1)
        app.buttons["Close recording"].tap()
        XCTAssertTrue(app.buttons["stopRecording"].isEnabled)
        XCTAssertEqual(draft.value as? String, "Keep this thought")
        app.buttons["stopRecording"].tap()
        XCTAssertTrue(app.buttons["askAboutRecording"].waitForExistence(timeout: 8))
        app.buttons["Close recording"].tap()
        app.buttons["homeNavigation"].tap()
        XCTAssertTrue(app.buttons["savedSession"].firstMatch.waitForExistence(timeout: 5))
        let home = XCTAttachment(screenshot: app.screenshot()); home.name = "Home with shared composer"; home.lifetime = .keepAlways; add(home)
        app.buttons["searchRecordings"].tap()
        let search = app.textFields["recordingSearch"]
        search.tap(); search.typeText("zzznomatch")
        XCTAssertTrue(app.staticTexts["No matching recordings"].exists)
        XCTAssertFalse(app.buttons["savedSession"].exists)
        app.buttons["Cancel"].tap()
        XCTAssertTrue(app.buttons["savedSession"].firstMatch.exists)
        app.buttons["agentNavigation"].tap()
        XCTAssertEqual(draft.value as? String, "Keep this thought")
        app.buttons["Attachments and message options"].tap()
        app.buttons["clearCompanionDraft"].tap()
        XCTAssertTrue(app.buttons["startDictation"].exists)
        XCTAssertFalse(app.buttons["sendCompanion"].exists)
        app.buttons["startDictation"].tap()
        XCTAssertTrue(app.buttons["stopDictation"].waitForExistence(timeout: 3))
        XCTAssertFalse(app.buttons["sendCompanion"].exists)
        app.buttons["stopDictation"].tap()
        let editable = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in draft.isEnabled && (draft.value as? String ?? "").contains("What does Maya enjoy?") }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [editable], timeout: 5), .completed)
        XCTAssertTrue(app.buttons["sendCompanion"].exists)
        XCTAssertFalse(app.buttons["startDictation"].exists)
    }

    func testRetainedMemoryReferenceAfterReopen() throws {
        continueAfterFailure = false
        let config = try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"])
        let app = XCUIApplication()
        app.launchArguments = ["--show-evidence-debug", "--ui-testing", "--enable-companion-ui", "--companion-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = config
        app.launch()
        defer { app.terminate() }
        XCTAssertTrue(app.staticTexts["retainedMemoryReference"].firstMatch.waitForExistence(timeout: 8))
        XCTAssertFalse(app.buttons["companionSource"].exists)
        XCTAssertTrue(app.staticTexts["companionAnswer"].firstMatch.label.contains("community center"))
        let image = XCTAttachment(screenshot: app.screenshot())
        image.name = "Retained memory — recording deleted, no broken source button"
        image.lifetime = .keepAlways
        add(image)
        app.terminate()
        app.launchArguments = ["--show-evidence-debug", "--ui-testing", "--companion-ui-fixture"]
        app.launch()
        XCTAssertTrue(app.staticTexts["retainedMemoryReference"].firstMatch.waitForExistence(timeout: 8))
        XCTAssertFalse(app.buttons["companionSource"].exists)
    }

    func testCompanionAndCaptureNavigation() throws {
        continueAfterFailure = false
        let config = try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"], "Launch with the isolated local companion fixture configuration")
        let app = XCUIApplication()
        app.launchArguments = ["--show-evidence-debug", "--ui-testing", "--enable-companion-ui", "--companion-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = config
        app.launch()
        defer { app.terminate() }
        let field = app.descendants(matching: .any).matching(identifier: "companionDraft").firstMatch
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        app.buttons["startRecording"].tap()
        XCTAssertTrue(app.buttons["showActiveRecording"].waitForExistence(timeout: 5))
        field.tap(); field.typeText("What does Maya enjoy?")
        app.buttons["sendCompanion"].tap()
        XCTAssertTrue(app.buttons["companionSource"].firstMatch.waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["stopRecording"].isEnabled)
        app.buttons["companionSource"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["citedPassage"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.staticTexts["citedPassage"].label, "Maya enjoys swimming.")
        XCTAssertTrue(app.buttons["stopRecording"].isEnabled)
        app.buttons["backToCompanion"].tap()
        app.buttons["stopRecording"].tap()
        // Stopping now opens the saved recording sheet automatically.
        XCTAssertTrue(app.buttons["askAboutRecording"].waitForExistence(timeout: 5))
        app.buttons["askAboutRecording"].tap()
        XCTAssertTrue(app.staticTexts["chatAttachment"].exists)
        app.buttons["removeAttachment"].tap()
        let image = XCTAttachment(screenshot: app.screenshot())
        image.name = "iPhone companion navigation — synthetic capture and local service"
        image.lifetime = .keepAlways
        add(image)
        app.terminate()
        app.launchArguments = ["--show-evidence-debug", "--ui-testing", "--companion-ui-fixture"]
        app.launch()
        XCTAssertTrue(app.buttons["companionSource"].firstMatch.waitForExistence(timeout: 5))
    }
}
#endif
