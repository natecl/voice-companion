# Recording notes — internal rollout

Status: deployed and installed September 26, 2026 (September 27 UTC). The bounded physical-iPhone acceptance check has passed. This completes the approved after-recording notes slice; it is not a public launch or a general summary-accuracy guarantee.

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

Post-deploy checks: `/health` ready; notes, memory learning and indexing idle without reported failures; runtime process has notes flag `1`; unauthenticated `/notes` WebSocket access returns 401 without invoking a model. Authenticated notes delivery through the physical app was subsequently verified in the check below. Existing daily limits have headroom for the intended single recording; no temporary grant was needed. Existing learning/Ask allocations remain unchanged.

Private local receipts are under ignored `work/notes-rollout/`: backup/provision, deploy metadata, verification, quota, auth guard, signed build and install logs. No new provider call or private transcript export was used for rollout verification.

## Physical acceptance — passed

The founder explicitly indicated readiness, recorded the short synthetic Project Willow statement on the physical iPhone, stopped, and reported that notes appeared. After the founder locked the phone for mirroring, the agent directly inspected the rendered app through iPhone Mirroring. The note title was “Project Willow Community Garden Meetup”; the overview correctly preserved the Saturday/community-garden fact and the uncertainty that bringing snacks was undecided. Passage 1 opened the exact original transcript, including “I might bring snacks, but I haven't decided yet,” at 0.9 seconds.

The app was then terminated and launched through the paired-device developer lifecycle commands. The agent reopened Recordings through mirroring, observed the generated library title, reopened the recording, and directly verified the same notes. Mirroring's app-switcher dismissal gesture had not closed the app; the explicit terminate/launch receipts establish the actual process restart. No new recording, retry, Ask or notes generation was requested during reopening.

Read-only backend evidence confirms source revision 1 completed, notes ready at the same revision, and valid passage references. Exactly one notes attempt completed with 567 input tokens and 50 output tokens, zero reasoning tokens, and a $0.025 conservative reservation. One of the two approved notes calls remains unused. The notes payload, source and attempt record were unchanged after reopening. Global reservations are $4.806868/$5 (including the new recording reservation); this is not invoiced cost. The earlier generation QA ledger remains exhausted and separate.

Receipts: ignored `work/notes-rollout/qa-receipt.json`, `qa-after-reopen.json`, `qa-terminate.json`, and `qa-relaunch.json`; direct mirroring observations are in the task tool history. This exercises physical microphone → real provider transcript → hosted Luna notes → native supporting passage → process restart → saved notes. The five-case generation screen and local failure/owner/revision/deletion tests remain complementary evidence; one phone recording does not establish accuracy for all conversations. Notes still require server connectivity to reopen. No additional model call is needed for this checkpoint.

## Recovery

Disable the notes flag to stop new scheduling/generation without changing transcripts or existing learned memory. Keep schema-17-compatible code for rollback or forward-fix; the old schema-16 binary rejects the migrated database. Do not restore old usage or source content as a shortcut. Preserve the backup and original failure evidence if recovery is needed.
