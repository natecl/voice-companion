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

At initial review, PR159's original integration acceptance had two missing real paths (capture is now verified below; refresh failures remain open):

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

## Physical capture/sign-out follow-up

The development-signed physical iPhone build from `1da7e188` was subsequently
installed with the existing production endpoint and deletion-enabled configuration.
Backend `482394e` contains the prior hosted `208ca34` plus only the bounded
transcription-budget compatibility patch; this is not deployment of the whole
account branch. [Sanitized receipt](../account-capture-signout/physical-receipt.json).

The founder started capture, spoke the declared fictional phrase and used profile
Sign out before ending capture. Read-only device/server inspection confirmed an
11.8-second interrupted recording saved to the original Google owner, all 24
preexisting files unchanged, zero unrevoked Google sessions and zero active
requests. Two signed-out snapshots matched, with no late file writes.
The transcript retained recognition errors; no accuracy benchmark is claimed.

The founder then reported empty Apple Notes, confirmed the recording returned
with Google, and confirmed persistent sign-in and transcript reopening after
fully closing/reopening the app. These visible switching/relaunch observations
are founder-reported, distinct from the independently inspected storage/server
evidence. The exercised capture/sign-out gate is complete. Native provider
rejection and network-failure refresh recovery remain unverified; keep the full
account branch unmerged pending that gate and required review/checks.

## Native network-failure recovery

The isolated localhost service was gracefully stopped while the native access
session had naturally expired. The unchanged app relaunched to sign-in with
“Could not connect to the server.” All 13 local content files, including a
clearly fictional owner-scoped transcript seeded before failure, retained their
hashes. Resuming the original server and fresh Apple authentication restored the
same owner. One executed native restart test passed; one executed transcript
reopen test passed and its screenshot was inspected. The UI harness was corrected
to use the observed Transcript switch role and start from a fresh app launch;
initial failed test results remain in the private evidence directory.

[Network recovery receipt](../account-lifecycle/native-network-refresh-recovery.json).
This closes the network-failure portion of the second gate. Actual Apple-provider
rejection and same-owner recovery remain pending. QA-only shorter session issuance
is being prepared to exercise that path without changing native clocks, existing
credentials or production lifetimes. No paid calls occurred.

## Final native provider-rejection recovery and checkpoint disposition

The QA server issued an explicitly configured 660-second access session. No native
clock, Keychain expiry or existing credential lifetime was edited. After staging
one encrypted invalid refresh grant only for the isolated QA owner, the app's
normal refresh called the real Apple token endpoint. Exactly one validation failed
with `provider_authorization_revoked` (the adapter's HTTP 400 / `invalid_grant`
classification), all owner sessions were revoked, and native sign-in showed
“Sign-in is unavailable right now. Please try again.” All 14 content files retained
their hashes. This verifies provider rejection, not external consent removal.

The harness was returned to normal 3600-second issuance before fresh Apple login.
That login returned the same owner with one active session. All 14 files remained
unchanged; one executed native test relaunched the app and reopened the original
fictional transcript. The resulting screenshot was inspected.
[Provider recovery receipt](../account-lifecycle/native-provider-rejection-recovery.json).
No paid model calls, production changes or founder-data mutations occurred.

Independent Astra review approved the bounded QA implementation and evidence;
the primary inspected the live results and final screenshots. Ten focused budget
and QA-lifetime tests passed. The prior 21-module backend and 53-pass native
integration checks remain applicable to unchanged app/account implementation.
Both previously missing original integration paths are now verified within the
stated environments. The account stack is eligible for integration after its
repository checks and final diff review. This is not full Phase 1 or TestFlight
acceptance: physical deletion, independent-human isolation, operational backup
policy and remaining legal/assets/distribution gates retain their separate scope.

## Merge result

PR180, PR179 and PR177–159 were merged through their dependency branches into
main `31b284340fda`. Every merge result retained the reviewed `afe114a` Git tree exactly.
Main had no branch protection or rulesets and the PRs had no required check runs;
recorded local and behavioral checks were still required and reviewed. No merge
override, production deployment or TestFlight upload accompanied integration.
