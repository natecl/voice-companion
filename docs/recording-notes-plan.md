# Transcript-derived notes — delivery plan

Founder approved implementation September 26, 2026. Notes and summary are one feature: a useful, source-grounded note beside the original transcript. Build after-recording notes first, then separately evaluate notes-based retrieval as a possible memory simplification. Existing memory and recording-deletion behavior remain unchanged until a verified replacement and explicit contract decision.

## Checkpoints

1. **Contract and storage:** title, sourced overview and flexible sourced sections; revision-bound pending/generating/ready/failed/outdated states; idempotency, interruption, empty/oversized input, stale completion and deletion guards. No provider or app exposure in this checkpoint.
2. **Generation:** bounded Luna adapter and structured output; source-only prompt, no history/memory; no forced business template. Preserve uncertainty, corrections and speaker ambiguity. Verify five short representative saved/synthetic transcripts (conversation, lecture, appointment, reflection, correction), including actual provider output inspection. No automatic paid retries.
3. **Integration:** enqueue after terminal evidence synchronization, independent of capture/chat; expose state and saved notes to native recording view; Notes / Transcript navigation, generated title and passage links. Failed generation leaves transcript usable; explicit retry remains admission/budget-controlled. No automatic historical backfill.
4. **Physical acceptance:** after readiness and rollout approval, one short iPhone recording → notes → transcript/reference navigation → close/reopen. Inspect usage and server state. Focused shared-view Mac verification. Prior fixtures cover failures without repeating STT.

Each checkpoint is independently reviewed, tested and merged through a focused PR. Live QA, rollout and device readiness remain distinct gates. No note editor, templates, live notes, voice replies, proactive participation, or memory redesign in this slice. Generated notes are derived views, never independent evidence for learning.

## Checkpoint 1 — verified foundation

`Backend/recording_notes.py` stores notes in the same transactional database as their source. Schema 17 adds one table without backfilling existing recordings. Source revisions clear the old payload and mark outdated; recording deletion removes notes even when learned-memory retention is enabled. Atomic completion checks revision, generation version, attempt and state. A late failed or successful attempt cannot overwrite a retry. Startup interruption recovery marks failed and does not automatically retry. These methods are not yet wired into hosted scheduling or a network endpoint.

A note has a title (120 characters), a sourced overview and up to six sections/36 bullets. Every overview/bullet references existing passage IDs; sections are flexible rather than mandatory meeting categories. Validation proves structure and reference existence, not factual entailment or useful model quality. Bounds: 48,000 UTF-8 input bytes and 20,000 output bytes. Oversized input fails explicitly, never truncates. Empty transcripts are ineligible. Terminal incomplete recordings can produce notes with a server-derived incomplete flag; personal-text inputs are excluded. The caller must enqueue only terminal recording uploads, matching the existing native outbox boundary.

Verification uses real SQLite storage, synthetic transcript and injected note data, with no model calls. Twelve new checks cover persistence/reopen, duplicate requests, revisions, deletion before/after completion, retry races, interrupted jobs, incomplete/empty/oversized sources, owner isolation, malformed output and schema-16 migration. All 92 targeted checks passed, including existing memory/retention/chat and schema-migration tests, run because the database/source invalidation boundary changed. Initial fixture failures exposed schema expectations and repeat migration setup; the final migration follows the existing idempotent schema pattern and updated tests assert version 17. Failed logs are retained in ignored work storage.

Behavior receipt `work/notes-foundation/behavior.json`: reopened notes are ready with the original passage reference, source revision makes the payload unavailable/outdated, and deletion leaves zero notes rows. This proves storage behavior only. Generation, native UI and hosted enablement remain pending. No paid run, production migration, existing note generation or app behavior changed.

Rollback/deployment: the previous binary rejects schema 17. Deploy only with explicit approval and a consistent backup; use compatible rollback or forward-fix rather than restoring old content/usage. No live service was migrated for this checkpoint.
