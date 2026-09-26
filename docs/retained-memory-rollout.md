# Retained-memory internal rollout

Status: backend deployed and matching native builds installed/updated on September 26, 2026. The bounded physical-iPhone deletion, retained recall and reopen check has passed after the temporal-handling fix below. This is not a public release.

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

## Physical acceptance after temporal-handling fix

The founder approved one temporary recording and one Ask attempt and explicitly indicated readiness. The recording completed, but uncertain temporal verification discarded the supported Cedar fact. We paused deletion/Ask, diagnosed from cached outputs, fixed the writer in PR 83, and obtained deployment/recovery approval. See [the failure, fix and recovery evidence](uncertain-memory-time.md). The initial failure remains part of this checkpoint's record.

On the physical iPhone, the founder deleted only the Cedar test recording. Read-only backend verification confirmed its transcript payload was removed, one retained-recording row and the learned claim remained, and retrieval produced a valid retained-memory packet with unavailable original source and unresolved temporal status. The founder asked “where does project cedar meet?” once. The persisted completed answer is “From what I remember, Project Cedar meets at the garden pavilion. [[p1]]” with a retained-claim citation. The founder confirmed “Memory · recording deleted” appeared and that the answer and label remained after fully closing and reopening the app. Device rendering/reopen evidence is founder-observed; no new device screenshot was taken.

The bounded capture → learn/recover → delete → retained recall → reopen path passes. This is not a general memory-accuracy guarantee. The answer uses remembered-information wording but does not explicitly explain uncertain timing; the storage/context constraints were separately inspected, and this check does not establish how every temporal question will be phrased.

Both one-time attempts are consumed: recording 7/7, Ask 41/41 for the tested UTC day. Final global reservations are $4.586868/$5; profile reservations are $3.38/$3.45. Caps and the Render plan are unchanged. These are conservative reservations, not invoiced cost. No further test calls or permanent quota increases were made. Evidence: ignored `work/retention-rollout/cedar-deleted.json`, `cedar-final.json`, and `cedar-final-quota.json`, plus the founder's reports in this task.

Rollback: use the schema-16-compatible code and disable new retention if needed. Keep already retained knowledge and usage accounting; never restore an old database to undo a failure. See [implementation and provider evidence](retained-recording-memory.md) for retained-excerpt semantics, retrieval limitations and backup boundaries.
