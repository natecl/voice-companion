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
             "transcript": ["segments": [["start": 0, "duration": 2, "text": summary + (index == 0 ? " Put together a first version. Compare feedback on Friday. Who will invite the participants?" : ""), "words": [], "isFinal": true]]]]
        }
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--companion-ui-fixture", "--experience-gallery"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = config
        app.launchEnvironment["VOICE_UI_SESSION_FIXTURE"] = String(data: try JSONSerialization.data(withJSONObject: samples), encoding: .utf8)
        app.launch(); defer { app.terminate() }
        XCTAssertTrue(app.buttons["notesNavigation"].waitForExistence(timeout: 5))
        tapReady(app.buttons["notesNavigation"])
        XCTAssertEqual(app.buttons.matching(identifier: "savedSession").count, 4)
        // Open the first note to wait on actual fixture generation, then refresh library titles.
        app.buttons["savedSession"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["notesText"].firstMatch.waitForExistence(timeout: 15))
        snapshot(app, "Polished notes")
        app.buttons["Close recording"].tap()
        XCTAssertTrue(app.staticTexts["Product planning"].waitForExistence(timeout: 5))
        snapshot(app, "Polished Home — four synthetic recordings")
        let firstNote = app.buttons["savedSession"].firstMatch
        firstNote.press(forDuration: 0.8)
        XCTAssertTrue(app.buttons["Share"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.buttons["Delete"].exists)
        XCTAssertTrue(app.buttons["Copy"].exists)
        snapshot(app, "Note context actions")
        app.buttons["Delete"].tap()
        XCTAssertTrue(app.alerts["Delete this note?"].waitForExistence(timeout: 3))
        app.alerts.buttons["Cancel"].tap()
        XCTAssertEqual(app.buttons.matching(identifier: "savedSession").count, 4)
        firstNote.swipeLeft()
        XCTAssertTrue(app.buttons["Delete"].waitForExistence(timeout: 3))
        XCTAssertTrue(app.buttons["Share"].exists)
        XCTAssertTrue(app.buttons["Copy"].exists)
        XCTAssertFalse(app.buttons["Close recording"].exists, "Swiping must not open the note")
        snapshot(app, "Swipe to delete note")
        firstNote.swipeRight()
        XCTAssertFalse(app.buttons["Close recording"].exists, "Closing swipe actions must not open detail")
        firstNote.swipeLeft()
        XCTAssertTrue(app.buttons["Copy"].waitForExistence(timeout: 3))
        app.buttons["Copy"].tap()
        XCTAssertFalse(app.buttons["Close recording"].exists)
        firstNote.swipeLeft()
        XCTAssertTrue(app.buttons["Delete"].waitForExistence(timeout: 3))
        app.buttons["Delete"].tap()
        app.buttons["confirmDeleteLibraryNote"].firstMatch.tap()
        XCTAssertEqual(app.buttons.matching(identifier: "savedSession").count, 3)
        app.buttons["agentNavigation"].tap()
        app.buttons["chooseRecordingAttachment"].tap()
        XCTAssertTrue(app.buttons["attachRecordingRow"].firstMatch.waitForExistence(timeout: 5))
        snapshot(app, "Recording attachment picker")
        app.buttons["attachRecordingRow"].firstMatch.tap()
        XCTAssertTrue(app.descendants(matching: .any).matching(identifier: "chatAttachment").firstMatch.waitForExistence(timeout: 5))
        app.buttons["removeAttachment"].tap()
        snapshot(app, "Polished Agent")
        tapReady(app.buttons["notesNavigation"])
        app.buttons["searchRecordings"].tap()
        app.textFields["recordingSearch"].tap(); app.textFields["recordingSearch"].typeText("launch\n")
        app.swipeDown()
        snapshot(app, "Search results")
        app.buttons["Cancel"].tap()
        app.buttons["agentNavigation"].tap()
        app.buttons["companionProfile"].tap()
        XCTAssertTrue(app.staticTexts["Good to have you here."].waitForExistence(timeout: 3))
        snapshot(app, "Your space")
        app.buttons["What Ellis remembers"].tap()
        XCTAssertTrue(app.staticTexts["You’re in control."].waitForExistence(timeout: 3))
        snapshot(app, "Memory preferences")
        app.buttons["Close panel"].tap()

    }

    func testCompanionRoomHeaderAndInvite() throws {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--companion-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"])
        app.launch(); defer { app.terminate() }
        XCTAssertTrue(app.buttons["notesNavigation"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["searchRecordings"].exists)
        XCTAssertTrue(app.buttons["inviteFriends"].exists)
        snapshot(app, "Companion room home")
        tapReady(app.buttons["inviteFriends"])
        XCTAssertTrue(app.staticTexts["Friend invitations aren’t available in this internal build yet."].waitForExistence(timeout: 3))
        snapshot(app, "Invitation boundary")
        app.buttons["Close invitation"].tap()
        tapReady(app.buttons["notesNavigation"])
        XCTAssertTrue(app.buttons["agentNavigation"].waitForExistence(timeout: 3))
        XCTAssertFalse(app.buttons["inviteFriends"].exists)
        app.buttons["agentNavigation"].tap()
        XCTAssertTrue(app.buttons["inviteFriends"].waitForExistence(timeout: 3))
        app.buttons["startRecording"].tap()
        XCTAssertTrue(app.buttons["showActiveRecording"].waitForExistence(timeout: 5))
        snapshot(app, "Companion room capture")
        app.buttons["stopRecording"].tap()
    }

    func testPrototypePanelsToastAndAppearance() throws {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--companion-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"])
        app.launch(); defer { app.terminate() }
        XCTAssertTrue(app.buttons["chooseRecordingAttachment"].waitForExistence(timeout: 5))
        app.buttons["chooseRecordingAttachment"].tap()
        XCTAssertTrue(app.staticTexts["Bring a note into the conversation"].waitForExistence(timeout: 3))
        snapshot(app, "Empty attachment panel")
        app.buttons["Close panel"].tap()
        tapReady(app.buttons["inviteFriends"])
        app.buttons["yourProfile"].tap()
        XCTAssertTrue(app.staticTexts["Your space"].waitForExistence(timeout: 3))
        app.buttons["roomAppearance"].tap()
        XCTAssertTrue(app.buttons["inviteFriends"].waitForExistence(timeout: 3))
        snapshot(app, "Dark companion home")
        tapReady(app.buttons["inviteFriends"])
        snapshot(app, "Dark invitation panel")
        app.buttons["yourProfile"].tap()
        app.buttons["roomAppearance"].tap()
        let draft = app.descendants(matching: .any).matching(identifier: "companionDraft").firstMatch
        XCTAssertTrue(draft.wait(for: \.isEnabled, toEqual: true, timeout: 3))
        let before = draft.frame
        draft.tap(); draft.typeText("UI failure fixture")
        app.buttons["sendCompanion"].tap()
        let toast = app.descendants(matching: .any).matching(identifier: "roomToast").firstMatch
        XCTAssertTrue(toast.waitForExistence(timeout: 8))
        XCTAssertEqual(draft.frame.minY, before.minY, accuracy: 2, "Toast must overlay rather than displace the composer")
        snapshot(app, "Failure toast")
        app.buttons["Dismiss message"].tap()
        XCTAssertFalse(toast.exists)
        XCTAssertTrue(app.buttons["chooseRecordingAttachment"].exists)
        XCTAssertFalse(app.staticTexts["companionPartial"].exists, "An empty failed reply must not leave an empty bubble")
        app.buttons["Check reply"].tap()
        XCTAssertTrue(app.buttons["Answer needs attention"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.staticTexts.matching(NSPredicate(format: "label == %@", "UI failure fixture")).count, 1, "Recovery must reconcile the original request without duplicating it")
    }

    private func tapReady(_ button: XCUIElement) {
        XCTAssertTrue(button.waitForExistence(timeout: 3))
        XCTAssertTrue(button.wait(for: \.isEnabled, toEqual: true, timeout: 3))
        button.tap()
    }

    private func snapshot(_ app: XCUIApplication, _ name: String) {
        // Capture settled artwork after navigation and panel transitions.
        Thread.sleep(forTimeInterval: 0.4)
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
        let singleLineHeight = draft.frame.height
        draft.typeText(" and help me remember the people involved, the decisions we made, and what I should follow up on tomorrow.")
        XCTAssertGreaterThan(draft.frame.height, singleLineHeight + 15)
        snapshot(app, "Composer wrapping naturally")
        draft.coordinate(withNormalizedOffset: CGVector(dx: 0.98, dy: 0.9)).tap()
        draft.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: (draft.value as? String ?? "").count))
        XCTAssertTrue(app.buttons["startDictation"].exists)
        draft.tap(); draft.typeText("Keep this thought")

        tapReady(app.buttons["notesNavigation"])
        XCTAssertFalse(draft.exists, "Notes is a separate reading surface")
        app.buttons["agentNavigation"].tap()
        XCTAssertEqual(draft.value as? String, "Keep this thought")
        XCTAssertTrue(app.buttons["sendCompanion"].exists)
        XCTAssertFalse(app.buttons["startDictation"].exists)
        snapshot(app, "Companion draft preserved after Notes")
        app.buttons["startRecording"].tap()
        XCTAssertTrue(app.buttons["showActiveRecording"].waitForExistence(timeout: 5))
        let stopBeforePanel = app.buttons["stopRecording"].frame
        app.buttons["showActiveRecording"].tap()
        XCTAssertTrue(app.staticTexts["transcriptSegment"].firstMatch.waitForExistence(timeout: 5))
        snapshot(app, "Live transcript panel")
        XCTAssertEqual(app.buttons.matching(identifier: "stopRecording").count, 1)
        app.buttons["Close recording"].tap()
        XCTAssertTrue(app.buttons["stopRecording"].wait(for: \.isEnabled, toEqual: true, timeout: 2))
        XCTAssertEqual(draft.value as? String, "Keep this thought")
        XCTAssertEqual(app.buttons["stopRecording"].frame.minY, stopBeforePanel.minY, accuracy: 2, "Closing a panel must not move the capture controls")
        app.buttons["stopRecording"].tap()
        let savedNoteReady = app.buttons["askAboutRecording"].waitForExistence(timeout: 8)
        if !savedNoteReady { print("CAPTURE_STOP_DIAGNOSTIC", app.debugDescription); snapshot(app, "Capture stop state") }
        XCTAssertTrue(savedNoteReady)
        app.buttons["Close recording"].tap()
        tapReady(app.buttons["notesNavigation"])
        XCTAssertTrue(app.buttons["savedSession"].firstMatch.waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["searchRecordings"].waitForExistence(timeout: 5))
        let home = XCTAttachment(screenshot: app.screenshot()); home.name = "Notes after capture"; home.lifetime = .keepAlways; add(home)
        app.buttons["searchRecordings"].tap()
        let search = app.textFields["recordingSearch"]
        search.tap(); search.typeText("zzznomatch")
        XCTAssertTrue(app.staticTexts["No matching recordings"].exists)
        XCTAssertFalse(app.buttons["savedSession"].exists)
        app.buttons["Cancel"].tap()
        XCTAssertTrue(app.buttons["savedSession"].firstMatch.exists)
        app.buttons["agentNavigation"].tap()
        XCTAssertEqual(draft.value as? String, "Keep this thought")
        draft.coordinate(withNormalizedOffset: CGVector(dx: 0.98, dy: 0.9)).tap()
        draft.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: (draft.value as? String ?? "").count))
        XCTAssertTrue(app.buttons["startDictation"].exists)
        XCTAssertFalse(app.buttons["sendCompanion"].exists)
        app.buttons["startDictation"].tap()
        XCTAssertTrue(app.buttons["discardDictation"].waitForExistence(timeout: 3))
        snapshot(app, "Live dictation waveform")
        app.buttons["discardDictation"].tap()
        XCTAssertTrue(app.buttons["startDictation"].exists)
        app.buttons["startDictation"].tap()
        XCTAssertTrue(app.buttons["sendDictation"].waitForExistence(timeout: 3))
        app.buttons["sendDictation"].tap()
        XCTAssertTrue(app.staticTexts["What does Maya enjoy?"].firstMatch.waitForExistence(timeout: 8))
        XCTAssertTrue(app.buttons["startDictation"].waitForExistence(timeout: 8))
        draft.tap(); draft.typeText("Keep this draft")
        app.buttons["companionProfile"].press(forDuration: 0.8)
        XCTAssertFalse(app.buttons["clearCompanionDraft"].exists)
        snapshot(app, "Conversation refresh action")
        app.buttons["Refresh conversation"].tap()
        XCTAssertTrue(app.staticTexts["Conversation is up to date."].waitForExistence(timeout: 8))
        XCTAssertEqual(draft.value as? String, "Keep this draft")

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
        XCTAssertTrue(app.staticTexts["agentWelcome"].waitForExistence(timeout: 5))
        XCTAssertFalse(app.staticTexts["What’s on your mind?"].exists)
        snapshot(app, "Agent welcome message")
        app.buttons["startRecording"].tap()
        XCTAssertTrue(app.buttons["showActiveRecording"].waitForExistence(timeout: 5))
        field.tap(); field.typeText("What does Maya enjoy?")
        app.buttons["sendCompanion"].tap()
        XCTAssertTrue(app.buttons["companionSource"].firstMatch.waitForExistence(timeout: 5))
        app.swipeDown()
        XCTAssertFalse(app.staticTexts["Ellis"].exists)
        XCTAssertTrue(app.descendants(matching: .any).matching(identifier: "roomToast").firstMatch.exists)
        snapshot(app, "Agent conversation during capture")
        app.buttons["Dismiss Agent update"].tap()
        XCTAssertFalse(app.buttons["Dismiss Agent update"].exists)
        XCTAssertFalse(app.buttons["Copy answer"].exists)
        app.swipeUp()
        app.staticTexts["companionAnswer"].firstMatch.press(forDuration: 0.8)
        XCTAssertTrue(app.buttons["Copy"].waitForExistence(timeout: 3))
        snapshot(app, "Copy bubble preview")
        app.buttons["Copy"].tap()
        app.buttons["showActiveRecording"].tap()
        snapshot(app, "Live transcript sheet")
        app.buttons["Close recording"].tap()
        XCTAssertTrue(app.buttons["stopRecording"].wait(for: \.isEnabled, toEqual: true, timeout: 2))
        app.buttons["companionSource"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["citedPassage"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.staticTexts["citedPassage"].label, "Maya enjoys swimming.")
        XCTAssertTrue(app.buttons["stopRecording"].wait(for: \.isEnabled, toEqual: true, timeout: 2))
        app.buttons["backToCompanion"].tap()
        app.buttons["stopRecording"].tap()
        // Stopping now opens the saved recording sheet automatically.
        XCTAssertTrue(app.buttons["askAboutRecording"].waitForExistence(timeout: 5))
        app.buttons["askAboutRecording"].tap()
        XCTAssertTrue(app.descendants(matching: .any).matching(identifier: "chatAttachment").firstMatch.exists)
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
