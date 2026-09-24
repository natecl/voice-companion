import XCTest

/// Opt-in verification of the consented appointment recording in normal app storage.
/// Reads existing data only; never records, uploads, or deletes a session.
@MainActor
final class SavedRecordingUITests: XCTestCase {
    private func displayedText(_ element: XCUIElement) -> String {
        element.label.isEmpty ? (element.value as? String ?? "") : element.label
    }

    func testLatestFiveMinuteRecordingSurvivesRelaunch() {
        let app = XCUIApplication()
        app.launch()
        var originalText: [String] = []
        for attempt in 0..<2 {
            let latest = app.buttons.matching(identifier: "savedSession").firstMatch
            XCTAssertTrue(latest.waitForExistence(timeout: 5))
            latest.tap()
            XCTAssertEqual(displayedText(app.staticTexts["sessionStatus"]), "Saved")
            XCTAssertTrue(displayedText(app.staticTexts["stopNotice"]).contains("300 seconds"))
            XCTAssertTrue(displayedText(app.staticTexts["recordingElapsed"]).hasPrefix("5:"))
            let text = app.staticTexts.allElementsBoundByIndex.map(displayedText)
            XCTAssertTrue(text.contains { $0.contains("Speaker 1") })
            XCTAssertGreaterThan(text.joined(separator: " ").split(separator: " ").count, 300)
            if attempt == 0 { originalText = text } else { XCTAssertEqual(text, originalText) }
            let screenshot = XCTAttachment(screenshot: app.screenshot())
            screenshot.name = "Five-minute saved transcript reopen \(attempt + 1)"
            screenshot.lifetime = .keepAlways
            add(screenshot)
            app.terminate()
            if attempt == 0 { app.launch() }
        }
    }

    func testExistingRecordingSurvivesNavigationAndRelaunch() {
        let app = XCUIApplication()
        app.launch()
        for attempt in 0..<3 {
            let savedSession = app.buttons.matching(identifier: "savedSession").firstMatch
            XCTAssertTrue(savedSession.waitForExistence(timeout: 5))
            savedSession.tap()
            XCTAssertEqual(app.staticTexts["sessionStatus"].label, "Saved")
            let segments = app.descendants(matching: .any).matching(identifier: "transcriptSegment")
            XCTAssertEqual(segments.count, 2)
            let text = app.staticTexts.allElementsBoundByIndex.map(\.label).joined(separator: " ")
            for phrase in ["Speaker 1", "The appointment is tomorrow morning", "vaccination record", "We will review the", "results together"] {
                XCTAssertTrue(text.contains(phrase), "Missing expected phrase: \(phrase)")
            }
            let screenshot = XCTAttachment(screenshot: app.screenshot())
            screenshot.name = "Saved microphone transcript verification \(attempt + 1)"
            screenshot.lifetime = .keepAlways
            add(screenshot)
            if attempt == 0 {
                app.buttons["closeSession"].tap()
            } else if attempt == 1 {
                app.terminate()
                app.launch()
            }
        }
        app.terminate()
    }
}
