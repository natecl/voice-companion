# Recording notes — internal rollout

Status: deployed and installed September 26, 2026 (September 27 UTC). Physical-iPhone acceptance is pending explicit founder readiness. This is not a public launch or a claim of complete notes acceptance.

The founder approved deployment of the verified notes checkpoint and up to $0.05 for at most two notes-generation calls inside the unchanged $5 global cap. The exhausted six-call generation QA allowance remains separate. No Render upgrade or permanent quota increase was authorized or performed.

## Delivered configuration

- Backend commit `19a2b41806b3d1ef75ff2e0ca4ff34e9a5a336a7`, PR 88.
- Render deployment `dep-das6h860tbcc73e1kseg`, live at `2026-09-27T00:52:48.26302Z`.
- Existing service `srv-daqtfs7lot8c73dleuug`, Starter plan, automatic deployments still off. The existing start command and flags are preserved with `VOICE_ENABLE_RECORDING_NOTES=1` added.
- Matching signed app installed as `ai.voicecompanion.phone` on the paired physical iPhone 16 Pro. Installation did not launch capture or begin manual QA.
- Mac/native shared-view evidence remains the local checkpoint in [the notes plan](recording-notes-plan.md); this rollout did not replace the running Mac app.

## Preservation and budget evidence

Consistent pre-migration backup: `/var/data/voice-companion/notes-approved-0gwtqq3j`, with SHA-256 manifest. There were zero active requests. The source database migrated schema 16 → 17. Every pre-existing table row in every backed-up database was preserved; integrity checks returned `ok`. The only allowed usage additions were the explicitly approved reservation and allocation marker. No old recordings were scheduled: `recording_notes` had zero rows after startup.

New subledger: `/var/data/voice-companion/notes-budget.sqlite`, approval `recording-notes-rollout-20260927-005`. It contains a $0.05 cap and a two-call maximum; each call reserves $0.025 without refunding uncertain attempts. The allocation is funded from unused STT-category headroom and marked as an allocation, so it does not count as a recording attempt. It is not permission to run additional STT or another model. Global reservations rose exactly $0.05, from $4.736868 to $4.786868 of $5. Notes attempts remain zero. These are conservative reservations, not invoice costs.

Post-deploy checks: `/health` ready; notes, memory learning and indexing idle without reported failures; runtime process has notes flag `1`; unauthenticated `/notes` WebSocket access returns 401 without invoking a model. Authenticated notes delivery through the physical app remains part of the pending end-to-end check. Existing daily limits have headroom for the intended single recording; no temporary grant was needed. Existing learning/Ask allocations remain unchanged.

Private local receipts are under ignored `work/notes-rollout/`: backup/provision, deploy metadata, verification, quota, auth guard, signed build and install logs. No new provider call or private transcript export was used for rollout verification.

## Pending physical check

After the founder explicitly says ready, open the updated app and make one short recording with a clear fact plus a tentative plan. Stop and wait for Notes, inspect the generated content, tap its supporting passage, then close/reopen the app and revisit the same notes. Use the same source for debugging and UI checks. A second generation call is available only if it provides necessary unresolved evidence; no automatic paid retry.

Record the founder-observed behavior together with notes state, revision, reservation and saved payload verification before declaring the slice complete. If access/permission or allowance blocks this check, stop and wait as required by the engineering principles.

## Recovery

Disable the notes flag to stop new scheduling/generation without changing transcripts or existing learned memory. Keep schema-17-compatible code for rollback or forward-fix; the old schema-16 binary rejects the migrated database. Do not restore old usage or source content as a shortcut. Preserve the backup and original failure evidence if recovery is needed.
