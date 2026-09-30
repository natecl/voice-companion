# Native account integration foundation

September 29, 2026; based on backend `d4d07f1`. Integrated native candidate; real-provider and TestFlight acceptance remain incomplete.

Implemented native account WebSocket transport with TLS-only endpoint validation, strict result envelopes, explicit cancellation and 15-second timeout. Credentials use a separate device-only, non-synchronizing Keychain item; the founder's legacy relay item is untouched. AccountSessionManager shares refresh work, preserves owner identity, rejects direct owner switching and discards late refresh results after sign-out. An uncertain rotation drops local in-memory access and attempts secure clearing rather than retrying a spent refresh token. Controller teardown is integrated below; real capture/sign-out and remote-revocation acceptance still require verification.

Official native adapters use AuthenticationServices and pinned GoogleSignIn 9.2.0. Both accept the server challenge nonce; Google's installed public SDK header confirms support on iOS and macOS. The backend exchange now verifies the Google nonce as well as Apple's. Fixed public native/server client IDs, callback schemes and Apple sign-in entitlements are configured; no secrets are bundled. Endpoint remains disabled on the live backend. Apple authorization codes are sent over the account TLS connection for server redemption; provider credentials are never bundled.

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

Next: exercise successful/cancelled/failed login and sign-out through the integrated app, then verify real providers on a fresh Release build. Distribution profiles, Apple server lifecycle keys, provider revocation and physical readiness remain release gates. Do not interpret compilation or synthetic tests as those receipts.

## Frontend integration candidate

Fresh installs now enter the existing signup view, whose Google/Apple buttons call native adapters; successful responses install the separate Keychain session and open the existing companion room. Legacy founder credentials retain their previous app path. Managed sign-out leaves a durable marker so credential loading cannot fall back to the founder account. Managed recordings have owner-scoped directories and reject mismatched/unowned records. Capture, chat, dictation, note loading and outbox work receive teardown on account change. Shared-room and Mac profile panels reuse existing row components for Sign out. Runtime refresh is shared and runs before access expiry.

Actual iPhone Simulator UI test passed on the dedicated Ellis Account QA simulator (iOS 26.5): both existing provider buttons are enabled, Google is above Apple, and fresh launch has no startup error. Inspected [the screenshot](fresh-account-screen.png): no clipping, unchanged signup layout/components and clean sign-in status. The first check exposed the decorative G in Google's accessibility label; it is now hidden from accessibility only. An unsigned simulator run then exposed a Keychain startup error that the original button-only assertion missed; the stronger test requires the clean status and passes with normal ad-hoc simulator signing. Use `CODE_SIGNING_ALLOWED=YES CODE_SIGN_IDENTITY=-` for Keychain/UI QA.

The local socket regression initially used Xcode's default Python without websockets. Run native memory tests with `TEST_RUNNER_VOICE_TEST_PYTHON=/tmp/ellis-auth-venv/bin/python` (requirements installed). This is an environment correction, not a production workaround.

These receipts establish initial screen and bounded local lifecycle behavior, not actual provider enrollment, sign-out during real capture, full two-user isolation, legal-page readiness or release acceptance. Legal links remain explicitly unconfigured. Real Apple redemption/revocation verification, deployment and real-provider/device QA remain required. Keep PR159 draft until those integration gates are satisfied.

Final local lifecycle regression: 15 selected CoreTests pass, including the real local memory socket fixture, owner-mismatch storage rejection, outbox preservation without network work after shutdown, session generation and relay configuration validation. Runtime refresh responses also check an account generation before applying state.

## Apple server lifecycle candidate

Native exchange includes Apple's one-time authorization code. The backend redeems it at Apple's fixed token endpoint with a short-lived ES256 client secret, independently verifies the returned ID token, and requires the same subject, audience and challenge nonce. Refresh grants are encrypted with Fernet under a deployment key kept outside the database. App refresh validates the stored Apple grant; an explicit provider invalid-grant response revokes that owner's local access credentials. Outages fail closed without retrying provider calls. Ordinary sign-out revokes the app session, not Apple consent. The provider revoke helper is implemented, but account deletion has not yet been connected.

30 backend checks passed: 25 account tests including real localhost sockets and synthetic signed tokens, four Apple OAuth request/signature/failure tests, and encrypted grant isolation/reopen/wrong-key verification. Mismatched redeemed subject/nonce and missing code are rejected. This used no real Apple credentials or paid API calls.

Enabling accounts now additionally requires `VOICE_APPLE_TEAM_ID`, `VOICE_APPLE_KEY_ID`, `VOICE_APPLE_PRIVATE_KEY` (P-256 PEM), and `VOICE_ACCOUNT_ENCRYPTION_KEY` (Fernet key), alongside the documented client IDs. Keep the encryption key backed up separately from the admission database; losing it makes saved grants unreadable. The Apple key has now been registered and secured locally (see the account enrollment packet); deployment secrets are now configured in Render and verified by readback, while `VOICE_ENABLE_ACCOUNTS=0` keeps the endpoint disabled.

## Hosted migration rehearsal

September 29: read-only Render inspection confirmed live commit `70f494b`, Starter plan, one instance, existing 1 GB disk and auto-deploy off. Default SSH identity failed; the existing dedicated `voice_companion_render` identity successfully accessed the service. No new access grants were needed. No account environment names were configured.

[Sanitized migration receipt](hosted-migration-rehearsal.json): private SQLite online snapshots of memory, usage, memory-budget and notes-budget were integrity-checked. Candidate `a18528e` migrated only the copied memory database from schema 19 to 20, preserving all existing rows across 39 tables. Account session/grant initialization added four tables to the copied usage database while preserving all existing rows across its 10 original tables, including policy, reservations and charges. Both migrated copies passed integrity checks. This is a rehearsal on independent per-database snapshots, not the coordinated backup required immediately before deployment. No live database, environment, deployment or quota was changed.

## Refresh and active-request review

Review found that routine rotation immediately revoked an access token still used by an active capture. The backend now consumes the refresh token while leaving the prior access token valid only until its original expiry; sign-out, provider revocation and refresh replay still revoke the family/owner immediately. Native connections for capture, chat, memory, notes and proactive requests resolve credentials through the same session manager immediately before opening a socket. Refresh starts with ten minutes remaining, covering the five-minute capture bound and finalization. A restored expired access token is refreshed before saving a new Keychain value. Request refresh checks the original owner and backend before substituting credentials.

The real local relay/socket test rotates an account while capture is open, crosses the periodic authorization check, sends fixture audio and receives transcript completion. All six hosted relay tests and 26 account tests passed, including original-expiry enforcement and family sign-out/replay. Native tests cover early refresh, shared rotation, restored expired access, owner/backend rejection and stale response suppression. These are synthetic-provider/local receipts, not real microphone or Apple/Google acceptance.

## Disabled deployment configuration prepared

After key registration and refresh review, the existing Render API access configured the Google server/native IDs, Apple native IDs/team/key/private key and a new Fernet encryption key using per-variable updates. Readback confirmed exact values internally without printing secrets, and every pre-existing environment value remained unchanged. The prior environment configuration and local keys are stored in owner-only credential storage outside the repository. `VOICE_ENABLE_ACCOUNTS=0` remains explicit; no deploy was triggered. A coordinated pre-deployment backup, candidate rollout review and real-provider/device acceptance still remain.

Refresh review final checks: 26 account backend tests and six hosted relay tests pass. The final nine account-session native tests pass; the preceding impacted run also passed eight memory and two configuration tests. iPhone Simulator build passes. Access checks-only verifier has no mechanical issues and correctly remains `needs_review` / not feature-verified.

## Account endpoint deployed for integration QA

September 30 UTC (September 29 local): candidate `c897dec55af9707f74d298772bc3318af6372831` was deployed first with accounts disabled (`dep-dau6esmk1f9s73ai2o6g`), then with accounts enabled (`dep-dau6gsdg1s2s73bl89e0`). Before deployment, all 24 top-level SQLite databases were write-locked together, backed up with SQLite's backup API and integrity-checked; active admission requests were zero. Backup directory: `/var/data/voice-companion/backups/accounts-20260930T013520Z`. A private local copy outside the repository was verified against every manifest hash.

After deployment, all existing rows matched the backup across usage (10 tables), memory (39), memory-budget (11) and notes-budget (2). Memory schema is now 20. Health is 200 and workers are idle without recorded failures. The account configuration passed construction using the actual serving process environment on temporary database copies. Render's SSH shell drops the trailing equals from the Fernet value, but API readback and serving-process environment retain the correct 44-byte value; no key change was needed.

[Live negative-path receipt](live-account-smoke.json): Google and Apple challenges work; malformed identity tokens, unknown refresh tokens, browser Origin and unauthenticated memory requests are rejected. These requests made no provider calls and issued no accounts. Real enrollment is still unverified.

Rollback: set `VOICE_ENABLE_ACCOUNTS=0` and explicitly redeploy the same candidate to close enrollment without changing data. If account implementation rollback is needed, merged `d4d07f10a24e1b4871df29b9f1318eed571a5e2d` with accounts disabled understands schema 20. Never restore the old schema-19 binary against migrated data or overwrite current ledgers with a pre-deploy backup. Render auto-deploy remains off; existing tier/disk/quotas unchanged.

Release archive: first attempt lacked a selected team; supplying team `7HF6VDCZF7` produced an archive but exposed missing resolved version metadata. Project settings now include the existing team, marketing version `0.1.0`, build `1` and explicit version substitutions. Rebuilt archive `/tmp/ellis-accounts-versioned-release.xcarchive` contains those values and Apple sign-in entitlement. It is development-signed (`get-task-allow=true`), not an App Store distribution export. App icon, legal/support assets, App Store record, distribution export/upload and independent install remain incomplete. No founder phone installation occurred.

## First real Apple enrollment

Founder confirmed readiness and completed Apple authentication in the isolated Ellis Account QA simulator. Release `0.1.0 (1)` from native candidate `07f9977` entered the existing companion UI. Read-only backend inspection found one Apple identity, one unrevoked account session and one encrypted Apple grant, confirming the real native token/code exchange reached the deployed account service. Terminating and relaunching the app reopened the companion without another sign-in. [Sanitized receipt](apple-real-sign-in.json) and [inspected screen](apple-real-sign-in.png). No transcript/model call or founder-phone modification occurred.

Google enrollment, token rotation against the real Apple grant, sign-out, second-user isolation and physical-device acceptance remain open. Device Hub exposed a screenshot but its coordinate interaction twice returned noWindowsAvailable after refreshing the window binding; user assistance is needed for the existing menu/sign-out tap rather than bypassing UI automation controls.

Founder then tapped Sign out. The app returned to the provider screen, backend inspection confirmed zero unrevoked account sessions, and terminating/relaunching stayed signed out with a clean status. This verifies the real Apple session sign-out path and signed-out persistence; account erasure, capture-in-progress sign-out and Google/two-user acceptance remain separate gates.
