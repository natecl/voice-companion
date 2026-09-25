# Memory foundation operating contract and evidence

September 25, 2026. Checkpoint 1 of the [memory plan](memory-implementation-plan.md). This is a local, provider-free foundation, not working AI extraction/recall or a deployed phone memory feature. The installed hosted configuration remains memory-disabled.

## Concrete storage and ownership contract

The Python service may open a separate `memory.sqlite` beneath `VOICE_DATA_DIR` only with `VOICE_ENABLE_MEMORY=1`. The usage ledger is unchanged. The app enrolls in synchronization only when its internal relay credential configuration contains `memoryOwnerID`. Neither switch is enabled by this checkpoint on the hosted service or founder phone.

Stable owner IDs are stored separately from renewable credential IDs. Existing V1 enrollment remains unchanged. For an explicitly enabled internal memory client, the administrative enrollment command accepts `--memory`; renew using `--memory --memory-owner <existing owner>` to retain ownership. The export contains the owner ID and existing-style server credential, never a provider key. Server authorization derives the owner and compares it with the client's expected owner before mutation, preventing a credential switch from silently uploading one owner's queued data to another account. No public enrollment or client-selected ownership exists.

`/memory` is an authenticated WebSocket accepting one version-1 upsert or delete per connection. It returns an acknowledgment only after commit. Upsert carries session ID, monotonic revision, capture timestamp/timezone, completeness and finalized passages with local IDs, times, text and anonymous speaker labels. Identical replay succeeds without another job; same revision/different content is rejected; older revision is reported stale. Deletion creates a permanent session-ID tombstone even if upload has not arrived. No client endpoint can create claims, bind credentials or run the internal writer.

The app saves locally first. Tracked session markers allow relaunch to recover a missed outbox write. Legacy sessions and sample replays are not automatically imported. The outbox persists revisions and pending acknowledgments; a late acknowledgment cannot erase a newer revision/deletion. It retries idempotent synchronization on finalization, foreground and restored network availability, with no immediate failure retry loop. It processes at most 32 pending entries per trigger. No assertion of iOS execution while suspended is made. If backlog remains, a later trigger continues it. Incomplete captures retain their status; interim segments remain local and are excluded from durable evidence. Source completeness is false when any interim segment was excluded.

Server source/job operations run off the audio/Ask event loop. Two synchronization operations may be in flight, with an eight-second service deadline and ten-second native deadline. Input is bounded to 63 KB for the envelope and 60 KB canonical source data, 200 passages and 1,000 live sessions per owner. Oversize input is explicitly rejected, never silently truncated. Claim storage is bounded to 5,000 records per owner; returned candidates are bounded to 50. These are internal foundation limits, not a public retention promise.

## Internal lifecycle and failure semantics

Model-free fixture judgments exercise source support links, duplicate consolidation, superseding, expiry, and invalidation. Unknown-subject claims cannot be merged across sessions. A superseding update requires explicit ordered validity times; uncertain ordering remains unresolved rather than using ingestion time as truth. Expiration is enforced at commit, startup maintenance and read time, so a late maintenance pass cannot make an expired claim current. Historical search retains superseded/expired records with their validity metadata. Evidence lookup includes lifecycle annotations for later context assembly.

The compact profile is computed from supported current stated user preferences. There is no independent profile/vector cache in this checkpoint; lexical candidates and the profile are rebuilt from authoritative records. No AI has verified fixture claims, and no semantic-retrieval quality is claimed yet.

Source correction/deletion removes that source's support. Claims with independent surviving support remain; unsupported claim text/subject are scrubbed and invalidated. Jobs for old revisions become obsolete and stale leases cannot commit. Interrupted running jobs become `interrupted` on service restart, not silently requeued: a future provider call may already have incurred spend. Queued work survives restart. No model worker consumes jobs yet.

The existing Delete session action queues cloud deletion before removing local content. An acknowledged deletion replaces the outbox's source copy with an identifier-only tombstone. Relaunch finishes a local deletion interrupted after the tombstone was saved. Offline cloud deletion is pending, not complete. There are no cross-session answer copies in the current product; their deletion cascade remains a mandatory PR 3 acceptance gate before they are introduced.

Failures never clear local transcripts or relax ownership. Disk/transaction failure rolls back; write failures leave pending work inspectable. Model-related uncertainty is not retried automatically. A future-schema database is refused rather than reset. Source content, questions and credentials are absent from routine diagnostics; state counts and IDs support engineering inspection. No Forget button, suggestion inbox or memory-management UI is added.

## Retention, backup and rollout

Local sessions keep the existing retention behavior. In a memory-enabled service, sources remain until session deletion; age/low retrieval frequency alone does not erase them. Derivative retirement retains useful history, while unsupported text is scrubbed. Tombstones and content-free invalidation/job records remain to reject stale writes. A stopped session need not produce a personal memory; attribution remains a separate judgment.

Files use restrictive permissions and SQLite secure-delete for removed database content. This is not a promise of cryptographic erasure of underlying disk blocks, provider retention or platform snapshots. The foundation provides an explicit exclusive-destination SQLite backup operation and a verified local restore. It does not schedule cloud backups. Before hosted enablement, document actual platform backup retention and deletion reconciliation; never restore a pre-deletion backup into live service without current tombstones and invalidations, or resurrected content could be exposed. This remains a deployment gate, not a claim already verified by local backup testing.

Rollback: disable memory on the service and in new client provisioning before reverting a memory-schema change. Do not remove `memory.sqlite`, owner mappings or the usage ledger to make old code start. Existing V1/STT/Ask behavior remains available with the memory feature off. This checkpoint does not change Render configuration, quotas, provider budgets, recording duration or the installed iPhone build.

## Targeted verification

Local evidence, ignored by Git:

- `work/memory-backend-regression.log`: all 36 then-current backend tests passed, including existing authentication, admission, relay and Ask fixtures. No external provider requests.
- `work/memory-backend-final.log`: focused final lifecycle/unknown-subject and admin-renewal checks. Includes SQLite write-lock failure, atomic rollback, backup/reopen, source correction, temporal state, multi-source support, deletion-before-upload, stale leases and owner isolation.
- `work/memory-native-regression.log`: 44 native core checks passed, one opt-in long test skipped; existing Live Ask UI check passed. The first memory UI attempt failed because the test runner lacked a loopback-server entitlement. The entitlement was added to the test runner only; app permissions were not changed.
- `work/memory-final-core.log`: final focused native memory and recording-lifecycle checks passed, including a regression ensuring failed recording setup cannot rewrite a previously saved session/memory source.
- `work/memory-native-tests.log`: actual Swift controller/store → URLSession WebSocket → local Python memory service → SQLite; service restart, saved reopening and cloud deletion verified with synthetic transcript events. Local transcript retained both final and interim text; server received only final text. Provider usage stayed empty.
- `work/memory-ui-focused.log`: corrected runner exercised save/upload/relaunch; deletion selector was ambiguous with the macOS Touch Bar. It was changed to the existing confirmation identifier. Failed evidence is retained.
- `work/memory-ui-final.log`: final targeted UI run passed; saved transcript inspection, reopen and deletion synchronization. Screenshot attachments remain local because they include desktop surroundings.
- `work/memory-simulator-build.log`: shared iPhone simulator target build; this is not physical-device memory QA.

Fixtures use generated owner IDs and synthetic text, isolated from real sessions/credentials. The UI fixture fails closed if configuration is missing. `MacUITests.entitlements` permits the test runner's synthetic local server; it does not disable the sandbox or change either production app's entitlements.

Reproduction:

```sh
python3 -m unittest discover -s Backend -p 'test_memory.py' -v
python3 -m unittest discover -s Backend -p 'test_admin.py' -v
xcodegen generate
TEST_RUNNER_VOICE_TEST_PYTHON="$(command -v python3)" xcodebuild \
  -project VoiceCompanion.xcodeproj -scheme Mac -destination platform=macOS \
  -derivedDataPath "$HOME/Library/Developer/Xcode/DerivedData/VoiceCompanion-mac" \
  CODE_SIGN_IDENTITY=- -only-testing:CoreTests/MemoryTests \
  -only-testing:MacUITests/MemoryUITests test
```

Use an interpreter with `Backend/requirements.txt` installed. No microphone or provider key is required. The checkpoint PR records the tested commit and final result. PR 2 must separately prove real Luna/Jev extraction and automatic updates; PR 3 must prove actual cross-session answers on iPhone. No launch-readiness claim follows from this foundation.
