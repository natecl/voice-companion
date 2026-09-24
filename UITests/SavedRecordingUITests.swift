import XCTest

/// Opt-in verification of the consented appointment recording in normal app storage.
/// Reads existing data only; never records, uploads, or deletes a session.
@MainActor
final class SavedRecordingUITests: XCTestCase {
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
