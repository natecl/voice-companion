# Feature details

Use the [index and authority rules](README.md) first. Paths below are repository-relative. “Verified” always means the bounded cases in the linked evidence, not universal accuracy. Test paths are entry points for targeted QA, not instructions to rerun every suite or consume paid allowances.

## Capture and live transcript

**Experience:** start microphone capture, see text arrive, stop and revisit it. Capture can continue while the companion answers. iPhone locked-screen capture has physical evidence; interruptions can stop capture while preserving received text. Speaker labels can be delayed or wrong and cannot establish the user's identity.

**Code:** `App/Audio/{MicrophoneAccess,MicrophoneCapture,AudioCapture}.swift`; `App/Transcription/{LiveTranscriber,RecordingConnection,Transcript}.swift`; `App/Sessions/{SessionController,RecordingFinalizationTask}.swift`; `Backend/relay.py`. Hosted provider URL currently selects `grok-voice-transcribe-2.0`. App wiring and fixture selection are in `SessionController+App.swift`.

**Boundaries:** microphone permission and platform audio lifecycle → provider connection → shared transcript reducer → session persistence. Partial/final events and stop/interruption are distinct. Receiving text is not proof of a finalized recording or completed learning. No Mac system audio.

**QA route:** `UnitTests/{TranscriptTests,RecordingLifecycleTests,TransportFailureTests,LiveAskTests}.swift`; `UITests/{MicrophoneUITests,SavedRecordingUITests,RecordingInterruptionUITests,LiveAskUITests}.swift`; `Backend/test_relay.py`. Use event replay for rendering/state bugs; actual audio only when the audio/provider boundary is implicated. Physical microphone claims require device evidence and founder readiness.

**Evidence:** [V1 acceptance](../v1-acceptance.md), [reliability edge cases](../reliability-edge-cases.md), [companion rollout](../companion-internal-rollout.md). V1's earlier current-conversation-only Ask limit is superseded by companion recall; its capture evidence remains useful.

## Recording library and evidence sync

**Experience:** saved recordings reopen with their transcripts; Ask about this attaches an existing recording to the main chat. A recording is not a new chat.

**Code:** `App/Sessions/SessionStore.swift` (`CaptureSession`, local JSON persistence); `MemorySync.swift` (`MemoryOutbox`, transport, recovery); `SessionController.swift` (save, attachment, deletion); `Backend/{memory_service,memory_store}.py` (source revision and owner boundaries).

**Boundaries:** local save precedes upload. Outbox acknowledgments and source revisions control sync; failed upload must preserve local data. Backend evidence sync does not establish cross-device library sync. Revisions must invalidate stale derived context; tombstones prevent late upload from resurrecting deleted sources.

**QA route:** `UnitTests/MemoryTests.swift`, `UITests/{SavedRecordingUITests,MemoryUITests}.swift`, `Backend/test_memory.py`. Reproduce offline/outbox/revision behavior with local socket fixtures before considering any provider run.

**Evidence:** [memory foundation](../memory-foundation.md), [source navigation](../companion-source-navigation.md), [retention rollout](../retained-memory-rollout.md). Older source-deletion cascade evidence is historical for ordinary recordings.

## Companion chat and source navigation

**Experience:** one persistent main chat with follow-ups, optional recording attachment, and questions while recording. Companion and Recordings are navigation surfaces. Original-source references open the relevant passage; retained memories use a deleted-recording label.

**Code:** `App/CompanionRootView.swift`; `App/Sessions/{CompanionController,CompanionConnection,ConversationAnswer,SessionController}.swift`; `Backend/{companion_service,companion_chat,companion_context,companion_snapshots,ask}.py`; `Backend/prompts/companion-chat-v2.md`. `ConversationAskView.swift` and session-scoped Ask code retain earlier paths; inspect active app configuration before modifying them.

**Boundaries:** capture and answer lifecycles are independent. Live transcript snapshots are immutable evidence for an individual answer; subsequent text cannot silently change that answer's source. Turns have durable pending/completed/interrupted states and request identity. Recover uncertain delivery from saved state rather than blindly paying for another answer. Backgrounding cancels foreground chat work; this does not imply capture stops.

**QA route:** `UnitTests/{CompanionControllerTests,CompanionConnectionTests,ConversationAnswerTests}.swift`, `UITests/{CompanionUITests,CompanionPhoneUITests}.swift`; backend `test_companion_{chat,context,service,snapshots,runtime,prompt}.py`. Use the real local service with recorded/injected events for navigation, streaming and persistence; model quality requires separate evidence.

**Evidence:** [chat storage](../companion-chat-store.md), [source navigation](../companion-source-navigation.md), [physical rollout](../companion-internal-rollout.md), [retained answer/reopen](../retained-memory-rollout.md). No side-chat or voice-reply claim.

## Automatic memory learning

**Experience:** recordings supply useful personal context automatically, without a memory-approval inbox. Learning happens outside the main answer loop.

**Code:** `Backend/hosted.py` composes the deployed writer; `memory_writer.py` supplies the worker and metering helpers; `memory_evidence_writer.py` orchestrates the current writer. `memory_evidence.py` extracts exact evidence; `memory_evidence_chunks.py` / `memory_chunks.py` preserve bounded continuity; `memory_source_verification.py` checks factual support and metadata; `memory_atomic.py` commits evidence and lifecycle changes; `memory_store.py` owns sources, jobs and cached results.

**Current model roles (not timeless recommendations):** Luna extracts; Sol (`gpt-6-sol`) independently verifies source entailment in the enabled recording path; Jev verifies modality/time and bounded relation decisions; Luna handles recording-subject identity. Do not describe production as Luna verifying its own extraction or Jev doing all verification. Personal-text/legacy paths differ; inspect `hosted.py` flags and writer branches.

**Boundaries:** original source ≠ proposal ≠ independently supported claim. Preserve exact supporting passages, revision/owner, judgments and atomic commit. Completed job can mean zero accepted claims. Stale/deleted sources cannot commit later. Preserve failed evidence; no automatic paid retries or historical backfill. A temporal abstention can retain an independently supported undated fact as unresolved; explicit date failures keep their gate.

**QA route:** `test_memory_{evidence,evidence_chunks,evidence_writer,atomic,worker}.py`, `test_source_verification.py`, `test_uncertain_memory_time.py`; recorded fixtures under `Backend/fixtures/{source-verification,uncertain-time}`. Exact-request replay through writer/SQLite is stronger than a standalone classifier pass.

**Evidence:** [chunk writer](../memory-chunk-writer.md), [independent verification](../independent-source-verification.md), [verification rollout](../verification-rollout.md), [Cedar failure and fix](../uncertain-memory-time.md).

## Personal context and identity

**Experience:** remember relationships, preferences, interests, goals and circumstances across life, rather than imposing a work-only profile. Profile context is derived knowledge, not a mandatory form or a separate normal capture type.

**Code:** `Backend/{memory_identity,memory_identity_model,memory_recording_identity,profile_identity}.py`; `memory_store.py` profile reads; `memory_evidence_writer.py` identity/relationship decisions. Existing authenticated `personal_text` input and native `savePersonalNote` are legacy/QA provenance paths, not the preferred product interaction.

**Boundaries:** speaker number ≠ named subject ≠ account owner. “Maya likes swimming” does not establish that Maya is the user. Authored text may discuss somebody else. Source-grounded identity links, relationship qualifiers and owner scope must survive correction, consolidation, retrieval and deletion. Unknown identity stays unresolved; no voiceprint enrollment has shipped.

**QA route:** `test_memory_{identity,identity_model,recording_identity}.py`, `test_profile.py`, negative cases in writer tests. Test same-name people, quotations, changing subjects, and account-owner misattribution at the identity layer.

**Evidence:** [identity foundation](../memory-identity.md), [identity transitions](../memory-identity-transitions.md), [personal profile foundation](../personal-profile-foundation.md), [current verification](../verification-rollout.md). Early profile docs are checkpoint history, not the latest deployment status.

## Corrections, time and maintenance

**Experience:** use updated knowledge without forgetting why it changed; keep plans, past events and uncertain statements distinct from current facts. Maintenance is internal, not a suggestion/forgetting inbox.

**Code:** `Backend/{memory_transitions,memory_expiry,memory_time,memory_related}.py`; `memory_atomic.py`, `memory_evidence_writer.py`, and `memory_store.py` maintenance and read-time qualification.

**Boundaries:** later capture alone does not authorize correction. Identity, relation and current applicability must be supported before supersession. Unresolved changes may qualify prior knowledge as disputed without replacing it. Expiry retires applicability, not source evidence, and does not prove an event happened. Stable facts do not simply decay. Calendar references use source capture time/timezone; a bare weekday is not automatically next week's date. Expiry currently has a narrow verified ISO through-date path. Uncertain undated memories do not acquire validity dates or overwrite current facts.

**QA route:** `test_memory_{transitions,expiry,time,temporal_reads,consolidation,related,uncertainty}.py`, `test_uncertain_memory_time.py`; writer composition tests. Exercise correction chains, duplicate evidence, future/past scope and deletion ordering with saved judgments.

**Evidence:** [temporal reads](../memory-temporal-reads.md), [expiry](../memory-expiry.md), [consolidation](../memory-consolidation.md), [multi-source evidence](../memory-multi-source.md), [uncertain timing](../uncertain-memory-time.md). These are bounded capabilities, not universal natural-language time understanding.

## Retrieval and answer context

**Experience:** relevant past recordings inform the current conversation; attached/live context and chat history support follow-ups. Turning off past memory is an explicit constraint.

**Code:** `Backend/{indexed_recall,memory_hybrid,memory_search,memory_vectors,memory_indexing,local_embeddings}.py` retrieve/index original sources; `memory_ranking.py` / `memory_multi_ranking.py` perform bounded Jev ranking; `memory_related.py` expands related lifecycle evidence; `memory_context.py` hydrates/validates references; `companion_context.py` assembles bounded live/attached/history/past context. `ask.py` uses Luna for answers. `local_reranker.py` exists as an adapter/evaluation option but is not wired into the inspected hosted path.

**Boundaries:** deterministic owner/revision/deletion guards precede probabilistic usefulness. Ranking is not proof of factual truth. Context fingerprints prevent stale evidence use; source identity and lifecycle qualifiers must reach the answer. Missing/partial indexing is not “no memories.” Retained deleted-recording claims currently use lexical retrieval, not their own semantic embeddings. Original transcripts and retained claim text are different evidence types.

**QA route:** `test_indexed_recall.py`, `test_multi_ranking.py`, `test_memory_{search,vectors,indexing,ranking,context,related}.py`, `test_companion_context.py`. Inspect candidates → ranking → selected packet → model output to isolate a miss. Don't re-record audio to fix retrieval.

**Evidence:** [indexed recall](../memory-indexed-recall.md), [index worker](../memory-index-worker.md), [ranking](../memory-ranking.md), [related evidence](../memory-related-evidence.md), [capacity](../companion-capacity.md). Local embeddings are pinned/prewarmed; do not infer unlimited Starter capacity from the bounded measurements.

## Recording deletion and retained memory

**Experience:** deleting a recording removes its transcript/library entry. Already learned knowledge can still answer questions, visibly labeled “Memory · recording deleted.” The deleted transcript cannot be opened through that reference.

**Code:** native `SessionController.swift`, `MemorySync.swift`, `CompanionRootView.swift`, `ConversationAnswer.swift`; backend `memory_store.py`, `memory_retention.py`, `companion_chat.py`, `memory_context.py`, `memory_related.py`, and `ask.py` retained-memory instructions.

**Boundaries:** retain eligible committed claims and their already stored bounded excerpts, not a copied full transcript. Remove source payload/index/snapshots; preserve a tombstone. Original-source answers invalidate; newly generated retained-memory answers may persist. Corrections/identity/time still apply. Revision is not deletion. Personal-text deletion keeps its older invalidation semantics. Unsupported legacy claims are not backfilled; previously deleted data is not restored. This is not explicit erasure of every memory or backup.

**QA route:** `test_memory_retention.py`, `test_uncertain_memory_time.py`, companion persistence/UI checks. Inspect backend deletion and retained packet before spending a phone Ask. Saved response replay covers most changes; one physical deletion/answer/reopen check proves the native path.

**Evidence:** [retention contract](../retained-recording-memory.md), [final physical acceptance](../retained-memory-rollout.md), [Cedar recovery](../uncertain-memory-time.md). Preserve the initial learning failure alongside the successful repaired run.

## Internal access, budgets and rollout

**Code:** native `RelayConfiguration.swift` / `RelayCredentialStore.swift`; `Backend/{hosted,admission,admin,service_policy,memory_budget,profile_budget}.py`; `scripts/check.sh`; `project.yml`.

**Boundaries:** credentials stay out of source and app binaries. Single-instance startup owns the service lock, migrations and interruption recovery. Backend composition/flags determine active paths; the existence of an adapter is not activation. Admission attempts, money reservations, suballocations and manual-QA readiness are separate gates. A provider failure does not refund a reservation. Subledger funding must not be counted twice or mistaken for microphone usage. Deployment approval does not grant more budget.

**QA route:** `test_admission.py`, `test_admin.py`, `test_hosted_startup.py`, `test_hosted_relay.py`, `test_rework_budget.py`. Run the narrowest applicable checks. `scripts/check.sh` supports mac/simulator/device; its default tests deliberately skip some manual microphone classes. Read the script and [development instructions](../development.md) before claiming device coverage.

**Evidence:** [V1 runbook](../v1-runbook.md), [capacity](../companion-capacity.md), [retention rollout](../retained-memory-rollout.md). Back up consistently before deployment; compare data/usage preservation and health. Forward-fix or use schema-compatible rollback; restoring old data can resurrect deleted sources and erase usage history. No automatic public deployment or subscription operations are implied.


## Transcript-derived recording notes

**Experience:** saved recordings have Notes and Transcript views. Notes contain a source-grounded title, overview and flexible sections; passage links show the original text. Live capture remains transcript-first. Local integration is verified and the [internal rollout](../recording-notes-rollout.md) is deployed; physical acceptance remains a separate gate.

**Code:** `Backend/recording_notes.py` owns revision-bound storage; `MemoryStore.put_source(generate_notes=True)` atomically schedules new terminal recording sources. `notes_generation.py` owns the transcript-only Luna request and validation; `notes_service.py` owns authenticated reads/retries and the serial worker; `notes_budget.py` checks separately funded reservations. `App/Sessions/RecordingNotes.swift` owns bounded socket reads; `App/RecordingNotesView.swift` and `CompanionRootView.swift` present notes and navigate supporting passages.

**Contracts:** reads never generate; unchanged uploads never backfill/retry; source changes invalidate; deletion removes notes regardless of learned-memory retention. Saved notes are server-side, so reopening needs connectivity. Existing capture outbox terminality is the scheduling boundary. Notes are not memory claims and this slice does not replace the existing harness.

**QA:** `test_recording_notes.py`, `test_notes_generation.py`, `test_notes_service.py`, `test_notes_budget.py`, and `RecordingNotes{,Phone}UITests.swift`. Reuse recorded model responses for quality replay and local synthetic socket fixtures for UI work; don't run paid transcription for a notes presentation bug. See [notes evidence and rollout gate](../recording-notes-plan.md).
