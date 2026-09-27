import XCTest

#if os(macOS)
@MainActor
final class RecordingNotesUITests: XCTestCase {
    func testNotesSupportingPassageRelaunchAndDeletion() throws {
        continueAfterFailure = false
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let fixture = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("Backend/companion_fixture.py")
        let process = Process()
        let python = ProcessInfo.processInfo.environment["VOICE_TEST_PYTHON"] ?? "/usr/bin/env"
        process.executableURL = URL(fileURLWithPath: python)
        process.arguments = (python == "/usr/bin/env" ? ["python3"] : []) + [fixture.path, directory.path, "--ui", "--notes"]
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
        app.buttons["startRecording"].tap()
        XCTAssertTrue(app.buttons["stopRecording"].waitForExistence(timeout: 5))
        app.buttons["stopRecording"].tap()
        // Saved notes open automatically when capture finishes.
        XCTAssertTrue(app.staticTexts["notesTitle"].waitForExistence(timeout: 15))
        XCTAssertEqual(app.staticTexts["notesTitle"].value as? String ?? app.staticTexts["notesTitle"].label, "Maya’s swimming")
        app.scrollViews.firstMatch.scroll(byDeltaX: 0, deltaY: -150)
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "Recording notes — actual native app and local service, synthetic input"
        screenshot.lifetime = .keepAlways; add(screenshot)
        app.buttons["notesPassage"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["notesSupportingPassage"].waitForExistence(timeout: 5))
        XCTAssertEqual(app.staticTexts["notesSupportingPassage"].value as? String ?? app.staticTexts["notesSupportingPassage"].label, "Maya enjoys swimming.")
        app.terminate()
        app.launchArguments = ["--ui-testing", "--companion-ui-fixture"]
        app.launch()
        app.buttons["homeNavigation"].tap()
        XCTAssertTrue(app.buttons["savedSession"].firstMatch.waitForExistence(timeout: 5))
        app.buttons["savedSession"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["notesTitle"].waitForExistence(timeout: 10))
        app.scrollViews.firstMatch.scroll(byDeltaX: 0, deltaY: 300)
        app.descendants(matching: .any).matching(NSPredicate(format: "label == %@", "Recording options")).firstMatch.tap()
        app.buttons["deleteSession"].tap(); app.buttons["confirmDeleteSession"].tap()
        XCTAssertFalse(app.buttons["savedSession"].firstMatch.exists)
    }
}
#endif
