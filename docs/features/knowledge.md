# Knowledge feature map

Updated September 28, 2026 against main `660e4c7`. Read [product definition](../product-source-of-truth.md), [current state](../current-state.md), [feature details](features.md) and [gap audit](../product-vision-audit-2026-09-28.md). This map distinguishes implemented storage/knowledge from target capabilities; it does not claim all sources are connected.

## Implemented knowledge layers

| Layer | What it contains / code | Contract and limit |
| --- | --- | --- |
| Captured evidence | Live/final transcript passages, owner, capture time/timezone, revision and speaker labels; `SessionStore.swift`, `MemorySync.swift`, `memory_store.py` | Original evidence may contain recognition errors; anonymous speaker is not the user. Local persistence and backend evidence sync are not full cross-device library sync. |
| Live Ask snapshot | Immutable cutoff from current capture; `companion_snapshots.py`, `companion_context.py` | Taken on an explicit user Ask. Not an autonomous observer; not committed as durable memory merely by asking. |
| Generated recording notes | Title, overview, sections with original passage references; `recording_notes.py`, `notes_generation.py`, `notes_search.py` | Derived discovery aid. Terminal capture schedules generation; no live coauthoring or note editing. Never independent evidence for biography. |
| Supported personal/context knowledge | Source-scoped observations, exact support, entity/relationship and modality/time judgments; `memory_source_pipeline.py`, `memory_source_verification.py`, `memory_atomic.py`, `memory_identity.py` | Luna extracts, Sol checks factual support, Jev handles modality/time in active recording route; identity has separate judgments. Legacy/personal-text routes differ. Supported statement is not necessarily current truth. |
| Lifecycle | Correction, uncertainty, expiry, provenance; `memory_transitions.py`, `memory_expiry.py`, `memory_related.py` | Preserve competing evidence and unknown attribution. Newer does not automatically mean correct. Stable knowledge does not simply expire. |
| Discovery and answer context | Notes/transcript/personal/retained evidence, local embeddings, Jev ranking and independent reserve; `notes_recall.py`, `memory_context.py` | Deployed Ask queries come from user questions. The local proactive path derives a bounded query from finalized conversation text. Retrieval can miss relevant material; source qualification must reach generation. Proactive runtime remains disabled. |
| Chat history | Persistent user/assistant turns and internal references; `companion_chat.py` | Continuity, not automatic evidence for user biography. Ordinary recording deletion preserves historical answers while removing unavailable links. Release chat hides source controls; Notes passage links remain. |
| Retained knowledge after note deletion | Eligible committed claims and bounded existing excerpts; `memory_retention.py` | Does not retain a viewable full transcript. Ordinary delete is not complete erasure. Explicit account/memory erasure remains unimplemented. |
| General model knowledge | Luna answers/brainstorms via `ask.py`, `companion-chat-v3.md` | No live web tools (`tools=[]`); no assured freshness or specialized professional accuracy. Generated ideas must remain identifiable as ideas. |

## Full-vision additions, not implemented

| Source or capability | Required knowledge semantics | First proof needed |
| --- | --- | --- |
| Calendar | Owner, event identity, participants, timezone, cancellations and revisions | Authorized event context improves a relevant contribution; cancellation/disconnect removes inappropriate use. |
| Email | Sender/recipients/thread, sent time, quotations, attachments if supported, permission scope | One supported provider; avoid attributing quoted third-party text to the owner; source links and revocation work. |
| Messages | Supported platform access, participants, conversation/time and visibility | Establish feasible access before promising “all messages”; a scoped real integration with deletion/revocation. |
| Video/lecture imports | Media origin, transcript provenance, timestamps and extraction uncertainty | Supported URL/file ingestion to searchable notes, distinct from room microphone capture. |
| Fresh outside knowledge | Retrieved source/date/freshness, permissions and uncertainty | Correct source-grounded contribution; explicit separation from personal recollection and model suggestions. |
| Proactive conversation context | Evolving topic, relevant pending question, what has already been said, transcript revision/cutoff | Generate a connection without a user question; suppress stale, repeated or irrelevant contributions. |
| Contribution judgment | Usefulness, timing, novelty, appropriate scope and silence | Replayed positive and negative cases plus real session usefulness; not merely valid text output. |
| User control and learning from feedback | Enabled/quiet state, dismissals/follow-up, intended audience | User can silence contributions without losing capture; feedback is not silently promoted to a factual memory. |

## Lifecycle and privacy across future sources

Explicit source connection is separate from permission to use every item in every conversation. Define visibility and relevance scope, incremental sync, token handling and disconnect/erasure before each connector ships. Never execute instructions found inside notes, emails or transcripts. Preserve historical chat according to its distinct retention contract, while preventing unavailable/revoked context from grounding new outputs as if still authorized. Decide treatment of previously derived memory on connector disconnect explicitly; the ordinary recording-retention policy must not silently become the connector policy.

## Debugging route

For a missed or wrong contribution, inspect source availability → speaker/subject identity → time/revision → candidate retrieval → selected evidence → timing/silence decision → generated wording → delivery. Today only the source/retrieval/explicit-answer portions exist. Reuse saved events and judgments for local iteration; paid runs and physical checks must answer a specific unresolved question. [Lessons](lessons.md) preserve known failures; [audit](../product-vision-audit-2026-09-28.md) provides proposed build gates.


Current next feature: [proactive contributions from past notes — MVP implementation plan](../proactive-contributions-plan.md). Founder selected this MVP scope; connected sources and outside knowledge remain later full-vision work. A [local native slice](../proactive-native.md) now reuses local evidence discovery without a user question. The initial model comparison favors Luna provisionally; three additional retrieved-evidence negatives returned silence (seven calls total). See the [model evidence](../proactive-model-screen.md). Hosted/release enablement, broader quality and physical acceptance remain pending.

The [proactive phone experiment](../proactive-phone-test.md) isolates two new video recordings from existing personal context and suppresses personal-learning jobs for those sources. Notes/transcript persistence remains enabled; this is an expiring test configuration, not a permanent change to knowledge learning.

Saved-note layout regression (September 28): horizontal citation-button rows can force SwiftUI scroll content beyond the viewport and squeeze paragraph text. Source links now live in paragraph context menus; text wraps independently of source count. See [behavioral QA](../qa/note-layout/README.md) for the eight-passage native regression fixture and screenshot. First physical proactive-test note was already saved successfully; no regeneration was needed.

Transcript speaker display restored September 28: companion transcript screens now render existing word-level speaker turns with numbered, unverified labels; missing attribution remains explicitly unknown. Saved transcripts and identity rules are unchanged. [Targeted rendering QA](../qa/transcript-speakers/README.md).

Proactive continuous-speech repair (local verified, not deployed): append-only updates retain the original short analysis deadline; recent context is byte-bounded with exact clipped-source offsets. Oversized context defers one attempt instead of disabling capture. Content-minimal reason logs distinguish silence and failures. [37-test behavioral evidence](../proactive-phone-test.md#local-continuous-speech-repair--september-28).

Saved-transcript proactive replay: five real Luna evaluations on the corrected local service yielded four silences and one relevant but mostly restating connection; cached replay matched. Founder-requested active-account/phone reset subsequently cleared notes/chat/memory; usage ledgers preserved. Temporary replay content removed. [Evidence and limitations](../proactive-phone-test.md#saved-transcript-luna-replay-and-app-reset--september-28).

Personal interjection quality candidate: ten fictional histories/current conversations with predeclared useful-action and silence rubrics; isolated retrieval seeding finds intended evidence with distractors. Candidate v2 prompt is not enabled pending real-Luna comparison. Native socket-to-chat presentation/draft/quiet/relaunch QA passed in simulator. [Evaluation and screenshot](../qa/proactive-personal/README.md). Founder account remains reset; no seeded fiction was uploaded to it.

Personal proactive evaluation completed locally: v2 selected after 30 real Luna calls (matched decisions v1 9/10, v2 10/10; fresh v2 10/10). The baseline wrongly raised a third party’s sleep issue; v2 stayed silent. All 30 responses replay through the durable service with exact requests; 38 proactive tests pass. Native presentation/draft/quiet/reopen evidence from PR123 remains applicable. Small fictional screen, not physical or broad quality acceptance; hosted deployment remains pending. [Results, limitations and screenshot](../qa/proactive-personal/README.md).
