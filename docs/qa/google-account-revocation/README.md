# Google revocation and secure deletion progress

September 30, 2026. Dependent draft candidate based on PR162 `aa435b6`; deletion remains disabled and nothing is deployed. Existing UI components/order/styles are unchanged.

## Contract

Successful Google enrollment captures the SDK user's refresh grant and subject together with the identity token. Only after the backend accepts that sign-in are the grant and account saved together in the device-local Keychain item. App-session rotation preserves that grant. Deletion carries it into its durable pending receipt; it never revokes whichever user the Google SDK happens to hold after a later failed login.

Server completion is saved first, then enrolled-owner local content is removed, then Google authorization is revoked. Successful revocation clears the grant and persists completion before clearing pending state. Retries after local cleanup or final Keychain failure do not repeat a durably completed server/revocation phase. Interrupted persistence may require an explicit retry, never an automatic provider loop.

The revoker POSTs a form-encoded token in the body to the fixed Google HTTPS endpoint. Its ephemeral URLSession has no persistent cookie/cache storage, rejects redirects, and has 15-second request/resource bounds. Only HTTP 200 confirms revocation. The specific HTTP 400 `invalid_token` response requests fresh Google sign-in. Generic 400s, redirects, network/server failures and unrecognized responses remain pending; provider details never appear in user-facing errors.

After server erasure, fresh Google sign-in may replace only the original subject's grant. It does not call account enrollment or recreate content, and does not require another backend challenge. A different subject/provider cannot replace that receipt. Older enrollments without a captured grant require backend-verified same-owner proof before server erasure. The runtime reloads saved progress after a failure so it does not mistakenly restart an already completed server phase.

Official reference: [Google OAuth token revocation](https://developers.google.com/identity/protocols/oauth2/native-app#tokenrevoke). Google documents project-wide authorization revocation and possible propagation delay. The saved-grant adapter deliberately avoids the SDK's global-current-user disconnect selection. Real success/retry/revocation propagation still requires acceptance QA.

## Executed evidence

- [24 native tests](native-tests.txt): deletion (9), account sessions (9), Google revoker (6). Includes exact grant selection, failed revocation retry, missing-grant reauthentication before deletion, final Keychain failure, same-subject-only recovery, backward-compatible decoding, encoded POST body, error classification and hidden provider errors.
- [Simulator Keychain lifecycle](keychain-relaunch.txt): actual app, Keychain and filesystem across three launches/two terminations on dedicated iPhone 17 Pro “Ellis Deletion UI QA,” iOS 26.5 (`9F0F6623-E33A-4E84-A1EB-B9D7C1530AE7`). Saves a fictional account, persists server completion before an injected local failure, relaunches and verifies the saved grant/phase, removes its actual fixture files, completes, then relaunches signed out. Server and revocation success are injected; it cannot delete a real account. The DEBUG fixture uses a UUID-specific Keychain service and filesystem root, never the real account namespace. An initial fixture compile failure was corrected by adding a missing `try`; no behavioral assertion changed.
- Negative endpoint investigation: one HTTPS request from Python with a wholly fabricated token returned 400 `{"error":"invalid_token"}`. This established the error contract, not real-grant revocation. The [separately opted-in native transport check](native-google-negative.txt) passed with one additional fabricated-token request through the actual Swift URLSession adapter and actual Google endpoint. It classified the error as reauthentication required. No real grant was used and there were no automatic retries.

Native test command:

```sh
TEST_RUNNER_VOICE_TEST_PYTHON=/tmp/ellis-auth-venv/bin/python xcodebuild -project VoiceCompanion.xcodeproj -scheme Mac -destination 'platform=macOS' -derivedDataPath /tmp/ellis-native-accounts-build CODE_SIGNING_ALLOWED=NO -only-testing:CoreTests/AccountDeletionTests -only-testing:CoreTests/AccountSessionTests -only-testing:CoreTests/GoogleGrantRevokerTests test
```

Simulator checks:

```sh
xcodebuild -project VoiceCompanion.xcodeproj -scheme Phone -destination 'platform=iOS Simulator,id=9F0F6623-E33A-4E84-A1EB-B9D7C1530AE7' -derivedDataPath /tmp/ellis-native-accounts-phone -only-testing:PhoneUITests/AccountDeletionUITests/testKeychainAndLocalErasureSurviveTwoRelaunches test
# Explicit live negative-only check: one fabricated token; no real grant.
TEST_RUNNER_ELLIS_GOOGLE_NEGATIVE_QA=1 xcodebuild -project VoiceCompanion.xcodeproj -scheme Phone -destination 'platform=iOS Simulator,id=9F0F6623-E33A-4E84-A1EB-B9D7C1530AE7' -derivedDataPath /tmp/ellis-native-accounts-phone -only-testing:PhoneUITests/AccountDeletionUITests/testRealGoogleInvalidGrantThroughNativeTransport test
```

Release iPhone-simulator build passed on this candidate with `xcodebuild -project VoiceCompanion.xcodeproj -scheme Phone -configuration Release -destination 'generic/platform=iOS Simulator' -derivedDataPath /tmp/ellis-native-accounts-phone build`. This checks compilation with DEBUG fixtures excluded, not App Store signing or physical installation.

## Remaining release gates

No real account/grant has been revoked or deleted. Review identified the next integration requirement: the server currently releases the erased Google identity before native revocation finishes. Keep that identity reserved through confirmed native revocation (or move revocation into server orchestration) so another device cannot re-enroll the same identity while the original deletion still awaits revocation. This is an unresolved release requirement, not permission to enable this candidate. Real Google successful revocation, expired/already-revoked grant recovery, Apple revocation/recovery, full native-to-backend runtime deletion, multi-window state, populated two-user isolation and physical/Release lifecycle remain unverified. Simulator Keychain evidence does not establish physical locked-device behavior. Backup policy, founder migration and schema-21 rollout remain open. Keep the feature disabled and the PR draft until the applicable gates are satisfied.
