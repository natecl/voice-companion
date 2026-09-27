import XCTest

#if os(iOS)
@MainActor
final class CompanionPhoneUITests: XCTestCase {
    func testHomeSearchSharedDraftAndTranscriptSheet() throws {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--companion-ui-fixture", "--dictation-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"])
        app.launch()
        defer { app.terminate() }
        let draft = app.descendants(matching: .any).matching(identifier: "companionDraft").firstMatch
        XCTAssertTrue(draft.waitForExistence(timeout: 5))
        draft.tap(); draft.typeText("Keep this thought")
        app.buttons["homeNavigation"].tap()
        XCTAssertEqual(draft.value as? String, "Keep this thought")
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
        app.buttons["startDictation"].tap()
        XCTAssertTrue(app.buttons["stopDictation"].waitForExistence(timeout: 3))
        app.buttons["stopDictation"].tap()
        let editable = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in draft.isEnabled && (draft.value as? String ?? "").contains("What does Maya enjoy?") }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [editable], timeout: 5), .completed)
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
