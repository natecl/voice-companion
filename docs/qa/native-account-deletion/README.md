# Native deletion checkpoint — September 30, 2026

Draft [PR162](https://github.com/natecl/voice-companion/pull/162), implementation `e3172e7`, disabled and not deployed. Depends on PR161 `f6548e8`, which depends on PR160 and PR159. This is local native lifecycle and presentation evidence, not full release acceptance.

## Behavior

The existing profile exposes a confirmation only when `EllisAccountDeletionEnabled` is true. No build currently sets it. A confirmed request saves an owner-bound pending receipt in the atomic device Keychain item before dropping app access. Restore finds pending deletion before any account or legacy fallback. Server completion is persisted before local cleanup; local disk failures can retry without repeating server deletion. Receipt IDs prevent delayed completion from clearing replacement state.

Cleanup removes only the enrolled owner's session directory, memory outbox and note cache. Persistent erasure markers reject late writes and survive cache clearing. Other owners and legacy data remain. Sign-out still permits final local transcript staging while stopping network work; account erasure separately blocks persistence with its markers.

Fresh provider proof recovers accepted deletion. If the original locally saved request never reached the server and its session expired, an optional `expected_owner` permits initiation only for that exact existing verified identity. This performs no enrollment or email matching and issues no content session. A new account created after erasure cannot be deleted by the old owner's request. Apple proof/grant persistence and session revocation remain transactional.

## Executed checks

- 34 native tests: `AccountDeletionTests` (6), `AccountSessionTests` (9), `MemoryTests` (8), `RecordingNotesCacheTests` (11). [Raw results](native-tests.txt). Temporary fictional owners, real file persistence, injected server responses. Covered other-owner/legacy preservation, invalid paths/symlinks, stale writes, pending-store failure, server failure, local failure/retry and late response isolation. No actual Keychain or provider claims from these tests.
- 51 backend account tests. [Results](backend-tests.txt). Includes signed synthetic Google/Apple proofs through real localhost sockets, exact-owner recovery, mismatched identity rejection, expiry, replay and Apple-grant rollback. Provider network operations are fixtures; no live API spend.
- Two iPhone UI tests on dedicated iPhone 17 Pro simulator “Ellis Deletion UI QA”, iOS 26.5, ID `9F0F6623-E33A-4E84-A1EB-B9D7C1530AE7`. [Raw results](phone-ui-tests.txt). `AccountDeletionUIFixture` renders actual RoomWebView/ExperienceSignupView components with fictional state and no credentials, storage, controllers or networking. Tested capability hiding, confirmation/cancel, confirm to pending, retry to recovery, and Google above Apple. This is presentation/bridge evidence, not integrated runtime deletion.
- Screenshots inspected: [profile](profile.png), [confirmation](confirmation.png), [pending retry](pending.png), [recovery](recovery.png). Existing CSS, HTML, icons, fonts and motion files unchanged. Simulator does not establish physical haptics.
- Mac app and iPhone simulator build during test runs. Development builds, not distribution validation.

Reproduce from the repository with the existing Python environment:

```sh
/tmp/ellis-auth-venv/bin/python -m unittest discover -s Backend -p 'test_account*.py'
TEST_RUNNER_VOICE_TEST_PYTHON=/tmp/ellis-auth-venv/bin/python xcodebuild -project VoiceCompanion.xcodeproj -scheme Mac -destination 'platform=macOS' -derivedDataPath /tmp/ellis-native-accounts-build CODE_SIGNING_ALLOWED=NO -only-testing:CoreTests/AccountDeletionTests -only-testing:CoreTests/AccountSessionTests -only-testing:CoreTests/MemoryTests -only-testing:CoreTests/RecordingNotesCacheTests test
xcodebuild -project VoiceCompanion.xcodeproj -scheme Phone -destination 'platform=iOS Simulator,id=9F0F6623-E33A-4E84-A1EB-B9D7C1530AE7' -derivedDataPath /tmp/ellis-native-accounts-phone -only-testing:PhoneUITests/AccountDeletionUITests test
```

The configured Python environment with PyJWT 2.15.1 passes all 65 access mechanical checks; [receipt](access-checks.json) correctly remains `needs_review`, `feature_verified=false`. Fifteen verification-tooling self-tests also passed. Final source differs from the recorded native/UI execution only in whitespace formatting; no behavior or assertions changed.

## Failures diagnosed

Swift could not infer optional callback closures in the root view. Explicitly typed computed actions fixed compilation. An initial test invocation named the wrong target (`VoiceCompanionTests` instead of `CoreTests`) and ran no tests. The first targeted suite exposed an over-broad stopped-state guard suppressing local transcript staging after sign-out. Removed that guard; deletion markers supply the scoped protection. The corrected 34-test run passed. No acceptance assertion was weakened. An initial verifier run used system Python with PyJWT 2.10.1 and failed the existing JWKS cooldown check. Repository requirements pin PyJWT 2.15.1; rerunning with the already-configured venv passed all 65 contracts. System packages and the security assertion were left unchanged.

## Remaining gates

Keep both native and backend deletion flags off. Actual native Keychain crash/relaunch/recovery and complete native-to-backend deletion still need integrated evidence. Google SDK disconnect/revocation is not yet connected (current completion only signs out); implement identity-safe revocation, including a different Google identity chosen during a failed recovery, before enabling. Real Apple revocation/recovery, populated two-owner runtime isolation, cross-window state, physical-device capture and Release lifecycle acceptance remain open.

Backups and restore retention policy, founder-data migration, schema-21 deployment/rollback and privacy/support configuration also remain unfinished. These local checks do not prove forensic erasure or backup deletion. No real account was deleted; the existing signed-in simulator, founder phone, production service and $5 provider budget were untouched.

Google's [disconnect guidance](https://developers.google.com/identity/sign-in/ios/disconnect) distinguishes revoking authorization from signing out. Inspection of pinned GoogleSignIn 9.2.0 confirms `disconnectWithCompletion` loads saved SDK auth state when needed; identity selection must be bound before using that operation.
