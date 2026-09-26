import XCTest

#if os(macOS)
@MainActor
final class MemoryUITests: XCTestCase {
    func testSavedTranscriptSynchronizesReopensAndDeletesWithoutMemoryUI() throws {
        try verifySource(personal: false)
    }
    func testPersonalNoteSynchronizesReopensAndDeletes() throws {
        try verifySource(personal: true)
    }
    private func verifySource(personal: Bool) throws {
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
        app.launchArguments = ["--ui-testing", "--memory-ui-fixture"]
        app.launchEnvironment["VOICE_MEMORY_UI_CONFIG"] = try String(contentsOf: config, encoding: .utf8)
        app.launch()
        defer { app.terminate() }
        let content = personal ? "My daughter Maya enjoys swimming." : "Synthetic appointment Tuesday at ten. Microphone off."
        if personal {
            app.buttons["addPersonalNote"].tap()
            let editor = app.textViews["personalNoteText"]
            XCTAssertTrue(editor.waitForExistence(timeout: 3))
            editor.tap()
            editor.typeText(content)
            app.buttons["savePersonalNote"].tap()
        } else { app.buttons["startRecording"].tap() }
        XCTAssertTrue(app.staticTexts["Saved"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts[content].exists)
        let report = directory.appendingPathComponent("report.json")
        let synced = XCTNSPredicateExpectation(predicate: NSPredicate { _, _ in
            guard let data = try? Data(contentsOf: report), let value = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else { return false }
            return (value["sources"] as? [[String: Any]])?.count == 1 && (value["usage"] as? [Any])?.isEmpty == true
        }, object: nil)
        XCTAssertEqual(XCTWaiter.wait(for: [synced], timeout: 5), .completed)
        if personal {
            XCTAssertTrue(app.staticTexts["Saved and synced."].waitForExistence(timeout: 3))
            XCTAssertFalse(app.staticTexts["Speaker pending"].exists)
            let value = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: report)) as? [String: Any])
            let payload = try XCTUnwrap((value["sources"] as? [[String: Any]])?.first?["payload"] as? String)
            let source = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(payload.utf8)) as? [String: Any])
            XCTAssertEqual(source["origin"] as? String, "personal_text")
            XCTAssertTrue(String(describing: value["diagnostics"]).contains("profile_pending"))
        }
        app.terminate(); app.launch()
        app.buttons["savedSession"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts[content].waitForExistence(timeout: 3))
        XCTAssertFalse(app.buttons["Forget"].exists)
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = personal ? "Personal note — saved and reopened" : "Memory foundation — synthetic saved transcript"
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
