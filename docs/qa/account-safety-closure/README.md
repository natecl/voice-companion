# Account safety closure — bounded native mechanics

October 1, 2026. Base `bd71cc2d579232218209d8faf5e213a1a8d65b58`, containing merged PR183 and PR185. **Seven new native tests and ten existing account-session tests executed and passed** on the final strengthened test file, with zero failures/skips. The initial independent review's transient-save assertions and policy-description corrections are addressed; same-reviewer follow-up remains pending. Production source is unchanged. This is not full account, real-Google, physical-device or release acceptance.

## Execution and source boundary

Nathan superseded Cursor-only engineering with direct Codex execution in the existing controller. The parent reported dispatch arguments `model=gpt-6.1-sol`, `thinking=high`, turn `01a0f644-9bf8-73d6-983c-01bb1eab1221`. These establish **requested settings only**. Nathan subsequently observed Medium in the task pickers; effective runtime model/reasoning remains unverified. The parent withdrew its earlier High-confirmed statement and paused substantial implementation/builds for configuration investigation. No Cursor prompt was submitted for this lane.

Nathan later explicitly resumed the existing Codex lanes with the same requested model/effort; effective readback remained unavailable. Source/evidence preparation resumed, while the serialized native build slot remained with H1b. A scratch XcodeGen project reproduces the `CoreTests` macOS target's source directories (`UnitTests`, `App/Transcription`, `App/Sessions`, `App/Audio`), Swift 6 and macOS 15 deployment target, with signing disabled. It excludes application/UI targets and package dependencies. All source references point to this worktree; generated artifacts stay outside it. This permits discovering the new test file without modifying tracked project, plist or entitlement files. Project generation is not a native compilation or executed test.

Only `UnitTests/GoogleNativeFailureRecoveryTests.swift` and this QA directory are authorized writes. H1b-owned relay/hosted/schema/erasure/native capture, other worktrees and the Phase0 drafts are preserved. The parent subsequently granted the serialized local Mac build slot; the focused run completed and the slot was released after checking no competing compilers remained. Simulator/UI/device execution and independent review remain pending coordinator scheduling. No live grant, credential, account content, provider call, app launch/install, deployment, deletion or restore activation was used here.

The actual checkout root and root `AGENTS.md` were read; `rg --files --hidden -g AGENTS.md -g '!**/.git/**' .` found no nested guidance. Referenced README, product source, V0 scope, engineering principles, feature index/access map/verifier and current delivery guidance were consulted. The engineering requirements are applied through actual CLI/state observations, executed native manager/storage failure paths, source hashes and raw results, targeted neighboring checks, and explicit synthetic/live/physical boundaries. Reviewers must read the same checkout guidance and inspect final source/evidence before reporting approval; receipt of an instruction alone is not proof of compliance.

## New test claims

The tests call the actual `AccountSessionManager` with a fake `AccountRefreshing` actor. All accounts are explicitly Google, with fictional grants. Save/clear callbacks persist JSON under a unique temporary directory; this is **injected file persistence, not Keychain**. An actual `SessionStore` saves/reopens one fictional owner-scoped transcript and verifies its exact bytes.

| Case | Required observation |
| --- | --- |
| Network timeout | Original typed timeout propagates; account persistence clears; subsequent calls and a new manager stay signed out; no automatic rotation retry; explicit same-owner synthetic login restores persistence and original transcript. |
| Rejected app session | `signInRequired` propagates with the same clear/restart/no-retry/content guarantees. This is an injected app authorization error, not external Google consent removal. |
| Other-owner response | Rejected as `invalidResponse` before saving/exposing that account. |
| Expired response | Rejected as `invalidResponse` before saving/exposing stale access. |
| Rotation save failure | Successful synthetic rotation followed by persistence failure drops access and clears persistence without repeating the consumed secret. |
| Clear failure | Access drops in the current manager; clear is attempted once, but the old persistent secret remains. After persistence becomes writable, explicit clear and synthetic same-owner recovery succeed. No durable sign-out or locked-device restart guarantee is claimed. |
| Exact family deadline | Local account clears at the exclusive boundary; transport is never called; explicit synthetic recovery preserves the recording. |

“Recovery” here supplies a new fictional session via `install`; it does not exercise the Google SDK, OAuth, `AccountRuntime`, sign-in UI or real device Keychain. New-manager restart is object reconstruction from injected persistence, not app termination/relaunch. These distinctions prevent mechanical coverage from being mistaken for the remaining live native acceptance.

## Executed operational evidence

### Focused native execution

On macOS 26.6.2 (25G83), arm64, Xcode 27.0 (27A266a), the actual scratch `CoreTests` target executed all seven `GoogleNativeFailureRecoveryTests` and all ten `AccountSessionTests`: **17 passed, 0 failed, 0 skipped**. Both classes and individual new cases were present in the raw XCTest output; `xcresulttool get test-results summary` independently reported `Passed`, total 17 and no runtime warnings. The build emitted one AppIntents metadata-extraction warning because the test target has no AppIntents dependency; it did not fail compilation or tests. No fixture assertions or production code were changed to obtain this result.

- [Exact command and hashes](native-command.txt)
- [Raw XCTest output excerpt](native-tests.txt)
- [Sanitized result-bundle summary](native-summary.json)
- [Scratch XcodeGen specification](scratch-project.json)
- Full final raw log retained outside git: `/tmp/account-safety-native-focused-2.log`
- Final result bundle retained outside git: `/private/tmp/account-safety-native-project-p36i_p31/focused-2.xcresult`
- Initial receipts preserved unchanged under [superseded/](superseded/); initial raw log and `focused-1.xcresult` also remain outside git. They establish the initial test file only.

The initial test source hash was `c7123babb8b9a6c9274b3da25977b47345035b9dd246a3cbf522cfaa45179667`. After reviewer-driven save-attempt assertions, the final test hash `c8c4c58d4164ff57559f5029ba05097fc7bb94a7fe6b934f41a769fbbc70516e` remained unchanged before/after the successful focused rerun. The unchanged manager hash was `7c88f0b788c3890520b13725083eeaece66feaef3fafcea016ad1c4ac57d7717`. Tracked `git diff --exit-code` remained clean. Actual file writes/reopens/content-byte comparisons passed; no Keychain or application UI was exercised. Failed-clear persistence is explicitly characterized as retaining the old secret, not waived or converted into a durable-sign-out claim.

### Quarantined restore and read-only inventory

The controller ran the existing disposable restore CLI rehearsal on the base implementation before authoring these tests. [Raw receipt](restore-rehearsal.json) records actual `prepare` and `validate` subprocess results: one deletion replayed; erased rows absent; unrelated content preserved; latest usage byte-identical; original input hashes unchanged; stale access/refresh/owner-rebinding denied; private quarantine validated. A post-snapshot source deletion was refused with no manifest. `activation_supported=false`; no restore activation or private database was involved.

Command, from this source tree (the completed Google worktree had identical relevant source):

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=Backend /tmp/ellis-auth-venv/bin/python docs/qa/backup-restore/rehearse.py
```

The source hashes in the raw receipt bind the implementation exercised. Temporary fixture inputs were removed by the existing harness's own cleanup; no previous worktree or backup was removed.

[Operational inventory](operational-inventory.json) is a sanitized controller transcription of read-only Render/SSH/device observations around 06:45–06:50 UTC; it is not a fresh runtime claim at a later date. It records live commit `482394e23dd081cc4a9a1e67ef79f7f4aa3b676e`, healthy liveness, automatic deployment off, and absent managed-backup implementation/configuration. PR183/185 and backup tooling are merged but absent from that runtime. `ready` proves liveness only.

Hosted inventory counted 24 top-level SQLite files and 488 nested database/archive files, totaling 43,241,472 bytes. The 187/82/219 directory-name categories are heuristics, not verified content ownership or a deletion list. No database contents or tokens were inspected. No managed-backup root/status was present; no retention/scan setting was configured. No `crontab` binary was available; that does not prove absence of every external scheduler. Off-host copies and provider snapshots were not inventoried.

Read-only connected-phone app metadata showed `ai.voicecompanion.phone`, developer-built version `0.1.0`, build `1`. Those reused values cannot establish exact source/binary identity. No phone app was opened or its data accessed. A default-sandbox CoreDevice timeout was preserved as a tooling failure; elevated read-only enumeration succeeded. SSH emitted a host-key-update signature warning while its existing pinned connection succeeded; strict host checking was retained.

## Existing acceptance credited

Do not repeat completed founder migration, Google/Apple happy-path enrollment/refresh/switching, populated deletion/re-enrollment, simulator fresh-proof recovery, Apple native network/rejection recovery, physical capture/sign-out or Nathan's credited delete/relaunch observations. Their original receipts and environments remain authoritative for their bounded claims. Nathan's later recollection of physical delete/relaunch is credited as reported behavior with exact build/date uncertain; it does not establish interrupted/failed deletion recovery.

PR183's revoked `/ask`/`stt` checks and PR185's negative-refresh/final-revocation synthetic checks are already merged and reviewed. This lane does not manufacture a new production fix or rerun their entire suites.

## Remaining specific gates

- Real Google native app-session failure/network recovery through normal UI and persistence remains distinct from the injected manager tests. External consent removal is not polled by the current implementation.
- Two independent real people with populated content need actual cross-owner visibility/stale-response inspection; fictional people and Nathan's two provider identities are different evidence.
- Physical pending/failed deletion must resume after interruption/relaunch, preserve unrelated-owner content and finish cleanup. It needs separate readiness and specific destructive-action authorization.
- Select operational retention/schedule/copy policy and review a matching deployment; independently preserve current deletion/revocation/spending authority before any recovery. Current quarantine tooling cannot activate a restore.
- Decide external-consent semantics and final Google grant binding; [concrete unselected options](policy-options.md) describe the boundaries. No policy is changed by tests passing.
- Final backend/native delivery identities and release configuration must be paired before claiming merged fixes live. Reused version numbers are insufficient.

The assigned independent reviewer (`01a0f667-f102-76d6-beae-7a3ce82680f3`) read the applicable guidance and verified initial source/evidence read-only. It found no P0/P1 issue but required two P2 corrections: detect forbidden transient saves before cleanup, and accurately describe rejected Google authorization-code requests. A P3 noted RISC excludes Workspace users. Save attempts now remain observable after cleanup, zero attempts are required before synthetic recovery for rejected/foreign/expired responses, Google protocol wording is corrected and Workspace coverage is explicit. The reviewer did not execute builds or edit files. Its requested model/effort is parent-controlled; effective readback is unavailable. The focused final rerun passed all 17 tests; same-reviewer follow-up is pending before this slice can be called approved. No PR/commit/merge or full-feature acceptance is claimed here.
