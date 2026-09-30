# Account branch merge review — September 30, 2026

Reviewed integration source: `1da7e188401ff5a8d31aa4a633d94a44a342319c`,
`codex/account-qa-resume`, including merged documentation PR178.
Target main was `d4d07f1`. No main merge or deployment occurred in this review.

## Fresh checks

- The `access --checks-only` backend runner passed all 21 mapped offline modules,
  including auth, deletion/finalization, migration, isolation and backup/restore.
- Mac native account/session/deletion/grant/migration/capture/memory/cache suites:
  53 passed, 1 skipped, 0 failed. The skipped test explicitly requires a private
  physical snapshot; the accepted prior rehearsal/cutover was not replayed.
- After attaching the inspected native fixture receipt, the actual mechanical
  verifier returned `needs_review`, no unresolved mechanical checks and
  `feature_verified: false`. It does not establish the live paths below.
- A development-signed iPhone Release build succeeded at the same source.
  It was not installed and does not establish physical behavior.

Reproduction: `/tmp/ellis-auth-venv/bin/python scripts/verify_feature.py access --checks-only`.
Native command uses scheme Mac, isolated DerivedData, `CODE_SIGNING_ALLOWED=NO`,
`TEST_RUNNER_VOICE_TEST_PYTHON=/tmp/ellis-auth-venv/bin/python` and CoreTests classes
AccountSessionTests, AccountDeletionTests, GoogleAccountGrantTests,
FounderAccountMigrationTests, RecordingLifecycleTests, MemoryTests and
RecordingNotesCacheTests. Private native log: `/tmp/ellis-account-integration-native.log`;
Release build log: `/tmp/ellis-account-integration-phone.log`.

## Independent review disposition

Two read-only Astra review lanes inspected original PR scopes, source and
receipts. No new correctness defect was reproduced. PR160–177 have evidence for
their bounded primitives/tooling/fixes. Actual founder migration/cutover receipts
supersede earlier pending statements; do not repeat that mutation. Provider,
Keychain and deletion source is unchanged from the relevant accepted receipts;
the later native capture callback fix was included in fresh controller tests.

PR159's original integration acceptance still has two missing real paths:

1. Actual capture → profile Sign out → capture stops and received text remains
   with its original owner, with no stale writes or visibility to another owner.
   Controller-injected callbacks do not establish the profile/notification/audio
   integration.
2. Native provider-rejection and network-failure recovery during refresh,
   including truthful sign-in/error state, preserved local content and same-owner
   recovery. Happy-path rotation and successful deletion are not this evidence.

Apple refresh validates its provider grant and explicitly handles invalid_grant.
Google Ellis-session refresh does not poll Google consent. Do not predeclare or
claim that externally removing Google consent immediately revokes Ellis sessions;
that expectation needs an explicit contract rather than an invented passing test.

Physical deletion, independent-human isolation, production backup policy and
release assets remain broader Phase 1/release gates. They are not retroactively
new acceptance criteria for every default-off backup primitive. Conversely,
the two original account integration gaps cannot be silently reclassified to
merge the complete branch. Keep the root PR draft until they are verified or the
founder explicitly revises the checkpoint scope. No paid calls in this review.
