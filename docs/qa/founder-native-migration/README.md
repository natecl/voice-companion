# Explicit founder phone migration candidate

September 30, 2026. Candidate implementation; no physical phone changes, hosted
migration, or ordinary sign-in imports. Builds on PR166's server-copy rehearsal.

An operator stages `founder-google-migration.json` inside the app's VoiceCompanion
Application Support directory while it is stopped. Its version 1 payload contains
`owner`, the exact account `endpoint`, and `sessions`/`outbox` maps of JSON filenames
to SHA256 hashes. No UI or ordinary enrollment creates this file. Stage only after
a coordinated backup, fresh Google identity verification, reviewed server binding
and credential revocation, and a fresh local inventory. Do not use an old snapshot
as the actual cutover plan. Keep the plan and any raw owner/content outside Git.

Startup with a plan blocks legacy capture and shows the existing sign-in screen.
Only a Google session for the preserved owner and exact endpoint can activate it.
The helper checks all file names/hashes and decoded session owners, rejects
unplanned files, destination conflicts and deletion barriers, and checks symlinks
through every component within the app-owned root. It atomically renames the
legacy sessions directory to accounts/owner/sessions. The already owner-scoped
outbox stays byte-identical in its existing location. Interrupted recordings are
preserved for the normal recovery behavior; migration does not rewrite completion
flags, notes, transcript text or IDs.

A surviving plan permits restart only with the exact moved files. AccountRuntime
saves the accepted account before removing the plan. Failure keeps migration
closed; a wrong sign-in's newly issued session is revoked. A malformed plan is
re-read and rejected on sign-in rather than silently falling back to legacy.
No typography, colors, layout, animation or shared UI assets changed.

## Evidence

`native-tests.txt`: 15 selected native tests passed (six migration, nine session
lifecycle). The migration tests exercise actual temporary filesystem moves,
restart by decoding the pending plan again, wrong provider/owner/endpoint,
changed files, occupied destination, extra outbox data, deletion barriers,
missing plans and linked destination parents. The explicit private-snapshot test
copied the previously inspected physical app snapshot into a temporary directory,
then moved all four sessions with their original bytes and retained all 20 outbox
files. It confirmed the original snapshot's sessions were untouched. Its account
session is synthetic; this is local filesystem evidence, not real OAuth or a
physical in-place migration. No provider calls or spending. The Phone Release simulator build also passed
with the runtime integration; this is compilation evidence, not app-flow acceptance.

The initial command used a nonexistent CoreTests scheme; reran with the actual
Mac scheme. A linked-parent regression initially failed because resolving an
absent leaf did not resolve its parent. Ancestor checking fixed it, then exposed
macOS's trusted /var alias; checks now cover all components inside the explicit
app root, leaving system-provided ancestors above that root alone. The full
selected rerun passed, including the linked-parent rejection. The physical
snapshot also showed non-completed saved captures; their bytes are intentionally
preserved rather than rejecting or marking them complete.

Reproduce with private fixture access (omit TEST_RUNNER_ELLIS_MIGRATION_SNAPSHOT
for routine tests; only that private rehearsal is then skipped):

```sh
TEST_RUNNER_ELLIS_MIGRATION_SNAPSHOT=/private/path/to/VoiceCompanion \
 xcodebuild test -project VoiceCompanion.xcodeproj -scheme Mac \
 -destination 'platform=macOS' -derivedDataPath /tmp/ellis-native-accounts-build \
 -only-testing:CoreTests/FounderAccountMigrationTests \
 -only-testing:CoreTests/AccountSessionTests CODE_SIGNING_ALLOWED=NO
```

## Remaining acceptance

Runtime/keychain interruption behavior and sign-in presentation need actual app
QA, including wrong Google selection, real sign-in, restart and reopened notes.
Physical Release migration must use fresh source/destination proof and a stopped
app/server cutover. This candidate is not merged or ready to run against the
founder's live installation. Operator orchestration and final acceptance remain
part of Phase 1.
