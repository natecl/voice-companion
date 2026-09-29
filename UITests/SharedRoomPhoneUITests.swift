import XCTest
#if os(iOS)
@MainActor final class SharedRoomPhoneUITests: XCTestCase {
    func testSharedRoomNativePipeline() throws {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--shared-room-ui", "--companion-ui-fixture", "--dictation-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"])
        app.launch(); defer { app.terminate() }
        let web = app.webViews.firstMatch
        XCTAssertTrue(web.buttons["Open notes"].waitForExistence(timeout: 10))
        XCTAssertTrue(web.staticTexts["Hey, good to see you."].exists)
        shot(app, "Shared room — welcome")
        let input = web.textViews["Message Ellis"]
        input.tap(); input.typeText("Where is the appointment?")
        let send = web.buttons["Send message"]
        XCTAssertTrue(send.waitForExistence(timeout: 3))
        XCTAssertEqual(send.frame.width, send.frame.height, accuracy: 1)
        shot(app, "Shared room — keyboard and circular send")
        send.tap()
        XCTAssertTrue(web.staticTexts.containing(NSPredicate(format: "label CONTAINS 'Hello from the saved companion'")).firstMatch.waitForExistence(timeout: 10), app.debugDescription)
        if web.buttons["Dismiss message"].exists { web.buttons["Dismiss message"].tap() }
        web.buttons["Invite Ellis into the conversation"].tap()
        XCTAssertTrue(web.staticTexts["Listening"].waitForExistence(timeout: 5))
        web.buttons["View"].tap()
        XCTAssertTrue(web.staticTexts.containing(NSPredicate(format: "label CONTAINS 'Maya'")).firstMatch.waitForExistence(timeout: 8))
        shot(app, "Shared room — live transcript")
        tapSettled(web.buttons["Close panel"])
        XCTAssertTrue(web.buttons["End recording"].waitForExistence(timeout: 3))
        web.buttons["End recording"].tap()
        XCTAssertTrue(web.buttons["Invite Ellis into the conversation"].waitForExistence(timeout: 8))
        // A left swipe on the conversation is the alternative to tapping the menu.
        let from = web.coordinate(withNormalizedOffset: CGVector(dx: 0.8, dy: 0.45))
        let to = web.coordinate(withNormalizedOffset: CGVector(dx: 0.2, dy: 0.45))
        from.press(forDuration: 0.05, thenDragTo: to)
        let note=web.buttons.containing(NSPredicate(format: "label CONTAINS 'Recorded conversation' OR label CONTAINS 'Maya’s swimming'")).firstMatch
        XCTAssertTrue(note.waitForExistence(timeout: 8))
        XCTAssertFalse(web.staticTexts["A small test, then build"].exists, "No prototype seed notes in the real app")
        web.buttons["Search notes"].tap()
        let search=web.searchFields["Find a conversation"]
        XCTAssertTrue(search.waitForExistence(timeout: 3))
        search.typeText("zzznomatchingnote")
        XCTAssertTrue(web.staticTexts["No notes match yet. Try another word."].waitForExistence(timeout: 3))
        search.typeText(String(repeating: XCUIKeyboardKey.delete.rawValue, count: 17))
        if app.keyboards.buttons["Search"].exists { app.keyboards.buttons["Search"].tap() }

        shot(app, "Shared room — saved note")
        note.swipeLeft()
        XCTAssertTrue(web.buttons["Delete"].waitForExistence(timeout: 3))
        XCTAssertFalse(web.buttons["Close panel"].exists, "A swipe cannot open the note")
        shot(app, "Shared room — swipe actions")
        note.swipeRight()
        note.press(forDuration: 0.7)
        XCTAssertTrue(web.buttons["Share"].waitForExistence(timeout: 3))
        XCTAssertTrue(web.buttons["Copy"].exists)
        XCTAssertTrue(web.buttons["Delete"].exists)
        shot(app, "Shared room — note long press")
        tapSettled(web.buttons["Close panel"])
        tapSettled(note)
        XCTAssertTrue(web.buttons["Talk about this"].waitForExistence(timeout: 12))
        shot(app,"Shared room — note and purple action")
        web.switches["Transcript"].tap()
        XCTAssertTrue(web.staticTexts.containing(NSPredicate(format: "label CONTAINS 'Maya'")).firstMatch.waitForExistence(timeout: 5))
        shot(app,"Shared room — transcript tab")
        web.switches["Notes"].tap()

        web.buttons["Talk about this"].tap()
        XCTAssertTrue(web.buttons["Remove attachment"].waitForExistence(timeout: 3))
        web.buttons["Remove attachment"].tap()
        web.buttons["Attach note"].tap()
        XCTAssertTrue(web.staticTexts["Bring a note into the conversation"].waitForExistence(timeout: 4))
        shot(app,"Shared room — attachment picker")
        tapSettled(web.buttons["Close panel"])
        web.buttons["Dictate a message"].tap()
        XCTAssertTrue(web.buttons["Send dictation"].waitForExistence(timeout: 5))
        shot(app, "Shared room — native dictation fixture")
        web.buttons["Send dictation"].tap()
        XCTAssertTrue(web.staticTexts["What does Maya enjoy?"].waitForExistence(timeout: 8))
        if web.buttons["Dismiss message"].exists { web.buttons["Dismiss message"].tap() }
        web.buttons["Invite"].tap()
        tapSettled(web.buttons["Your profile"])
        shot(app, "Shared room — profile")
        web.buttons["What Ellis remembers"].tap()
        XCTAssertTrue(web.staticTexts["You’re in control."].waitForExistence(timeout: 3))
        shot(app, "Shared room — memory controls")
        tapSettled(web.buttons["Close panel"])
        tapSettled(web.buttons["Your profile"])
        tapSettled(web.buttons.containing(NSPredicate(format:"label BEGINSWITH 'Appearance'")).firstMatch)
        XCTAssertTrue(web.buttons["Open notes"].waitForExistence(timeout: 3))
        shot(app, "Shared room — dark")
    }
    func testSharedRoomAccessoryPanels() throws {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--shared-room-ui", "--companion-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"])
        app.launch(); defer { app.terminate() }
        let web = app.webViews.firstMatch
        XCTAssertTrue(web.buttons["Invite"].waitForExistence(timeout: 10))
        web.buttons["Invite"].tap()
        XCTAssertTrue(web.staticTexts["A little more company."].waitForExistence(timeout: 3))
        shot(app, "Shared room — invitation")
        tapSettled(web.buttons["Your profile"])
        shot(app, "Shared room — settled profile")
        web.buttons["What Ellis remembers"].tap()
        XCTAssertTrue(web.staticTexts["You’re in control."].waitForExistence(timeout: 3))
        shot(app, "Shared room — memory controls")
        tapSettled(web.buttons["Close panel"])
        XCTAssertTrue(web.buttons["Attach note"].waitForExistence(timeout: 3))
        web.buttons["Attach note"].tap()
        XCTAssertTrue(web.staticTexts["No notes yet"].waitForExistence(timeout: 3))
        shot(app, "Shared room — empty attachment picker")
    }
    func testSharedRoomProactiveAndRelaunch() throws {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--shared-room-ui", "--companion-ui-fixture", "--proactive-qa"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"])
        app.launch(); defer { app.terminate() }
        let web=app.webViews.firstMatch
        XCTAssertTrue(web.buttons["Open notes"].waitForExistence(timeout: 8))
        let draft=web.textViews["Message Ellis"]
        draft.tap(); draft.typeText("Keep my draft")
        web.buttons["Invite Ellis into the conversation"].tap()
        XCTAssertTrue(web.staticTexts["Earlier, Alex mentioned waking at three each morning."].waitForExistence(timeout: 10))
        XCTAssertTrue(web.staticTexts["That may be worth bringing up."].exists)
        XCTAssertEqual(draft.value as? String, "Keep my draft")
        web.descendants(matching: .any).matching(identifier: "Quiet mode").firstMatch.tap()
        XCTAssertTrue(web.buttons["End recording"].isEnabled)
        XCTAssertFalse(web.descendants(matching: .any).matching(identifier: "Quiet mode").firstMatch.isEnabled)
        shot(app, "Shared room — proactive message group and quiet")
        web.buttons["End recording"].tap()
        XCTAssertTrue(web.buttons["Invite Ellis into the conversation"].waitForExistence(timeout: 8))
        app.terminate(); app.launchArguments.removeAll { $0 == "--shared-room-ui" }; app.launch()
        XCTAssertTrue(web.staticTexts["Earlier, Alex mentioned waking at three each morning."].waitForExistence(timeout: 10))
        XCTAssertTrue(web.staticTexts["That may be worth bringing up."].exists)
    }
    func testSharedRoomFailureAndSafeText() throws {
        continueAfterFailure=false
        let app=XCUIApplication()
        app.launchArguments=["--ui-testing", "--enable-companion-ui", "--shared-room-ui", "--companion-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"]=try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"])
        app.launch(); defer { app.terminate() }
        let web=app.webViews.firstMatch
        XCTAssertTrue(web.buttons["Open notes"].waitForExistence(timeout: 8))
        let draft=web.textViews["Message Ellis"]
        draft.tap();draft.typeText("UI failure fixture");web.buttons["Send message"].tap()
        XCTAssertTrue(web.buttons["Dismiss message"].waitForExistence(timeout: 10))
        XCTAssertTrue(web.buttons["Check reply"].exists)
        shot(app,"Shared room — failure toast")
        web.buttons["Dismiss message"].tap()
        XCTAssertTrue(web.buttons["Dismiss message"].waitForNonExistence(timeout: 3))
        web.buttons["Check reply"].tap()
        XCTAssertTrue(web.buttons["Check reply"].waitForNonExistence(timeout: 10))
        XCTAssertEqual(web.staticTexts.matching(identifier: "UI failure fixture").count,1)
        if web.buttons["Dismiss message"].exists { web.buttons["Dismiss message"].tap() }
        let literal="<b>Plain text, never HTML</b>"
        draft.tap();draft.typeText(literal);web.buttons["Send message"].tap()
        XCTAssertTrue(web.staticTexts[literal].waitForExistence(timeout: 8))
        XCTAssertTrue(web.staticTexts["Hello from the saved companion."].waitForExistence(timeout: 8))
        if web.buttons["Dismiss message"].exists { web.buttons["Dismiss message"].tap() }
        web.staticTexts["Hello from the saved companion."].press(forDuration: 0.7)
        XCTAssertTrue(web.buttons["Copy"].waitForExistence(timeout: 4))
        shot(app,"Shared room — message copy menu")
        web.buttons["Copy"].tap()
        XCTAssertTrue(web.buttons["Open notes"].waitForExistence(timeout: 4))
    }
    private func waitUntilSettled(_ element: XCUIElement, timeout: TimeInterval = 5) {
        var lastFrame = CGRect.zero
        var stableSince = Date()
        let settled = NSPredicate { _, _ in
            guard element.exists, element.isHittable else { stableSince = Date(); return false }
            let frame = element.frame
            if frame != lastFrame { lastFrame = frame; stableSince = Date(); return false }
            return Date().timeIntervalSince(stableSince) > 0.5
        }
        XCTAssertEqual(XCTWaiter.wait(for: [XCTNSPredicateExpectation(predicate: settled, object: nil)], timeout: timeout), .completed)
    }
    private func tapSettled(_ element: XCUIElement) {
        waitUntilSettled(element)
        element.tap()
    }
    private func shot(_ app: XCUIApplication, _ name: String) {
        let close = app.webViews.buttons["Close panel"]
        if close.exists { waitUntilSettled(close, timeout: name.contains("live transcript") ? 15 : 5) }
        let attachment=XCTAttachment(screenshot:app.screenshot());attachment.name=name;attachment.lifetime = .keepAlways;add(attachment)
    }
}
#endif
