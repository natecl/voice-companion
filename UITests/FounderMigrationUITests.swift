import XCTest
#if os(iOS)
@MainActor final class FounderMigrationUITests: XCTestCase {
    func testRuntimeKeychainMigrationAcrossFourLaunches() {
        continueAfterFailure = false
        let app = XCUIApplication()
        app.launchArguments = ["--account-keychain-fixture", "--founder-migration-fixture"]
        app.launchEnvironment["ELLIS_ACCOUNT_QA_ID"] = UUID().uuidString
        for (phase, expected) in [
            ("prepare", "Wrong accounts blocked; move interrupted"),
            ("pending", "Pending move survived; account saved"),
            ("finish", "Migration restored from Keychain"),
            ("verify", "Google account persisted after relaunch")
        ] {
            app.launchEnvironment["ELLIS_ACCOUNT_QA_PHASE"] = phase
            app.launch()
            XCTAssertTrue(app.staticTexts[expected].waitForExistence(timeout: 12), app.debugDescription)
            app.terminate()
        }
    }
}
#endif
