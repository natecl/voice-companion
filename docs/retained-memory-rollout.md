# Retained-memory internal rollout

Status: backend deployed and matching native builds installed/updated on September 26, 2026. Physical-iPhone acceptance is pending founder readiness and the two explicit test-attempt grants below. This is not a public release or a claim that the phone check has passed.

The founder approved this internal rollout after reviewing the live-provider QA. Render remains on Starter (512 MiB / 0.5 CPU, 1 GB disk), with automatic deployments off. No budget caps or permanent daily quotas were raised.

## Delivered configuration

- Commit: `ac8e1a1f7bbfabe4ef3b189f584870d0fcf942d6` (PR 81).
- Deployment: `dep-das451ojo6nc73a4qo10`, live September 26 at 22:10:15 UTC.
- Existing service: `srv-daqtfs7lot8c73dleuug`; `/health` returns ready.
- `VOICE_RETAIN_RECORDING_MEMORIES=1` is present in the running service process. Other flags and the existing start command are preserved.
- Signed iPhone build succeeded and installed as `ai.voicecompanion.phone` on the paired iPhone 16 Pro, iOS 26.5.2. No recording or device QA was started.
- The previously running Mac development app was stopped while no backend requests were active, rebuilt at its existing `VoiceCompanion-long-check` path and reopened. This is an update, not a new microphone QA claim.

## Migration and preservation

Before deployment, a consistent private backup of the runtime directory's top-level SQLite databases was created at `/var/data/voice-companion/retention-approved-qirgdqcl`. This includes canonical storage, usage and isolated QA ledgers; the backup has a hash manifest. There were no active requests during the snapshot.

The service migrated memory schema 15 → 16. Read-only comparison against the backup confirmed every pre-existing table row was preserved across all backed-up databases, and integrity checks returned `ok`. The new retained-recording table is empty until eligible recordings are deleted; there is no backfill or restoration of deleted content. Learning and indexing are idle with no reported failure. Global reserved usage is unchanged at $4.563868/$5; no new provider calls were made for deployment.

Local evidence: ignored `work/retention-rollout/` contains service/deploy metadata, signed build/install logs, backup receipt, row-preservation and process-flag checks, and quota inspection. These files do not contain provider secrets or private transcript exports.

## Remaining physical acceptance

Use one short fictional recording, wait until its learned memory is confirmed, delete that recording, ask once about the remembered fact, then reopen the app and inspect the saved answer and unavailable-recording label. The earlier real-provider checks and simulator screenshot remain valid; no broad transcription regression run is needed.

Preflight found recording quota 6/6 and Ask quota 40/40 for this UTC day. Do not ask the founder to begin a test that will immediately hit those limits. Await approval for one additional recording attempt and one additional Ask attempt, along with explicit readiness. The existing internal learning allocation has $0.17 remaining; category budgets also cover this short check. No new dollar allocation or permanent quota increase is proposed. Use unique, idempotent grant IDs, inspect effective availability before starting, and prohibit automatic paid retries.

If the day rolls over first, recheck actual quotas and skip unnecessary grants. Stop if access, device readiness, budget or required acceptance evidence becomes blocked. Do not mark physical acceptance complete until the observed result is recorded.

Rollback: use the schema-16-compatible code and disable new retention if needed. Keep already retained knowledge and usage accounting; never restore an old database to undo a failure. See [implementation and provider evidence](retained-recording-memory.md) for retained-excerpt semantics, retrieval limitations and backup boundaries.
