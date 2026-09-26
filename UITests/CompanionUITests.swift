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
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--companion-ui-fixture"]
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
        app.buttons["companionSource"].firstMatch.tap()
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
        app.launchArguments = ["--ui-testing", "--companion-ui-fixture"]
        app.launch()
        XCTAssertTrue(app.buttons["companionSource"].firstMatch.waitForExistence(timeout: 5))
        app.buttons["companionSource"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["citedPassage"].waitForExistence(timeout: 5))
        app.buttons["deleteSession"].tap()
        app.buttons["confirmDeleteSession"].tap()
        app.radioButtons["Companion"].tap()
        let removed = app.staticTexts["Answer removed because its source changed or was deleted"].firstMatch
        XCTAssertTrue(removed.waitForExistence(timeout: 5))
        XCTAssertFalse(app.buttons["companionSource"].firstMatch.exists)
        XCTAssertFalse(app.staticTexts["companionAnswer"].firstMatch.exists)
    }
}
#endif
