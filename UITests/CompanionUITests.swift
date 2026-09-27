import XCTest

#if os(macOS)
@MainActor
final class CompanionUITests: XCTestCase {
    func testCaptureChatAttachmentCitationReopenAndDeletion() throws {
        continueAfterFailure = false
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let fixture = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("Backend/companion_fixture.py")
        let process = Process()
        let python = ProcessInfo.processInfo.environment["VOICE_TEST_PYTHON"] ?? "/usr/bin/env"
        process.executableURL = URL(fileURLWithPath: python)
        process.arguments = (python == "/usr/bin/env" ? ["python3"] : []) + [fixture.path, directory.path, "--ui"]
        process.standardOutput = FileHandle.nullDevice
        try process.run()
        defer { if process.isRunning { process.terminate() }; process.waitUntilExit() }
        let config = directory.appendingPathComponent("config.json")
        let ready = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in FileManager.default.fileExists(atPath: config.path) }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 5), .completed)
        let app = XCUIApplication()
        app.launchArguments = ["--show-evidence-debug", "--ui-testing", "--enable-companion-ui", "--companion-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = try String(contentsOf: config, encoding: .utf8)
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
        field.tap(); field.typeText("Keep this draft")
        app.buttons["companionSource"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["citedPassage"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.staticTexts["citedPassage"].value as? String ?? app.staticTexts["citedPassage"].label, "Maya enjoys swimming.")
        XCTAssertTrue(app.buttons["stopRecording"].isEnabled)
        XCTAssertTrue(app.staticTexts.containing(NSPredicate(format: "value CONTAINS %@", "More simulated speech.")).firstMatch.exists)
        app.buttons["backToCompanion"].tap()
        XCTAssertEqual(field.value as? String, "Keep this draft")
        app.buttons["stopRecording"].tap()
        // Stopping now opens the saved recording sheet automatically.
        XCTAssertTrue(app.buttons["askAboutRecording"].waitForExistence(timeout: 5))
        app.buttons["askAboutRecording"].tap()
        XCTAssertTrue(app.staticTexts["chatAttachment"].exists)
        XCTAssertEqual(field.value as? String, "Keep this draft")
        app.buttons["sendCompanion"].tap()
        let twoAnswers = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in app.staticTexts.matching(identifier: "companionAnswer").count == 2 }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [twoAnswers], timeout: 5), .completed)
        app.buttons["removeAttachment"].tap()
        XCTAssertFalse(app.staticTexts["chatAttachment"].exists)
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Companion main chat — real local service, synthetic provider and capture"
        attachment.lifetime = .keepAlways
        add(attachment)
        app.terminate()
        app.launchArguments = ["--show-evidence-debug", "--ui-testing", "--companion-ui-fixture"]
        app.launch()
        XCTAssertTrue(app.buttons["companionSource"].firstMatch.waitForExistence(timeout: 5))
        app.buttons["companionSource"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["citedPassage"].waitForExistence(timeout: 5))
        app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "Recording options")).firstMatch.tap()
        app.buttons["deleteSession"].tap()
        app.buttons["confirmDeleteSession"].tap()
        app.buttons["agentNavigation"].tap()
        let removed = app.staticTexts["Answer removed because its source changed or was deleted"].firstMatch
        XCTAssertTrue(removed.waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["companionSource"].firstMatch.exists)
        XCTAssertFalse(app.staticTexts["companionAnswer"].firstMatch.exists)
    }
    func testDictationDraftAndExplicitSendWithCapture() throws {
        try checkDictation(emptyFinal: false)
    }

    func testDictationEmptyFinalRetainsEditableDraft() throws {
        try checkDictation(emptyFinal: true)
    }

    private func checkDictation(emptyFinal: Bool) throws {
        continueAfterFailure = false
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let fixture = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("Backend/companion_fixture.py")
        let process = Process()
        process.executableURL = URL(fileURLWithPath: ProcessInfo.processInfo.environment["VOICE_TEST_PYTHON"] ?? "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3")
        process.arguments = [fixture.path, directory.path, "--ui"]
        process.standardOutput = FileHandle.nullDevice
        try process.run()
        defer { if process.isRunning { process.terminate() }; process.waitUntilExit() }
        let config = directory.appendingPathComponent("config.json")
        let ready = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in FileManager.default.fileExists(atPath: config.path) }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 5), .completed)
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--companion-ui-fixture", "--dictation-ui-fixture"]
        if emptyFinal { app.launchArguments.append("--dictation-empty-final-fixture") }
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = try String(contentsOf: config, encoding: .utf8)
        app.launch(); defer { app.terminate() }
        let field = app.descendants(matching: .any).matching(identifier: "companionDraft").firstMatch
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        let dictate = app.buttons["startDictation"]
        let enabled = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in dictate.isEnabled }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [enabled], timeout: 5), .completed)
        field.tap(); field.typeText("Please tell me:")
        dictate.tap()
        XCTAssertTrue(app.buttons["stopDictation"].waitForExistence(timeout: 3))
        XCTAssertEqual(field.value as? String, "Please tell me: What does Maya")
        app.buttons["stopDictation"].tap()
        let expected = emptyFinal ? "Please tell me: What does Maya" : "Please tell me: What does Maya enjoy?"
        let finalized = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in field.value as? String == expected && field.isEnabled }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [finalized], timeout: 5), .completed)
        XCTAssertFalse(app.staticTexts["companionAnswer"].exists)
        if emptyFinal {
            XCTAssertTrue(app.staticTexts["dictationNotice"].exists)
            field.tap(); field.typeText(" edited")
            XCTAssertTrue((field.value as? String ?? "").contains("edited"))
            XCTAssertTrue((field.value as? String ?? "").contains("What does Maya"))
            let attachment = XCTAttachment(screenshot: app.screenshot())
            attachment.name = "Empty final preserves editable speech — synthetic input"
            attachment.lifetime = .keepAlways; add(attachment)
            let clear = app.buttons["clearCompanionDraft"]
            app.popUpButtons["Message options"].tap()
            clear.tap()
            XCTAssertEqual(field.value as? String, "")
            XCTAssertFalse(app.staticTexts["dictationNotice"].exists)
            dictate.tap()
            XCTAssertTrue(app.buttons["stopDictation"].waitForExistence(timeout: 3))
            app.popUpButtons["Message options"].tap()
            clear.tap()
            XCTAssertEqual(field.value as? String, "")
            XCTAssertTrue(dictate.exists)
            XCTAssertFalse(app.staticTexts["companionAnswer"].exists)
            return
        }
        app.buttons["startRecording"].tap()
        XCTAssertTrue(app.buttons["stopRecording"].waitForExistence(timeout: 5))
        dictate.tap()
        XCTAssertTrue(app.buttons["stopDictation"].waitForExistence(timeout: 3))
        app.buttons["sendCompanion"].tap()
        XCTAssertTrue(app.staticTexts["companionAnswer"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.buttons["stopRecording"].isEnabled)
        XCTAssertEqual(field.value as? String, "")
        let message = app.staticTexts["companionAnswer"].firstMatch
        XCTAssertEqual(message.value as? String ?? message.label, "Maya swims.")
        XCTAssertFalse(app.buttons["companionSource"].exists)
        XCTAssertFalse(app.staticTexts["retainedMemoryReference"].exists)
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Dictation explicit send with continuing capture — synthetic input"
        attachment.lifetime = .keepAlways; add(attachment)
        app.buttons["stopRecording"].tap()
    }

}
#endif
