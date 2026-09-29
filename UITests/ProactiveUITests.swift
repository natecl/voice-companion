import XCTest

@MainActor
final class ProactiveUITests: XCTestCase {
    func testContributionUsesMainChatPreservesDraftAndQuietDoesNotStopCapture() throws {
        continueAfterFailure = false
        #if os(macOS)
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let fixture = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("Backend/companion_fixture.py")
        let process = Process()
        let python = ProcessInfo.processInfo.environment["VOICE_TEST_PYTHON"] ?? "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3"
        process.executableURL = URL(fileURLWithPath: python)
        process.arguments = [fixture.path, directory.path, "--ui", "--proactive"]
        process.standardOutput = FileHandle.nullDevice
        try process.run()
        defer { if process.isRunning { process.terminate() }; process.waitUntilExit() }
        let config = directory.appendingPathComponent("config.json")
        let ready = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in FileManager.default.fileExists(atPath: config.path) }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 5), .completed)
        let rawConfig = try String(contentsOf: config, encoding: .utf8)
        #else
        let rawConfig = try XCTUnwrap(ProcessInfo.processInfo.environment["VOICE_MEMORY_UI_CONFIG"])
        #endif
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--enable-companion-ui", "--companion-ui-fixture", "--proactive-qa"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = rawConfig
        app.launch(); defer { app.terminate() }
        let field = app.descendants(matching: .any).matching(identifier: "companionDraft").firstMatch
        XCTAssertTrue(field.waitForExistence(timeout: 5))
        field.tap(); field.typeText("Keep my draft")
        app.buttons["startRecording"].tap()
        let message = app.staticTexts.matching(identifier: "companionAnswer").firstMatch
        XCTAssertTrue(message.waitForExistence(timeout: 8))
        XCTAssertTrue(message.label.contains("Alex"))
        XCTAssertFalse(app.staticTexts["Ellis"].exists)
        XCTAssertGreaterThan(message.frame.width, 100)
        XCTAssertGreaterThanOrEqual(message.frame.minX, 16)
        XCTAssertLessThanOrEqual(message.frame.maxX, app.frame.maxX - 80)
        XCTAssertEqual(field.value as? String, "Keep my draft")
        XCTAssertTrue(app.buttons["stopRecording"].isEnabled)
        app.buttons["quietContributions"].tap()
        XCTAssertFalse(app.buttons["quietContributions"].isEnabled)
        XCTAssertTrue(app.buttons["stopRecording"].isEnabled)
        XCTAssertEqual(app.staticTexts.matching(identifier: "companionAnswer").count, 1)
        let screenshot = XCTAttachment(screenshot: app.screenshot())
        screenshot.name = "Proactive ordinary message — local socket, synthetic capture and model"
        screenshot.lifetime = .keepAlways; add(screenshot)

        app.buttons["proactiveNewMessage"].tap()
        XCTAssertFalse(app.buttons["proactiveNewMessage"].exists)
        app.buttons["stopRecording"].tap()
        app.terminate(); app.launch()
        let restored = app.staticTexts.matching(identifier: "companionAnswer").firstMatch
        XCTAssertTrue(restored.waitForExistence(timeout: 8))
        XCTAssertEqual(restored.label, "Earlier, Alex mentioned waking at three each morning. That may be worth bringing up.")
        XCTAssertEqual(app.staticTexts.matching(identifier: "companionAnswer").count, 1)
    }
}
