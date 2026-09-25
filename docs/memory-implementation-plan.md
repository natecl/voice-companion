# Automatic cross-session memory — implementation plan

Status: planned, not implemented. Founder direction consolidated September 25, 2026. Follow the [product source of truth](product-source-of-truth.md) and [engineering principles](engineering-principles.md). The existing internal V1 remains the verified baseline. This plan does not deploy changes or start paid evaluations.

## Outcome and accepted boundaries

A conversation automatically informs useful answers in later conversations. The companion learns from completed listening sessions, handles corrections and temporary context in the background, and uses Jev to judge retrieved candidates before Luna answers. No memory suggestions, approval inbox, Forget button, or memory-management screen. Internal lifecycle operations remain observable to engineers. Source references in answers remain available; they are not a memory-management UI.

Build our own harness. Supermemory is inspiration only. Jev judges source support, attribution, modality, memory relationships and retrieval relevance; Luna extracts candidates and answers; code controls ownership, persistence, time and lifecycle transitions. This does not reopen the failed V1 Jev intent-routing experiment.

The first slice includes session-end learning, relevant cross-session answers during/after recording, automatic maintenance and source-linked answers on iPhone. Preserve shared Mac contracts and existing recording/current-session Ask behavior. Defer live incremental learning, public account enrollment, full cross-device session sync, old-library bulk import, voice identity recognition, proactive participation and a new UI design. Do not automatically ingest old private sessions during migration. No automatic deletion of source transcripts based on age or retrieval frequency.

## Baseline and implementation direction

Verified baseline: Swift/SwiftUI; local JSON sessions and Q&A; Python hosted relay with SQLite admission/usage ledger on a persistent disk; direct Luna Ask over a supplied snapshot. The current service does not persist transcript/answer payloads. Memory introduces explicit durable server content, not just a new prompt.

Relevant existing boundaries:

- `App/Sessions/SessionStore.swift` and `SessionController.swift`: local saving, finalization and deletion.
- `App/Sessions/ConversationAnswer.swift`: current answer snapshots and passage references.
- `Backend/ask.py`: current bounded question handling and Luna integration.
- `Backend/admission.py`, `service_policy.py`, `hosted.py`: credentials, usage budgets and single-instance lifecycle.

Proposed smallest storage: a separate versioned SQLite memory database on the existing persistent volume, leaving the usage ledger intact. Validate startup, transactions, backup/restore and bounded search locally in PR 1. Start with structured/entity and lexical candidate lookup; add an embedding adapter if the fixed paraphrase-recall cases need it. Choose/version any embedding model before paid evaluation. Do not assume Jev can retrieve records that candidate search missed. No new hosted database or graph service is required by this plan; if evidence requires one, resolve deployment/cost before proceeding.

Use focused modules for store/jobs, extraction/judgments, retrieval and context assembly within the existing backend. Keep provider adapters separate. Background work must not block the event loop serving recording and Ask. Retain local transcripts as the user's immediate saved result; upload a revision-aware copy for memory. The server owns derived memories and indexes.

Credential IDs currently identify enrollments. Add stable server-owned user IDs mapped to credentials so renewal does not create a different memory owner. Ownership is never accepted from an arbitrary client field or model output. This is internal provisioning, not a public login project.

## Shared data and lifecycle contract

Persist source session/revision/passage IDs, capture time and timezone, completeness, anonymous speaker labels, claim subject (possibly unknown), modality, evidence links, observation time, applicable time interval, processing/model/rubric versions and lifecycle state. Use namespaced source references: current `p1` is not globally unique. Distinguish statements in a conversation from verified real-world facts. Anonymous Speaker 1 never becomes the user or a cross-session identity by assumption.

| Internal transition | Trigger and effect | Historical recall |
| --- | --- | --- |
| Supersede | Supported correction changes a claim; old version ceases to be current | Old and new versions remain available with dates when relevant |
| Expire | Explicit time-bounded context passes its validity window | Event remains history; do not infer completed/cancelled merely because its date passed |
| Invalidate | Source revision/deletion removes support, or claim is unsupported | Exclude invalid claim; retained corrected evidence can explain a change |
| Prune/consolidate | Proven duplicate derived records merge with combined source links | Preserve supported information and evidence; defer subjective low-value deletion |

Jev can propose relationships and temporary status. Code checks IDs, ownership, temporal rules and commits transitions. Ambiguity remains separate/unknown, not a forced merge or task for the user. Stable preferences do not expire from inactivity. Conflicting speakers do not resolve by last-write-wins. Derive dates from capture timezone/context and retain unresolved dates rather than guessing; use code for comparisons.

Superseded/expired information must not reappear as current through raw-passage fallback. Attach lifecycle context to source retrieval and include current replacements where appropriate. Invalidated/deleted content is excluded. Automatic retirement is not erasure: do not hide valid historical evidence from a historical question.

Existing Delete session remains intact and gains cloud propagation; this is not a new Forget feature. It removes server source content and invalidates unsupported derivatives, index/profile/cache entries and outstanding jobs. Recompute memories with surviving independent support. Use deletion/version guards to prevent replay resurrection. Define derived answer snapshots referencing deleted sources: remove their copied source text and affected saved answers for this bounded slice, rather than leaving another hidden copy. Offline deletion queues are durable; do not claim server deletion before acknowledgment. Backup retention and deletion replay must be documented before deployment.

## PR 1 — persistent foundation and automatic lifecycle

**Deliver:** a working source/job/memory store and native synchronization boundary, with models disabled.

- Add schema migrations, stable owner mapping, evidence/version records, lifecycle operations and internal diagnostics. Keep migrations compatible with rollback or require memory feature disablement before reverting; never reset the spend ledger.
- After successful local save of a terminal recording, enqueue its transcript revision in a durable native outbox. Preserve incomplete-session status for interrupted recordings; exclude mutable interim text from durable claims. Save-first ordering means upload failure cannot lose the transcript.
- Authenticated upsert/delete handling is idempotent. Jobs keyed by owner/session/revision/extractor version survive process restart. Same revision with conflicting content is rejected. Duplicate deliveries do not duplicate jobs.
- Pending upload/delete survives app relaunch; drain on supported foreground/network opportunities. Do not promise iOS background execution while suspended. Server processing continues once upload is acknowledged. Deletion wins over stale upload/job delivery.
- Implement superseding, expiration, invalidation and duplicate consolidation using fixture judgments. Store internal reason codes and run maintenance with an injectable clock. Filter expired state at read time even if maintenance runs late.
- Provide bounded source lookup and rebuilding of derived indexes/profile. Version feature/API contracts so the installed V1 client remains usable while memory is disabled.

**Acceptance evidence:** actual local client/service persistence across restarts; duplicate/out-of-order delivery; credential renewal preserves owner; two synthetic owners cannot read or mutate each other's data; simulated clock advances retire temporary context without erasing history; source correction/deletion blocks stale worker commits. Inspect resulting store/job records. Test disk/write failure, revoked access and offline outbox behavior. No provider calls are necessary. Build affected native targets and inspect the actual simulated app path, without claiming real-device cloud acceptance.

## PR 2 — automatic learning and maintenance with Luna + Jev

**Deliver:** finalized sessions create and maintain supported memories without user action.

- Consume durable jobs; Luna extracts bounded candidate claims with existing source IDs. Exclude assistant answers from evidence of user facts or commitments. Empty/filler sessions complete with no memories.
- Find a small set of related existing records. Batch Jev questions for support, subject, modality, duplicate/update/conflict and temporary status. Pin model/rubric versions and give unknown/uncertain outcomes.
- Validate schemas and source existence in code, commit supported transitions, update compact profile and indexes. Profile only contains supported, attributed, broadly useful current information within a fixed budget.
- Apply the lifecycle contract automatically. No user-facing forgetting workflow. Ambiguous claims remain evidence and do not contaminate the user's profile.
- Record per-job state, input revision, usage and error reason without routinely logging transcript text. Bound concurrency and paid admission separately from Ask/STT. Check source validity again before commit.
- Preserve the no-automatic-paid-retry principle. Resume deterministic stages using cached results; uncertain provider completion becomes an explicit internal failure requiring deliberate, budgeted retry. Do not imply exactly-once external billing.

**Acceptance evidence:** local cached-response replay first, then a bounded real Luna/Jev run through the writer using synthetic saved transcripts. Inspect actual persisted claims/source links and updates. Include an unknown-speaker example, hypothetical/quoted speech, changed appointment, distinct similar names, duplicate input, incomplete recording, missing fields and provider failure. Restart/reprocess must not duplicate or restore invalidated claims. Simulated time verifies automatic expiration without waiting in real time.

Compare extraction alone versus extraction with Jev on a small held-out set to establish which errors Jev fixes or introduces. No broad model competition. A failed critical gate blocks enablement; document and fix it rather than silently removing the agreed Jev role.

## PR 3 — Jev-assisted recall and complete iPhone acceptance

**Deliver:** Ask incorporates useful past context with resolvable source references while recording remains independent.

- Form a bounded search query from the question and relevant current context. Search permitted memories and source passages; apply ownership/deletion and lifecycle constraints before Jev sees candidates. Distinguish current-state and historical queries and preserve temporal annotations for ambiguous questions.
- Jev assesses candidate relevance against the question/current conversation. Evaluate relevance separately from source support. Batch a bounded shortlist; no pre-search Jev gate that can silently prevent recall.
- Build a fixed context manifest with current snapshot/cutoff, selected past sources and memory versions, profile entries and timestamps. Avoid duplicated passages and preserve a deterministic token/byte budget. Never silently truncate required current-session context to make room for history.
- Extend the answer protocol, prompt and saved answer model compatibly. Resolve past-source references to the correct session/revision. Previously saved V1 answers must still load. Answer with a clear distinction between current conversation, remembered context and inference.
- On unavailable memory search or failed Jev retrieval, use the verified current-session path with an explicit past-context-unavailable notice. Do not say nothing was ever remembered. No duplicate Luna calls or interruption to capture.
- Revalidate source/deletion generation immediately before generation; cancel/reject in-flight results if their sources become invalid during the answer. Invalidate affected persisted snapshots/caches. Preserve Stop and Cancel independence.

**Acceptance evidence:** local replay verifies ranking, context manifests, citation UI, temporal questions, no-result/outage behavior, deletion races and saved-answer compatibility. A bounded real provider check proves Jev selection feeds the actual answer. After founder readiness, install the tested build and run actual microphone sessions: A states a fact, B asks about A without restating it, C corrects it, then Ask uses the correction. Inspect references and reopen the saved result. Retiring temporary context is verified with a controlled clock in fixtures; do not change the phone's system clock or claim fixture time proves real-world waiting. Preserve relevant Mac build/shared-core checks, without claiming untested device parity.

## Evaluation gates, efficiency and delivery

Before the first paid run, freeze a small development/held-out corpus and expected facts, subjects, relationships and questions. Cover ordinary recall, paraphrase, multi-session detail, updates, temporal history, unknown identity, quoted instructions, uncertainty and no evidence. Evaluate candidate recall before Jev filtering, retained relevant evidence after Jev, final answer support and cost/latency. Debug failures at their actual stage.

Critical scripted cases must have no cross-user access, invented source IDs, incorrect subject merges, stale facts presented as current, or deleted/invalidated content resurrection. Every designated end-to-end case must achieve its stated behavior; small passing samples are bounded evidence, not a general accuracy guarantee. Report counts and errors, not a single blended score. Establish numeric input/candidate caps, quality targets and timeout budgets before live measurement. Keep memory deadlines within the existing Ask timeout or make a separately justified protocol change; don't quietly lengthen it to hide slow retrieval.

Use saved transcript events and cached provider responses for iteration. Do not rerun audio transcription to debug storage, lifecycle, ranking or answer rendering. Real model integrations still need bounded live evidence; final microphone/iPhone claims need the real path. No provider tests in this planning PR.

At PR 1 start, record the exact local storage/auth contract and private-content retention/backup policy. Before hosted memory enablement, review the concrete deployment/migration and any cost change. Before PR 2 provider QA, obtain a bounded memory-testing allocation within or explicitly revising the existing ledger; the retired Jev allocation is not silently reactivated. Any founder-dependent access, spend or manual readiness blocker means stop and wait, per engineering principles.

Each checkpoint: branch from verified main → implement → run and inspect targeted behavior → record tested commit/input/results/limitations → open focused PR → review → merge only after its gates pass. PR 1 proves infrastructure, PR 2 proves automatic learning, PR 3 proves the complete product slice. Do not call partial infrastructure a working companion memory feature.

Final release evidence: **learn → recall → correct → recall correction → automatically retire temporary context → verify current versus historical retrieval**, plus deletion/invalid-source regressions and restart persistence. Update the runbook with actual retention, operation, spend and known limits. This remains an internal founder trial, not a public-launch declaration.
