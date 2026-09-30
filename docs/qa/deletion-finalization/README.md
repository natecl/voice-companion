# Server finalization of Google account deletion

September 30, 2026. Implementation checkpoint `2d21c76`; dependent candidate based on PR163 `35e0bfd`. Not deployed; both deletion flags remain off. This replaces the prior native revocation phase. It preserves the saved owner-bound grant and the existing UI.

## Closed interval

The server keeps the Google identity reserved after erasing content. `delete_account` / `resume_deletion` return `awaiting_google_revocation` for Google; Apple still completes its existing server-side revocation/erasure path. A small admission table records whether Google account content was erased. No Google grant is stored in that table.

Native cleanup sends the saved Google grant and authenticated deletion receipt to `finish_google_deletion` over the original account TLS endpoint. The server verifies the receipt and completed content phase, calls the fixed Google revocation endpoint, and releases the identity only on HTTP 200. Enrollment, fresh-proof recovery and finalization share the account mutation lock. Cancellation waits for the bounded provider call before releasing that lock. A client assertion alone cannot complete deletion.

Failures retain the identity reservation and pending native receipt. The server maps Google's specific `invalid_token` response to fresh-proof recovery; this reuses its retained identity hash after the original identity/content rows are erased. Recovery remains same-owner and issues no content session. A successful finalization lost in transit can be retried without repeating the provider call. Old completed receipts cannot target a newly enrolled owner.

Native transport decodes explicit deletion status and persists phases before cleanup. Local Google HTTP/revocation-only reauthentication code was removed; the existing backend proof verifier now handles all recovery, including after content erasure. The Google grant remains in device Keychain until finalization succeeds. No Google tokens are sent to UI or logs.

## Evidence

- [54 account tests](account-tests.txt), including three new finalization cases: reservation across restart and provider failure; fresh proof after content erasure; unrelated/stale receipt isolation; lost-response idempotency; rejection before erasure/on Apple accounts; cancellation while a provider operation is held. Existing signed synthetic Google/Apple proof tests still traverse actual localhost sockets and now exercise the finalization endpoint.
- [Three Google HTTP adapter tests](google-oauth-tests.txt): fixed HTTPS POST, form encoding, five-second timeout, invalid input, invalid-token classification, safe errors, no redirects and no automatic retries. These replace tests of the removed native HTTP adapter. No live Google request was made in this checkpoint.
- [19 native tests](native-tests.txt): deletion coordinator, session rotation and credential decoding. Covers pending grant recovery, receipt/grant selection, failed finalization retry, local failures and persisted completion. The prior local subject-comparison path is replaced by existing cryptographic backend recovery tests.
- [Actual native/TLS backend run](native-backend-tests.txt), with [server assertions](native-backend-result.json): dedicated iPhone 17 Pro simulator, iOS 26.5, ID `9F0F6623-E33A-4E84-A1EB-B9D7C1530AE7`; actual URLSession WebSockets, account service, SQLite erasure, Keychain and filesystem through three app launches. Three native requests: erase content, fail fictional revocation, relaunch and finish fictional revocation. Other-owner data remains. Same-identity re-enrollment is rejected between phases and succeeds with a new owner only after completion. Provider authentication/success responses are synthetic, not real Google acceptance.
- [Neighboring Apple/local content replay](apple-replay.json) still passes, preserving other-owner transcript/notes/chat and spending rows. The receipt's `not_proven` list describes that replay alone, not the separate native TLS run.
- Release iPhone-simulator build passed with the production compilation path and DEBUG drivers excluded; this is not distribution signing or physical installation evidence.
- 15 verifier self-tests passed after catalog inclusion of finalization and Google OAuth suites.

The TLS fixture generates a one-day localhost certificate in its supplied temporary output directory. Only the dedicated simulator's trusted root store received it; host trust and the founder's phone/signed-in simulator were untouched. Generated keys, account fixtures and database paths stay outside git. The server exited normally after all assertions passed.

Initial setup found the dedicated simulator shut down; it was booted and the certificate was installed before app execution. The first app run exposed a fixture-only UUID case normalization error and failed before network requests. The fixture now preserves the exact server-issued owner string. After that correction, the same still-running server and its untouched fixture accounts passed the complete run. No acceptance assertions were weakened.

## Reproduction

```sh
/tmp/ellis-auth-venv/bin/python -m unittest discover -s Backend -p 'test_account*.py'
/tmp/ellis-auth-venv/bin/python -m unittest discover -s Backend -p 'test_google_oauth.py'
TEST_RUNNER_VOICE_TEST_PYTHON=/tmp/ellis-auth-venv/bin/python xcodebuild -project VoiceCompanion.xcodeproj -scheme Mac -destination 'platform=macOS' -derivedDataPath /tmp/ellis-native-accounts-build CODE_SIGNING_ALLOWED=NO -only-testing:CoreTests/AccountDeletionTests -only-testing:CoreTests/AccountSessionTests -only-testing:CoreTests/GoogleAccountGrantTests test
/tmp/ellis-auth-venv/bin/python scripts/qa/native-deletion-server.py --output /tmp/ellis-finalization-tls-qa
```

Use a new output directory for each TLS run. Boot the dedicated simulator and add its generated `cert.pem` using `xcrun simctl keychain <simulator-id> add-root-cert <certificate>`. Read `account.json` into the test runner environment variable `TEST_RUNNER_ELLIS_ACCOUNT_QA_NETWORK` without logging it; run `PhoneUITests/AccountDeletionUITests/testNativeDeletionAgainstLocalTLSBackend` under the Phone scheme. After the test passes, send SIGINT to that exact fixture server process; it checks the database/operation counts and writes `result.json`. Do not point this fixture at production or an existing real account namespace.

The [access checks-only receipt](access-checks.json) has no unresolved mechanical checks and deliberately remains `feature_verified=false`, `needs_review`.

## Remaining gates

The full AccountRuntime provider prompts and real Google/Apple grant revocation/recovery, expired/revoked real sessions, populated real-user isolation, multi-window behavior, physical/Release installation and lifecycle remain unverified. The TLS test exercises actual native storage/coordinator/transport and service, with synthetic enrollment/provider responses and a DEBUG driver, not production provider authentication or human UI acceptance. Previous presentation evidence remains applicable; no design assets/components changed.

No deletion candidate has been deployed with its flag on, so there are no live pending deletions from the earlier draft protocol to migrate. This candidate adds its admission table without replacing existing ledger rows; deploy only as a reviewed matching native/backend pair with schema-21-compatible rollback. Backups/restore policy, explicit founder migration, privacy/support, billing and distribution gates remain open. Keep this draft and disabled until applicable release evidence is complete. No paid calls or real account changes occurred.
