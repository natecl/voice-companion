# Independent-person revocation boundaries — September 30, 2026

Local, uncommitted checkpoint on `cursor/account-isolation-revocation-20260930`,
base `b365ad52cfed1bd480c8f5a2566725713629fe5b`. Two fictional people with
separate Google subjects (`fictional-person-avery`, `fictional-person-blake`)
and distinct server-derived owners, temporary SQLite stores and actual loopback
WebSockets only. No live provider, private account, credential, simulator,
device, deployment or paid call was used. Not deployed.

## Diagnosis

Owner scoping held throughout: every reviewed route derives the owner from the
authenticated credential, and no case let one person's data reach the other.
The gaps were revocation boundaries on two routes that predate the PR171
companion fix:

- **`/ask`** (`Backend/ask.py`, hosted with paid recall ranking) emitted events
  without reauthorizing. A session signed out while recall was in flight still
  received its private recall `context`, a full provider answer and `done`; the
  request was recorded `completed`. Provider revocation between two deltas let
  the next delta through. Revocation during recall validation still started
  paid generation.
- **`/stt`** (`Backend/relay.py`) only checked every second. After sign-out or
  provider revocation it forwarded further paid audio upstream and relayed the
  next transcript event to the revoked client.

## Fix

- `/ask`: `send` reauthorizes before each non-error event (errors stay sendable
  so a revoked client receives `unauthorized`), and generation reauthorizes
  immediately before the provider stream starts.
- `/stt`: reauthorize before each forwarded audio frame (before byte
  accounting), before forwarding `audio.done`, and before relaying each
  upstream event. The periodic monitor remains for idle sessions. The local
  development relay without admission is unchanged.

In every revoked case the reservation finishes `failed`, never refunded, and
the other person's following request completes with only their own content.

## Regression evidence

`Backend/test_account_independent_isolation.py`, 6 tests: four `/ask` and
`/stt` revocation regressions via `AccountSessions.sign_out` and
`ProviderGrants.revoke_local_owner`, one pre-provider check, and one companion
characterization (revoked turn stays `failed` after the same person signs in
again; histories stay owner-separated).

| Source under test | Result | Output |
| --- | --- | --- |
| Committed `ask.py`/`relay.py` at `b365ad5` | 6 run, **5 failures**; companion characterization passes (PR171 covers it) | [baseline.txt](baseline.txt) |
| Fix without the pre-provider check | 6 run, **1 failure**: paid answer started after sign-out | [send-boundary-only.txt](send-boundary-only.txt) |
| Final fix | **6 passed** | [fixed.txt](fixed.txt) |

Repeats: final fix 25/25 and 20/20 passing runs; committed-source replay failed
identically (5 failures) in 10/10 runs.

Commands, from the repository root. The baseline and send-only runs shadow the
modules from gitignored `work/` (committed files byte-identical to `b365ad5`
via `git show … | cmp`; `prompts` symlinked to `Backend/prompts`):

```sh
PYTHONPATH=work/baseline-backend:Backend /tmp/ellis-auth-venv/bin/python -m unittest Backend.test_account_independent_isolation -v
PYTHONPATH=work/send-only-backend:Backend /tmp/ellis-auth-venv/bin/python -m unittest Backend.test_account_independent_isolation -v
PYTHONPATH=Backend /tmp/ellis-auth-venv/bin/python -m unittest Backend.test_account_independent_isolation -v
```

Aggregate run by this checkpoint: 23 modules, **143 tests passed** in 8.7 s:

```sh
PYTHONPATH=Backend /tmp/ellis-auth-venv/bin/python -m unittest Backend.test_account_deletion Backend.test_account_deletion_finalization Backend.test_account_deletion_recovery Backend.test_account_erasure Backend.test_account_identity Backend.test_account_independent_isolation Backend.test_account_isolation_regression Backend.test_account_migration Backend.test_account_service Backend.test_account_sessions Backend.test_account_tokens Backend.test_admission Backend.test_ask Backend.test_companion_chat Backend.test_companion_context Backend.test_companion_prompt Backend.test_companion_runtime Backend.test_companion_service Backend.test_companion_snapshots Backend.test_hosted_relay Backend.test_proactive_socket Backend.test_provider_grants Backend.test_relay -q
```

Coordinator evidence, not rerun here: 19 synthetic modules, 124 tests passed
in 4.757 s; `git diff --check` clean. `git diff --check` was also clean here.

Checkpoint-tooling tests: in this agent's sandbox, 9 of 20 passed and 11 errored
at their fixture's `git init`; an unsandboxed rerun could not be started here.
The coordinator then ran them outside the sandbox on unchanged hashes:
**20 tests OK in 2.794 s** (coordinator evidence, not this agent's run):

```sh
PYTHONDONTWRITEBYTECODE=1 /tmp/ellis-auth-venv/bin/python -m unittest discover -s scripts/verification -p 'test_*.py' -q
```

Environment: macOS, Python 3.13, existing isolated auth venv. Tested SHA-256
(rechecked unchanged after the native runs):

```text
8149636571f62cc629b28ec483d24f152368532980ef360acd93f6872128596a  Backend/ask.py
21ff200f39ae6ac0a23a92ce67fb351d85408a868e2c6ec9a9cd56f540505ee3  Backend/relay.py
975d0714c2fa8ffe004e92d5ed78e061aeb8310fd81e8b8469469b1f12dcae88  Backend/test_account_independent_isolation.py
24a183c494458acf93272c52e9242e8a8434266909ff6903317bf983ed66e39e  UnitTests/AccountSessionTests.swift
```

## Native coverage — Mac synthetic contracts

`AccountSessionTests.testPreviousPersonsLateRefreshCannotReplaceOrClearNextPerson`
covers person A's late refresh success and failure after A is removed and B
signs in: B must stay current, and the only credential writes must be A's
removal and B's save. Production Swift is unchanged; this adds coverage of
existing generation guards and is expected to pass on the base too.

History: this agent's first native run failed with `No space left on device`
(about 0.5 GiB free) before any test ran. Two authorized removals followed,
both performed by the coordinator: first the previously approved task-local
`work/native-derived` build output (444 MB, about 424 MiB recovered); then,
under a separate later approval, only the exact generated Xcode DerivedData
cache (about 1.5 GiB recovered). No cleanup beyond these two removals was
performed.

The coordinator then ran both commands below on the hashes listed above
(coordinator evidence, not this agent's runs). Extracted suite lines, log
hashes and result summary: [native-summary.txt](native-summary.txt).

| Run | Suites | Result |
| --- | --- | --- |
| `work/native-retry.log` | AccountSession 10, AccountDeletion 9, RecordingNotesCache 11 | 30 tests, 0 failures, `TEST SUCCEEDED`; new late-refresh test passed |
| `work/native-contracts-final.log` | Above plus GoogleAccountGrant 1, FounderAccountMigration 6, RecordingLifecycle 10, Memory 8 | 55 reported, 54 passed, 1 skipped, 0 failures, `TEST SUCCEEDED` |

Both were run with the environment prefix shown; the log header does not
print environment variables.

```sh
TEST_RUNNER_VOICE_TEST_PYTHON=/tmp/ellis-auth-venv/bin/python xcodebuild -project VoiceCompanion.xcodeproj -scheme Mac -destination platform=macOS -derivedDataPath work/native-derived CODE_SIGNING_ALLOWED=NO -jobs 2 -only-testing:CoreTests/AccountSessionTests -only-testing:CoreTests/AccountDeletionTests -only-testing:CoreTests/RecordingNotesCacheTests test
TEST_RUNNER_VOICE_TEST_PYTHON=/tmp/ellis-auth-venv/bin/python xcodebuild -project VoiceCompanion.xcodeproj -scheme Mac -destination platform=macOS -derivedDataPath work/native-derived CODE_SIGNING_ALLOWED=NO -jobs 2 -only-testing:CoreTests/AccountSessionTests -only-testing:CoreTests/AccountDeletionTests -only-testing:CoreTests/RecordingNotesCacheTests -only-testing:CoreTests/GoogleAccountGrantTests -only-testing:CoreTests/FounderAccountMigrationTests -only-testing:CoreTests/RecordingLifecycleTests -only-testing:CoreTests/MemoryTests test
```

Result bundles (gitignored scratch, not committed):
`work/native-derived/Logs/Test/Test-Mac-2026.09.30_22-26-44--0400.xcresult`
and final `work/native-derived/Logs/Test/Test-Mac-2026.09.30_22-30-55--0400.xcresult`.
This agent read the final bundle with `xcrun xcresulttool get test-results
summary`: `Passed`, 55 total, 54 passed, 1 skipped, 0 failed, macOS 26.6.2.

The skipped test, `FounderAccountMigrationTests.testPrivatePhysicalSnapshotWhenExplicitlyProvided`,
requires a private physical snapshot and explicit rehearsal; neither is
supplied in synthetic scope.

This is Mac synthetic contract evidence only. It is not iPhone, TestFlight,
physical lifecycle, final provider configuration, independent-human acceptance,
deployed identity or Phase 1 acceptance evidence.

## Review and remaining gates

An independent fresh-context review found no defects in the boundary checks,
cleanup/reservation semantics or owner scoping; its suggested reservation
assertion was added. Accepted limitations:

- A revoked `/stt` client receives the existing generic ended message, not
  `unauthorized`.
- Per-frame authorization is an indexed SQLite read. Admission failure now
  ends a capture at the next frame instead of within one second (fails closed).
- Global one-active-request-per-category means the two people's same-category
  requests run sequentially in these fixtures.
- Previously noted and unchanged: an involuntary native sign-out does not clear
  the owner-keyed notes cache; a stale revoked proactive socket can delay the
  same owner's reconnect; memory writes and background jobs already dispatched
  before sign-out (not deletion) can finish.

A second fresh-context, read-only review of these final docs against the logs,
outputs and hashes found no wrong counts, commands, hashes, attribution or
scope claims; its one minor receipt-filter omission and three wording nits were
fixed.

Fictional fixtures do not satisfy the independent second-person, physical
lifecycle or final provider-revocation gates in the
[access map](../../features/maps/access.md). Remaining: an
exact commit with these hashes, required CI on that commit, PR review and
merge, deployment with fresh authorized identity evidence, iPhone/TestFlight
release acceptance, and those real-world gates. The deployed backend identity
recorded in the access map is unchanged by this checkpoint. Phase 1 remains
incomplete.
