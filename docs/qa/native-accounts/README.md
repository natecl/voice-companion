# Native account integration foundation

September 29, 2026; based on backend `d4d07f1`. Integrated native candidate; real-provider and TestFlight acceptance remain incomplete.

Implemented native account WebSocket transport with TLS-only endpoint validation, strict result envelopes, explicit cancellation and 15-second timeout. Credentials use a separate device-only, non-synchronizing Keychain item; the founder's legacy relay item is untouched. AccountSessionManager shares refresh work, preserves owner identity, rejects direct owner switching and discards late refresh results after sign-out. An uncertain rotation drops local in-memory access and attempts secure clearing rather than retrying a spent refresh token. Controller teardown is integrated below; real capture/sign-out and remote-revocation acceptance still require verification.

Official native adapters use AuthenticationServices and pinned GoogleSignIn 9.2.0. Both accept the server challenge nonce; Google's installed public SDK header confirms support on iOS and macOS. The backend exchange now verifies the Google nonce as well as Apple's. Fixed public native/server client IDs, callback schemes and Apple sign-in entitlements are configured; no secrets are bundled. Endpoint remains disabled on the live backend. Apple authorization codes are retained in the adapter result for the upcoming server redemption/revocation implementation, not yet sent.

## Evidence

- Swift 6 typechecking passed for transport, Keychain and session-manager modules.
- Four Xcode CoreTests passed: concurrent callers share refresh, late response cannot restore a signed-out account, owner switch requires teardown/sign-out, insecure and credential-bearing endpoints are rejected.
- Mac app build and iPhone Simulator app build passed with official Google dependency. Initial Mac build found the SDK's Swift error type differs from its Objective-C typedef; corrected to `GIDSignInError` and rebuilt successfully.
- 25 backend account tests passed after Google nonce binding, including live localhost WebSocket and JWKS fixtures. No real provider identity or paid calls.
- Initial module checkpoint left UI untouched. The later integration and screen evidence below supersede that limitation; actual provider sheets, signed-device Keychain lifecycle and real enrollment remain unverified.

Reproduce native checks with an isolated DerivedData directory:

```sh
xcodegen generate
xcodebuild -project VoiceCompanion.xcodeproj -scheme Mac -destination 'platform=macOS' -derivedDataPath /tmp/ellis-native-accounts-build CODE_SIGNING_ALLOWED=NO -only-testing:CoreTests/AccountSessionTests test
xcodebuild -project VoiceCompanion.xcodeproj -scheme Phone -destination 'generic/platform=iOS Simulator' -derivedDataPath /tmp/ellis-native-accounts-phone CODE_SIGNING_ALLOWED=NO build
```

Next: wire these modules into the existing account UI, serialize refresh across actual services, isolate local recordings/outboxes/caches, wire callbacks, exercise successful/cancelled/failed login and sign-out through the app, then verify real providers on a fresh Release build. Distribution profiles, Apple server lifecycle keys, provider revocation and physical readiness remain release gates. Do not interpret compilation or synthetic tests as those receipts.

## Frontend integration candidate

Fresh installs now enter the existing signup view, whose Google/Apple buttons call native adapters; successful responses install the separate Keychain session and open the existing companion room. Legacy founder credentials retain their previous app path. Managed sign-out leaves a durable marker so credential loading cannot fall back to the founder account. Managed recordings have owner-scoped directories and reject mismatched/unowned records. Capture, chat, dictation, note loading and outbox work receive teardown on account change. Shared-room and Mac profile panels reuse existing row components for Sign out. Runtime refresh is shared and runs before access expiry.

Actual iPhone Simulator UI test passed on the dedicated Ellis Account QA simulator (iOS 26.5): both existing provider buttons are enabled, Google is above Apple, and fresh launch has no startup error. Inspected [the screenshot](fresh-account-screen.png): no clipping, unchanged signup layout/components and clean sign-in status. The first check exposed the decorative G in Google's accessibility label; it is now hidden from accessibility only. An unsigned simulator run then exposed a Keychain startup error that the original button-only assertion missed; the stronger test requires the clean status and passes with normal ad-hoc simulator signing. Use `CODE_SIGNING_ALLOWED=YES CODE_SIGN_IDENTITY=-` for Keychain/UI QA.

The local socket regression initially used Xcode's default Python without websockets. Run native memory tests with `TEST_RUNNER_VOICE_TEST_PYTHON=/tmp/ellis-auth-venv/bin/python` (requirements installed). This is an environment correction, not a production workaround.

These receipts establish initial screen and bounded local lifecycle behavior, not actual provider enrollment, sign-out during real capture, full two-user isolation, legal-page readiness or release acceptance. Legal links remain explicitly unconfigured. Apple authorization-code redemption/revocation, deployment and real-provider/device QA remain required. Keep PR159 draft until those integration gates are satisfied.

Final local lifecycle regression: 15 selected CoreTests pass, including the real local memory socket fixture, owner-mismatch storage rejection, outbox preservation without network work after shutdown, session generation and relay configuration validation. Runtime refresh responses also check an account generation before applying state.
