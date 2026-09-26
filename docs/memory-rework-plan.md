# Companion memory rework — implementation plan

Status: implementation authorized by the founder. Checkpoint 0 baseline evidence is recorded in [memory-rework-baseline.md](memory-rework-baseline.md); checkpoint 1 is split into the bounded storage change below and the remaining identity foundation. Storage, chunk-boundary and extraction/judgment foundations have since merged through PR 40. The bounded atomic writer within 3C is described in [memory-atomic-writer.md](memory-atomic-writer.md); long-source chunk integration is now verified in [memory-chunk-writer.md](memory-chunk-writer.md); later product checkpoints remain pending. Hosted rollout still requires approval of the concrete deployment. Follow [engineering principles](engineering-principles.md). This replaces the remaining personal-profile plan as the delivery direction; its completed work and failed QA remain part of the evidence.

## Product outcome

> Granola with an AI that listens alongside you and can join the conversation.

Initial ICP: a curious, ambitious, AI-comfortable person who thinks out loud, already turns to AI for help, and wants useful perspective without repeatedly explaining their life. The founder, Mark Pincus and Garry Tan are reference personas, not a job-title restriction. Understand family, relationships, interests, goals, studies, work and appointments. The feeling is an attentive friend with personal intelligence on tap, not a filing cabinet of notes.

Two primary actions: **Capture meeting note** and **Talk to companion**. Voice notes and meeting recordings are one capture type. An ongoing companion chat works across recordings, with or without an active capture. Chat stays available while capture continues. The latest transcript is immediate context; durable learning happens in the background. The UI does not expose an additional personal-note workflow, memory approval inbox or forgetting screen. Sources stay inspectable and recordings remain deletable.

Scope: shared Swift/SwiftUI app and Python/SQLite service; iPhone leads physical acceptance and shared Mac functionality remains working. Keep Luna for extraction and responses, Jev for bounded independent judgments. Preserve the verified storage/sync foundation. No Supermemory integration, mandatory graph database, autonomous external actions, unsolicited interruptions, silent always-on recording, voice enrollment, or full visual redesign. Typed ongoing chat is the first interaction implementation; speech-to-speech companion conversation/TTS is a separate slice, not silently included by the label “Talk.”

For the entire memory harness, use the [Jev article](https://x.com/dhravyashah/status/2103314339239428201) as the agreed design baseline: background learning, contextual chunks, bounded harness decisions and relevance ranking; preserve meaning rather than aggressively discarding sentences. Its reported findings guide role selection. Acceptance still requires evidence from this implementation; the article does not establish our entity matching or thresholds.

## Revised interaction and source model

Founder-approved refinement: one persistent **main companion chat** is the default. Returning to the app or starting a recording does not create a new conversation. Give messages an owner-scoped conversation ID now; optional side conversations are a later slice. They will have separate local discussion histories and access to the same relevant personal memory. Separate does not mean private or memory-free, and their messages must not be indiscriminately injected into the main chat.

Keep the existing **recording library** alongside chat. Each capture is one durable item with its title/date, available duration, transcript and stable source references. Future generated summaries and user notes belong to that same item, not a separate source silo. For this rework, retain transcript browsing and deletion; do not build summary generation, a notes editor or library search as incidental scope.

“Ask about this” opens the main chat with the selected recording visibly attached. The user can clear or replace that attachment. Attachment selects relevant evidence; it does not silently exclude all other permitted memory or assert that every passage fits the model context. Source citations open the same recording detail at the referenced passage. Deleted/unavailable sources must have an explicit state rather than a broken or misleading link.

Capture remains accessible from chat and the library. Switching views preserves the draft, reading position and conversation, and does not interrupt recording or answer generation. An active recording has a visible status and stop control across both surfaces. The Manus pill toggle is a navigation reference only: Companion / Workspace are working labels, not a required visual redesign or final naming decision.

Keep three distinct layers: **transcript evidence**, **derived summaries/notes**, and **cross-recording memory**. A generated summary cannot independently support facts or overwrite the transcript. Future user-authored note edits need explicit provenance and correction semantics in their own slice; they must not silently mutate original evidence.

## Non-negotiable contracts

- A transcript statement, the person it concerns, and whether it applies now are separate concepts. Source support is not proof of current truth or identity.
- The recording owner is not necessarily its speaker. Until voice recognition, first-person speech remains attributed to an unresolved speaker unless independent evidence establishes identity. Do not assume one diarization label means the user.
- Speaker identity and identity of people mentioned are separate. A name/relationship is evidence, not a unique person key. Preserve “other,” “former,” and similar distinguishing qualifiers.
- Unresolved correction/conflict is a persisted internal state with evidence and candidate links, not another authoritative current profile fact. It can be retrieved as qualified evidence when useful.
- Explicit conversational clarification may establish a link, with the user message and source reference recorded as evidence. Do not build a required manual identity-setup flow. Ordinary questions, hypotheticals and assistant answers do not silently become user biography.
- Current chat turns provide conversational continuity. Captures provide durable life context. Assistant-generated answers or summaries never become independent evidence for durable facts.
- Ownership, deletion, source revisions, entity-link evidence and lifecycle checks are enforced in code. Models propose; transactions validate and apply.
- Identity/link uncertainty must remain recoverable. Do not merge identities because a model is confident, then discard the evidence needed to reverse the link.
- No aggressive pre-extraction sentence deletion. Retain originals; learn and retrieve with source/time/speaker context intact.

## Delivery sequence

Each checkpoint produces a focused PR with a bounded behavior, real-path QA, review, and merge after its gate passes. These are logical checkpoint names, not reserved GitHub PR numbers. Split a checkpoint further if it stops being independently reviewable.

### Checkpoint 0 — recovery baseline and frozen acceptance cases

**Outcome:** preserve the current working capture/chat path and make the known failures reproducible before changing architecture.

- Record main (`060fd85` at planning), deployed implementation (`85e72cd`), draft PR 31 and schema 3. Refresh these values before execution. Do not merge PR 31 to clear the backlog: its physical correction gate failed.
- Start new implementation branches from verified main. Explicitly isolate and revalidate any required support code from PR 31; name dependencies rather than treating the deployed draft as a verified foundation. Preserve PR 31 until replacement PRs cover its useful changes; then mark it superseded, not retrospectively passed.
- Convert audit probes and saved synthetic provider responses into reproducible checked-in fixtures. Preserve failed variants without deploying them.
- Freeze development and held-out cases before model changes: same-name people; different relationships; unnamed relatives; “other daughter”; valid corrections without special wording; additional interests; historical changes; quoted/hypothetical speech; first-person unknown speakers; current conflicts; old paraphrased facts; source deletion; oversized sources; relative dates.
- Define explicit expected entity links, claim states, source references and answer behavior per case. Label staged fixture results separately from provider/device evidence.

**Gate:** reproduce the failed Maya transition and audit failures without inference; capture baseline behavior and proposed pass criteria. No provider calls, migration or deployment.

### Checkpoint 1 — structured identity, uncertainty and transactional lifecycle

Delivery split: **1A** persists unresolved lifecycle proposals and prevents the known new-fact fallback; see [implementation and evidence](memory-uncertainty.md). **1B** delivers structured entities/mentions and evidence-backed identity links; see [implementation and evidence](memory-identity.md). **1C** adds the evidence-dependent correction storage path and reopening gates; see [implementation and evidence](memory-identity-transitions.md). Legacy model decisions are not retroactively verified; adoption of this path and deduplication judgments remains part of checkpoint 3 integration. The identity ledger is not treated as active model-driven resolution before those integration gates pass. Completing 1A does not establish correction-model quality or completion of checkpoint 1.

**Outcome:** stored memory can represent the world without forcing ambiguous evidence into a current fact.

- Add the smallest necessary owner-scoped structures for entities, source mentions, evidence-backed mention/entity links, claims, and proposed correction/conflict links. Stay in SQLite. Record provenance and schema/version information.
- A mention preserves name, relationship, qualifiers and speaker attribution. Established entities have stable IDs; unresolved mentions need not be linked. Do not unify people solely by normalized names or session-local hashes.
- Keep claim support, identity resolution and temporal/lifecycle state separate. Represent supported-but-unresolved claims and corrections explicitly. A conflict must not silently default to current/new.
- Apply supported supersession and duplicate consolidation transactionally; retain history and multiple supports. Deleting identity evidence must invalidate or reopen dependent links/claims as appropriate, not leave unsupported derived identity behind.
- Define current, historical and unresolved read contracts. Handle true new facts separately from possible replacements. Reconsider unresolved links only after relevant new evidence or an explicit versioned review—not on every Ask.
- Additive migration first: preserve original sources, existing history, tombstones, budgets and unknown identities. Mark legacy name hashes as legacy/unverified rather than declaring them established identities. No automatic paid backfill.

**Gate:** temporary SQLite execution proves same-name separation, unknown identity retention, uncertainty preservation, valid correction, rejected false correction, duplicate support, atomic rollback, source revision/deletion races, restart, migration and owner isolation. Use fixture judgments here; do not claim model-quality acceptance.

### Checkpoint 2 — resilient background learning and contextual chunks

Delivery split: **2A** isolates known job-local failures and exposes learner state; see [implementation and evidence](memory-worker-isolation.md). **2B** implements the off-by-default deterministic chunk pipeline, bounded verification batches, exact deduplication and reviewed recovery; see [implementation and evidence](memory-chunks.md). **2C** implements optional Jev semantic boundaries and passes the bounded live provider gate; see [evidence](memory-semantic-boundaries.md). Hosted enablement remains pending approved rollout. Deterministic/local fixture success does not complete the provider-quality gate. Oversized sources remain failed after 2A; do not claim chunk learning or trigger automatic paid reprocessing.

**Outcome:** every accepted source has a bounded processing path, and one bad job cannot stop the rest.

- Align source admission, serialization overhead and model input limits. Preserve local capture if cloud processing is unavailable. Never silently truncate a source.
- Introduce source-versioned chunk jobs with stable passage/time ranges, bounded overlap and deduplication. Keep coherent neighboring turns and speaker context. Partition safely before a boundary model call when the full source is too large.
- Jev assesses continuation/boundary choices near a target size. Application code enforces hard limits. On unavailable boundary judgment, use a clearly recorded conservative overlapping-turn fallback; do not drop sentences or spin on paid retries.
- Chunk/model/version cache keys prevent duplicate paid processing. Late results cannot revive deleted or revised sources. Learning runs after finalization in this slice; live partial text is available to chat without being committed as durable memory.
- Classify failures: quarantine source-specific malformed/oversized jobs and continue independent jobs; halt paid work for global budget/authentication failures. Use reviewed bounded recovery for failed paid jobs.
- Add content-free readiness, backlog, stalled-job and stage-cost diagnostics. Distinguish saved, synchronized and learned internally; keep user-facing wording simple and truthful.

**Gate:** execute source → chunks → worker → store with saved model responses. A bad job followed by a valid job must leave the valid one learned. Cover boundary context, duplicate delivery, restart and deletion during processing. A small real Jev boundary check verifies this new integration before enabling it; no STT run is needed.

### Checkpoint 3 — Luna extraction and independent Jev judgments over the new contracts

**Outcome:** natural captured statements yield supported memories and reliable state transitions.

- Version Luna's structured output to preserve mentions, explicit relationship qualifiers, modality, source spans, possible changes and temporal expressions. Do not turn an attributed relationship into an account-owner fact.
- Retrieve possible entities and prior facts by evidence and relevance before limiting results; remove the “latest 50 profile claims only” dependency. Expose explicit absence/ambiguity, not a deceptively complete candidate list.
- Give Jev atomic, evidence-specific questions for support, attribution and semantic replacement. The founder-approved bounded writer uses a separate Luna low-reasoning identity resolver after comparative QA; see [evidence and limits](memory-atomic-writer.md). Include original source evidence and prior supporting evidence needed to decide. Batch independent questions; do not ask one question to infer another question's output in the same request.
- Define separate acceptance policies for support, identity writes, lifecycle writes and ranking. Preserve distributions/reasons in diagnostics. Confidence is not a second independent verification; empirical error costs determine thresholds.
- Apply accepted proposals through checkpoint 1 rules. An uncertain/unsupported link cannot overwrite an established entity. Do not substitute Luna verifying itself or lower a threshold to fit Maya.
- Cap re-evaluation per new evidence event and stop futile repeated judgments. Maintain independence between extraction and verification.

**Gate:** full writer execution first with cached responses, then a frozen live development/held-out subset within the approved allowance. Designated positives must create the expected facts and corrections; critical negatives must produce no unsupported entity merge, false user attribution or false supersession. Inspect stored results and history. A failed negative blocks this checkpoint; do not label it a passing “limitation.”

Delivery split: **3A** validates versioned evidence extraction and exact source spans with recorded live responses; **3B** supplies evidence-aware candidate lookup and independent atomic Jev judgments; **3C** adopts those decisions through the identity/correction ledger in the writer and runs the full positive/negative gate. Extraction proposals alone never authorize identity or lifecycle writes. The bounded atomic writer and its long-source chunk integration are verified backend checkpoints; [memory-chunk-writer.md](memory-chunk-writer.md) records the source-attribution role comparison, exact-span mapping and acceptance. Consolidation and rollout remain separate gates.

### Checkpoint 4 — temporal understanding and internal forgetting

Delivery split: **4A** makes validity qualification consistent across current search, historical search and source evidence, with controlled-clock storage QA. Relative-time normalization, event-time modeling, consolidation and broader derivative invalidation remain subsequent slices. See [read-time validity](memory-temporal-reads.md).

**Outcome:** changes and temporary circumstances are handled without a memory-management chore.

- Separate captured/observed time, event time and validity. Preserve original temporal expressions, timezone and uncertainty.
- Normalize a bounded set of explicit relative expressions such as “today” and “until Friday” against source time using tested rules. Keep ambiguous phrases such as “this semester” unresolved unless the dates are supplied. Future event time is not proof of attendance or completion.
- Stable preferences do not decay solely from inactivity. Superseded facts remain historical. Consolidation preserves evidence; expiry removes current applicability, not original source history.
- On source deletion, invalidate unsupported claims, chunks, embeddings, entity-link evidence, retrieval caches, and locally retained answer/context derivatives. Tombstones prevent replay resurrection. Document backup retention honestly; this is not a claim of immediate erasure of every historical backup.
- Prefer eligibility checks at read time plus bounded maintenance, not inference repeated across the whole profile.

**Gate:** time-controlled lifecycle tests cover timezone boundaries, future/current/history distinctions, correction, expiry, duplicate support and deletion of an identity-defining source. Run real storage transitions and inspect them. Reuse existing model evidence where the model boundary did not change.

### Checkpoint 5 — relevant retrieval and bounded context assembly

**Outcome:** the companion can find older relevant information without dumping a biography into every answer.

- Add keyword plus semantic candidate retrieval behind a small interface. Use indexed owner-scoped lookup and source/version-scoped embedding caches; keep the canonical store independent of the embedding provider. Select the embedding model/runtime from current documentation and a narrow cost/quality evaluation before integration. No new provider is presumed free or already authorized.
- Search established and unresolved evidence with distinct labels; query identity and correction targets before candidate limits. No unrelated-recency cutoff may prevent designated older evidence from entering the candidate set.
- Use Jev to score/rank useful candidates. Enforce ownership/deletion/admissibility separately from ranking, and retain current/historical/conflict qualifications. A high relevance score cannot make an unresolved identity certain.
- Assemble current question, bounded recent history from the selected conversation, explicitly attached recording passages, active transcript cutoff and a small relevant past-context packet with explicit item/token/time budgets. Deduplicate overlapping evidence; label attached past recordings separately from live capture. Retrieve relevant passages when an attachment exceeds the budget rather than silently treating a truncated recording as complete. Honor an explicit request not to use past memory before retrieval; do not require another model call merely to decide whether a cheap lookup is allowed.
- Replace repeated full-library scans/hashes with indexed candidate lookup, cheap change detection and selected-source/claim validation. Unrelated new notes should not cancel an answer; deletion/correction of selected evidence must invalidate it.
- Version and propagate provenance through context summaries and answers so deleted content cannot re-enter via an old chat summary.

**Gate:** verify designated older paraphrases and correction targets in libraries of 10, 100 and 1,000 synthetic sources; include distractors with matching words. Measure candidate recall, final evidence selection, irrelevant injection and latency separately. Zero owner/deleted-source leakage in the frozen suite. Record a reference environment and latency target before measuring; keep current live-Ask deadlines until a deliberate change is justified. Paid relevance/embedding checks are small and separate from UI replay.

### Checkpoint 6A — persistent main companion chat

**Outcome:** one obvious place to talk, independent of recording selection, with reliable conversational continuity.

- Add a durable owner-scoped main conversation with stable conversation/message/question IDs. Reopen it across app launches; do not create a new thread on each visit or capture. Chat works with an empty recording library. Reserve the data boundary for future side conversations without building their UI, branching or management features now.
- Keep an explicit bounded recent-turn window in model context. If summarization becomes necessary, use source-linked derived summaries; never imply unlimited history is in context or promote assistant text to factual evidence. Future side conversations share relevant memory access, not indiscriminate message history.
- During recording, questions use a fixed snapshot of transcript received so far plus current chat and relevant past sources. Answer generation does not stop capture. Follow-ups retain the relevant conversational subject.
- Answers should sound attentive and direct, personalize when useful, and clarify only when ambiguity materially affects the answer. Memory outage should be disclosed without blocking a useful answer from available context.
- Validate authenticated ownership, message roles, history limits, source revisions and question IDs. Save chat/answers reliably and prevent duplicate turns after reconnect/retry. Propagate deletion to assistant context derived from deleted sources rather than creating a second untracked memory store in chat history.
- Keep microphone permission, interruptions, phone locking and capture limits consistent with the verified capture path. No voice replies or always-on listening in this checkpoint.

**Gate:** execute empty-library chat, follow-up, relaunch, cross-recording recall, correction, deletion, memory outage and chat while transcript events continue through the actual app. Inspect stored turns, context boundaries and capture continuity. Use saved streaming events for UI iteration; perform bounded live answer validation only for changed model integration. Build Mac and iPhone. Physical claims wait for checkpoint 7.

### Checkpoint 6B — recording library and chat connections

**Outcome:** users can revisit a capture and discuss it with the same companion without creating another chat.

- Preserve the recording list and one detail view per capture, including transcript, existing metadata and deletion. Voice notes and meeting notes remain the same source type. Summary generation, user-note editing and optional side conversations remain later work; do not add empty tabs for unimplemented features.
- Implement “Ask about this” from recording detail: return to the main chat with a visible recording attachment, preserving any unsent draft. Allow clearing/replacing that context. Verify attachment ownership and source revision server-side; do not trust a client-provided recording identifier alone.
- Route companion citations to the same recording detail and referenced passage. Handle deleted/unavailable sources explicitly. Preserve access/deletion for legacy personal notes and their original authorship provenance; remove separate personal-note creation from the normal workflow.
- Make Capture meeting note and Talk to companion accessible through simple navigation. Keep capture available from either chat or library, with recording status and stop control visible across both. Switching views preserves drafts and reading position and never implicitly stops capture, cancels an answer or resets memory.
- Use the Manus toggle only as a reference. Implement the smallest usable navigation change; defer visual polish, final labels, library search, summaries and a notes editor.

**Gate:** run actual app navigation with saved transcript/answer events: open a past recording → Ask about this → follow-up → open its source citation → return to the same chat. Inspect the submitted context when attachments are added, cleared or replaced, including a past attachment alongside active capture. Verify unchanged drafts, reading position, no accidental new threads, long-recording context limits, deleted-source handling and legacy-source access. Build both app targets. No new STT calls are needed for these navigation checks.

### Checkpoint 7 — internal rollout and physical acceptance

**Outcome:** the complete agreed experience works on the founder's iPhone with a recoverable deployment.

- Review the exact commit, migration, flags, queued work, daily admission and remaining budget. Back up canonical databases consistently, preserve ledgers/identity, and verify migration on a copy before approved hosted rollout. Do not leave failed experimental handlers enabled as a purported success.
- Use additive migration and flags where practical. Prefer disabling new behavior or a forward fix; do not roll an incompatible old binary onto a newer schema or restore data that resurrects deletions.
- Install the matching native build. Describe the concrete QA steps and wait for founder readiness before recording or asking them to perform timed actions.
- Minimal real-device path: capture a short fictional meeting note → ask during capture while new speech continues → switch between chat and library without stopping capture → stop/save → chat without opening the recording → ask a follow-up → open the saved recording and use Ask about this → verify its attachment and citation return path → capture an explicit changed fact → verify corrected recall and source → relaunch → delete test sources and inspect derived-memory removal.
- Design the pre-voice-enrollment example around explicitly named subjects and preserve unknown speaker identity. Separately verify anonymous first-person speech is not promoted to an account-owner fact. The final test must not rely on the removed personal-note UI or silently assume the recorder is speaking.
- Reuse capture QA when unchanged; the real capture-plus-chat coexistence check is necessary for the new interface. Inspect service/app state as well as the user's answer report. Repeat only failed boundaries.

**Gate:** all designated behavior passes on the physical iPhone, corresponding service state is correct, critical negative fixtures remain passing, and final source cleanup is verified. Record native/backend commits, devices, actual spend, observed latency, limitations and rollback. Review and merge verified checkpoint PRs under standing authorization. Public launch and voice enrollment are separate decisions.

## QA, costs and completion rules

The founder subsequently approved an additional $1, bringing the canonical profile/rework QA cap to **$2**. See the latest reservations and evidence in [memory-atomic-writer.md](memory-atomic-writer.md). Read the canonical ledger again before spending. This is not a new allowance, not a per-checkpoint allowance, and not a promise that the entire rework fits the remainder. No provider calls are required to write this plan.

For each live gate, first state the unanswered question, frozen cases, providers, maximum attempts, expected token/embedding/audio volume and conservative reservation. Reuse cached synthetic results for development, time/lifecycle/identity rules, rendering and network replay. Give new provider integrations their own bounded validation. Stop before exceeding the approved total; request a concrete additional allowance only if it is needed. No automatic paid retries, quota resets or bulk historical model reprocessing. Do not spend on STT to debug memory state or answer rendering.

Each PR reports: outcome; implementation boundaries; schema/API compatibility; expected/observed behavioral evidence; failed evidence; exact code version; model roles/versions; calls/reservations; known limitations; deployment impact. Large model-positive counts cannot compensate for a critical false merge. Passing tests is necessary but not sufficient: execute the delivered path and inspect its result.

Done for this rework means one persistent main companion chat works independently and during capture; users can browse saved recordings, attach one with Ask about this, and open citations at original passages without losing conversation or capture state; recordings feed one automatic source-backed memory system; designated supported corrections work; ambiguous people and conflicts remain honest; older relevant facts remain discoverable; failed inputs do not halt unrelated learning; deletion and validity propagate; and physical acceptance passes. Optional side conversations, generated meeting summaries, a notes editor, voice replies/enrollment and visual redesign remain separate later slices. Completion does not mean perfect recall, verified identity for anonymous speech, public-launch readiness, or unrestricted autonomous agency.
