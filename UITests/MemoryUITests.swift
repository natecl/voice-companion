import XCTest

#if os(macOS)
@MainActor
final class MemoryUITests: XCTestCase {
    func testSavedTranscriptSynchronizesReopensAndDeletesWithoutMemoryUI() throws {
        continueAfterFailure = false
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let fixture = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("Backend/memory_fixture.py")
        let process = Process()
        let python = ProcessInfo.processInfo.environment["VOICE_TEST_PYTHON"] ?? "/usr/bin/env"
        process.executableURL = URL(fileURLWithPath: python)
        process.arguments = (python == "/usr/bin/env" ? ["python3"] : []) + [fixture.path, directory.path]
        process.standardOutput = FileHandle.nullDevice
        process.standardError = FileHandle.standardError
        try process.run()
        defer { if process.isRunning { process.terminate() }; process.waitUntilExit() }
        let config = directory.appendingPathComponent("config.json")
        let ready = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            FileManager.default.fileExists(atPath: config.path)
        }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [ready], timeout: 5), .completed)
        let app = XCUIApplication()
        app.launchArguments = ["--ui-testing", "--memory-ui-fixture", "--relay-config", config.path]
        app.launch()
        defer { app.terminate() }
        app.buttons["startRecording"].tap()
        XCTAssertTrue(app.staticTexts["Saved"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["Synthetic appointment Tuesday at ten. Microphone off."].exists)
        let report = directory.appendingPathComponent("report.json")
        let synced = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            guard let data = try? Data(contentsOf: report), let value = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return false }
            return (value["sources"] as? [[String: Any]])?.count == 1 && (value["usage"] as? [Any])?.isEmpty == true
        }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [synced], timeout: 5), .completed)
        app.terminate(); app.launch()
        app.buttons["savedSession"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["Synthetic appointment Tuesday at ten. Microphone off."].waitForExistence(timeout: 3))
        XCTAssertFalse(app.buttons["Forget"].exists)
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = "Memory foundation — synthetic saved transcript, no memory-management UI"
        attachment.lifetime = .keepAlways
        add(attachment)
        app.buttons["deleteSession"].tap()
        app.buttons["confirmDeleteSession"].tap()
        let deleted = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            guard let data = try? Data(contentsOf: report), let value = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return false }
            return (value["sources"] as? [[String: Any]])?.first?["deleted"] as? Int == 1
        }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [deleted], timeout: 5), .completed)
        XCTAssertTrue(app.staticTexts["No saved sessions yet."].exists)
    }
}
#endif
