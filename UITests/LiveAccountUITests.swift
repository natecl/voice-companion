import XCTest

#if os(iOS)
/// Opt-in controls for the dedicated, localhost-only real-provider QA simulator.
/// Ordinary test runs skip these; provider challenges remain human handoffs.
@MainActor final class LiveAccountUITests: XCTestCase {
    private func application() throws -> XCUIApplication {
        let env = ProcessInfo.processInfo.environment
        guard env["ELLIS_LIVE_ACCOUNT_QA"] == "localhost-recovery",
              env["SIMULATOR_DEVICE_NAME"] == "Ellis Real Account Lifecycle" else {
            throw XCTSkip("Dedicated real-account simulator and explicit opt-in required")
        }
        continueAfterFailure = false
        return XCUIApplication(bundleIdentifier: "ai.voicecompanion.phone")
    }

    func testSignOutAndRequestGoogle() throws {
        let app = try application()
        app.activate()
        let profile = app.webViews.buttons["Your profile"]
        XCTAssertTrue(profile.waitForExistence(timeout: 15))
        profile.tap()
        let signOut = app.webViews.buttons["Sign out"]
        XCTAssertTrue(signOut.waitForExistence(timeout: 5))
        signOut.tap()
        let google = app.buttons["Continue with Google"]
        XCTAssertTrue(google.waitForExistence(timeout: 15))
        google.tap()
        capture(app, name: "Google authorization entry")
    }

    func testSignOutToProviderScreen() throws {
        let app = try application()
        app.activate()
        let profile = app.webViews.buttons["Your profile"]
        XCTAssertTrue(profile.waitForExistence(timeout: 15))
        profile.tap()
        let signOut = app.webViews.buttons["Sign out"]
        XCTAssertTrue(signOut.waitForExistence(timeout: 5))
        signOut.tap()
        XCTAssertTrue(app.buttons["Continue with Google"].waitForExistence(timeout: 15))
        XCTAssertTrue(app.buttons["Continue with Apple"].exists)
        XCTAssertFalse(app.webViews.buttons["Your profile"].exists)
        capture(app, name: "Signed out before provider recovery")
    }

    func testInspectCurrentScreen() throws {
        let app = try application()
        capture(app, name: "Current account screen")
    }

    func testPreservedNetworkRecoveryTranscript() throws {
        let app = try application()
        app.terminate()
        app.launch()
        let notes = app.webViews.buttons["Open notes"]
        XCTAssertTrue(notes.waitForExistence(timeout: 15))
        notes.tap()
        let marker = "Fictional network recovery marker: violet lighthouse."
        let recording = app.webViews.buttons.matching(NSPredicate(format: "label CONTAINS %@", marker)).firstMatch
        XCTAssertTrue(recording.waitForExistence(timeout: 10))
        recording.tap()
        let transcript = app.webViews.switches["Transcript"]
        XCTAssertTrue(transcript.waitForExistence(timeout: 10))
        transcript.tap()
        XCTAssertTrue(app.webViews.staticTexts[marker].waitForExistence(timeout: 10))
        capture(app, name: "Preserved fictional transcript after network recovery")
    }

    func testRequestAppleFromSignedOutScreen() throws {
        let app = try application()
        app.activate()
        let apple = app.buttons["Continue with Apple"]
        XCTAssertTrue(apple.waitForExistence(timeout: 10))
        apple.tap()
        capture(app, name: "Apple authorization entry")
    }

    func testInspectPendingAppleDeletion() throws {
        let app = try application()
        app.activate()
        assertPendingAppleDeletion(app)
        capture(app, name: "Apple enrollment refused for pending deletion")
    }

    func testRequestFreshAppleDeletionProof() throws {
        let app = try application()
        app.activate()
        // Verify the refusal and request recovery in one invocation: the
        // recoveringDeletion flag belongs to the current application runtime.
        assertPendingAppleDeletion(app)
        capture(app, name: "Apple pending deletion before fresh proof")
        app.buttons["Continue with Apple"].tap()
        // Do not choose an Apple account or operate password/security prompts.
        // The operator inspects this attachment before the founder handoff.
        capture(app, name: "Apple fresh-proof authorization entry")
    }

    private func assertPendingAppleDeletion(_ app: XCUIApplication) {
        XCTAssertTrue(app.staticTexts[
            "Sign in with the same provider to finish the account deletion you requested."
        ].waitForExistence(timeout: 20))
        XCTAssertTrue(app.buttons["Continue with Apple"].exists)
        XCTAssertFalse(app.webViews.buttons["Your profile"].exists)
        XCTAssertFalse(app.buttons["Retry deletion"].exists)
    }

    func testCompletedAppleDeletionRecoveryAndRestart() throws {
        let app = try application()
        app.activate()
        // Run only after the real Apple authorization handoff completes. A
        // signed-out screen alone does not establish successful deletion.
        XCTAssertTrue(app.staticTexts["Your account was deleted."].waitForExistence(timeout: 20))
        XCTAssertTrue(app.buttons["Continue with Apple"].exists)
        XCTAssertFalse(app.webViews.buttons["Your profile"].exists)
        XCTAssertFalse(app.buttons["Retry deletion"].exists)
        capture(app, name: "Apple fresh-proof deletion completed")
        app.terminate()
        app.launch()
        XCTAssertTrue(app.buttons["Continue with Apple"].waitForExistence(timeout: 15))
        XCTAssertTrue(app.buttons["Continue with Google"].exists)
        XCTAssertFalse(app.webViews.buttons["Your profile"].exists)
        XCTAssertFalse(app.buttons["Retry deletion"].exists)
        XCTAssertFalse(app.staticTexts[
            "Sign in with the same provider to finish the account deletion you requested."
        ].exists)
        capture(app, name: "Signed out after Apple recovery and restart")
    }

    func testSignedInRestart() throws {
        let app = try application()
        app.activate()
        XCTAssertTrue(app.webViews.buttons["Your profile"].waitForExistence(timeout: 15))
        capture(app, name: "Signed-in account before restart")
        app.terminate()
        app.launch()
        XCTAssertTrue(app.webViews.buttons["Your profile"].waitForExistence(timeout: 15))
        XCTAssertFalse(app.buttons["Continue with Apple"].exists)
        XCTAssertFalse(app.buttons["Continue with Google"].exists)
        capture(app, name: "Signed-in account after restart")
    }

    func testContinueGooglePermission() throws {
        let app = try application()
        try continueGooglePermission(app)
    }

    private func continueGooglePermission(_ app: XCUIApplication) throws {
        let system = XCUIApplication(bundleIdentifier: "com.apple.springboard")
        let alert = system.alerts.containing(.staticText, identifier:
            "“VoiceCompanion” Wants to Use “accounts.google.com” to Sign In").firstMatch
        XCTAssertTrue(alert.waitForExistence(timeout: 5))
        alert.buttons["Continue"].tap()
        // The web authorization sheet can require a saved-account choice or a
        // human security challenge. Inspect it before choosing the next action.
        XCTAssertTrue(app.webViews.firstMatch.waitForExistence(timeout: 15))
        capture(app, name: "Google provider authorization")
    }

    func testChooseObservedGoogleAccount() throws {
        let app = try application()
        try chooseGoogleAccount(app)
    }

    private func chooseGoogleAccount(_ app: XCUIApplication) throws {
        let email = try XCTUnwrap(ProcessInfo.processInfo.environment["ELLIS_QA_GOOGLE_ACCOUNT"])
        XCTAssertFalse(email.isEmpty)
        XCTAssertTrue(app.staticTexts["Choose an account"].waitForExistence(timeout: 10))
        let match = NSPredicate(format: "label CONTAINS[c] %@", email)
        let links = app.links.matching(match)
        let buttons = app.buttons.matching(match)
        if links.count == 1 { links.element.tap() }
        else if buttons.count == 1 { buttons.element.tap() }
        else {
            let text = app.staticTexts.matching(identifier: email)
            XCTAssertEqual(text.count, 1)
            text.element.tap()
        }
        capture(app, name: "After saved Google account choice")
    }

    func testRequestGoogleFromSignedOutScreen() throws {
        let app = try application()
        let google = app.buttons["Continue with Google"]
        XCTAssertTrue(google.waitForExistence(timeout: 10))
        google.tap()
        capture(app, name: "Google request from signed-out screen")
    }

    func testContinueReturningGoogleSignIn() throws {
        let app = try application()
        continueGoogleSignIn(app)
        XCTAssertTrue(app.staticTexts[
            "Sign in with the same provider to finish the account deletion you requested."
        ].waitForExistence(timeout: 20))
        capture(app, name: "Pending deletion requires fresh proof")
    }

    private func continueGoogleSignIn(_ app: XCUIApplication) {
        let heading = app.staticTexts.matching(NSPredicate(
            format: "label CONTAINS %@", "signing back in to Ellis")).firstMatch
        XCTAssertTrue(heading.waitForExistence(timeout: 10))
        let button = app.webViews.buttons["Continue"]
        XCTAssertTrue(button.exists)
        button.tap()
    }

    func testRecoverPendingGoogleDeletion() throws {
        let app = try application()
        XCTAssertTrue(app.staticTexts[
            "Sign in with the same provider to finish the account deletion you requested."
        ].waitForExistence(timeout: 10))
        app.buttons["Continue with Google"].tap()
        try continueGooglePermission(app)
        try chooseGoogleAccount(app)
        continueGoogleSignIn(app)
        XCTAssertTrue(app.staticTexts["Your account was deleted."].waitForExistence(timeout: 20))
        capture(app, name: "Fresh-proof deletion completed")
        app.terminate()
        app.launch()
        XCTAssertTrue(app.buttons["Continue with Google"].waitForExistence(timeout: 15))
        XCTAssertFalse(app.webViews.buttons["Your profile"].exists)
        XCTAssertFalse(app.buttons["Retry deletion"].exists)
        capture(app, name: "Signed out after recovery and restart")
    }

    private func capture(_ app: XCUIApplication, name: String) {
        let screenshot = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        screenshot.name = name; screenshot.lifetime = .keepAlways
        add(screenshot)
        // Provider pages can contain identifiers: keep this result bundle private.
        let tree = XCTAttachment(string: app.debugDescription)
        tree.name = name + " accessibility"; tree.lifetime = .keepAlways
        add(tree)
    }
}
#endif
