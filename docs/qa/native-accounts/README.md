# Native account integration foundation

September 29, 2026; based on backend `d4d07f1`. Candidate modules, not completed sign-in UI or TestFlight acceptance.

Implemented native account WebSocket transport with TLS-only endpoint validation, strict result envelopes, explicit cancellation and 15-second timeout. Credentials use a separate device-only, non-synchronizing Keychain item; the founder's legacy relay item is untouched. AccountSessionManager shares refresh work, preserves owner identity, rejects direct owner switching and discards late refresh results after sign-out. An uncertain rotation drops local in-memory access and attempts secure clearing rather than retrying a spent refresh token. UI/controller teardown and pending remote revocation still need integration.

Official native adapters use AuthenticationServices and pinned GoogleSignIn 9.2.0. Both accept the server challenge nonce; Google's installed public SDK header confirms support on iOS and macOS. The backend exchange now verifies the Google nonce as well as Apple's. Fixed public native/server client IDs, callback schemes and Apple sign-in entitlements are configured; no secrets are bundled. Endpoint remains disabled on the live backend. Apple authorization codes are retained in the adapter result for the upcoming server redemption/revocation implementation, not yet sent.

## Evidence

- Swift 6 typechecking passed for transport, Keychain and session-manager modules.
- Four Xcode CoreTests passed: concurrent callers share refresh, late response cannot restore a signed-out account, owner switch requires teardown/sign-out, insecure and credential-bearing endpoints are rejected.
- Mac app build and iPhone Simulator app build passed with official Google dependency. Initial Mac build found the SDK's Swift error type differs from its Objective-C typedef; corrected to `GIDSignInError` and rebuilt successfully.
- 25 backend account tests passed after Google nonce binding, including live localhost WebSocket and JWKS fixtures. No real provider identity or paid calls.
- Existing visual UI files remain unchanged. No actual provider sheet, Keychain access on a signed device, callback, controller teardown, visible login button or real enrollment has been accepted.

Reproduce native checks with an isolated DerivedData directory:

```sh
xcodegen generate
xcodebuild -project VoiceCompanion.xcodeproj -scheme Mac -destination 'platform=macOS' -derivedDataPath /tmp/ellis-native-accounts-build CODE_SIGNING_ALLOWED=NO -only-testing:CoreTests/AccountSessionTests test
xcodebuild -project VoiceCompanion.xcodeproj -scheme Phone -destination 'generic/platform=iOS Simulator' -derivedDataPath /tmp/ellis-native-accounts-phone CODE_SIGNING_ALLOWED=NO build
```

Next: wire these modules into the existing account UI, serialize refresh across actual services, isolate local recordings/outboxes/caches, wire callbacks, exercise successful/cancelled/failed login and sign-out through the app, then verify real providers on a fresh Release build. Distribution profiles, Apple server lifecycle keys, provider revocation and physical readiness remain release gates. Do not interpret compilation or synthetic tests as those receipts.
