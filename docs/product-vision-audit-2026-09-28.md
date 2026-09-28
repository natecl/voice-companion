# Product vision implementation audit — September 28, 2026

## Target and audit boundary

**Agreed positioning:** AI notes that proactively contribute to discussions.

**Full target:** an AI note-taking app acting as a third smart person in conversations. Capture lectures, meetings, appointments and voice notes; connect the unfolding discussion with past notes, calendar, email and messages; proactively contribute useful reminders, questions and ideas through text; retain Ask across captured material. [Canonical description](product-source-of-truth.md#full-product-vision--september-28-2026).

The exact agreed short description has **51 characters**, not 50. Preserve it as positioning. Suggested form-compatible variant (not yet founder-selected): **“AI notes that proactively join conversations”** (44 characters). No application field was edited.

Audit base: `660e4c7` (main, includes PR106 note-preview fix). Method: inspect native entry points, service request/response paths, source schema, model request configuration, feature maps and dated QA/rollout evidence. This pass changes documentation only. It does not rerun provider/device tests or independently inspect the live service. “Implemented” below means code plus cited historical bounded evidence, not universal correctness or renewed acceptance. Last recorded backend rollout is `4dd5b70`; native follow-up source is `3954284`. No production data was read for this audit.

## Assessment

We have an internal **capture → transcript → notes → personal memory → user-requested chat** foundation. We do not yet have the defining **listen → notice relevance → decide whether/when to contribute → surface an unsolicited useful text** experience. A polished chat UI, an onboarding greeting and background memory extraction do not constitute proactive participation.

The current implementation is worth retaining. The missing core is an event-driven contribution path and its product-quality evidence, not a requirement to replace the whole memory system or build a new generic chat app.

## Capability and gap map

| Capability required by the vision | Inspected state and evidence | Remaining work / acceptance gap |
| --- | --- | --- |
| Deliberate voice capture and live transcript | Implemented internally: `App/Audio/`, `App/Transcription/`, `SessionController.swift`, `Backend/relay.py`; [V1 acceptance](v1-acceptance.md), [background evidence](v1-background-validation.md) | Five-minute internal cap is unsuitable for full lectures/appointments. Extend through a measured duration/reconnect/persistence/battery/cost checkpoint, not just a constant change. Best-effort speaker labels are not identity. |
| Stored notes, transcript and retrieval | `RecordingNotes.swift`, `RecordingNotesView.swift`, `recording_notes.py`, `notes_generation.py`, `notes_service.py`; [notes rollout](recording-notes-rollout.md) | Generated notes follow terminal capture; no live rolling note-generation claim. Notes reads require connectivity. No note editing; useful later, not a prerequisite for the first proactive test. |
| Notes library and capture controls | `CompanionRootView.swift`: Notes cards, search, swipe/hold actions, shared composer, live View/Stop; [native UI evidence](native-experience-ui.md) | No product-quality evidence that users can notice contributions while staying present. Do not equate pixel fidelity with this acceptance. |
| Existing captured-context memory | Source-scoped learner, identity/provenance/lifecycle store and unified recall; [foundation](simple-memory-foundation.md), [rollout](simple-memory-rollout.md) | Bounded cases pass, not “knows everything.” Unresolved identity/time, delayed learning and conservative misses remain. Broad cross-life relevance and long history need evaluation. |
| Questions across recordings during capture | `CompanionController.send`, `companion_service.validate_request/handle`, `companion_context.assemble`; [companion rollout](companion-internal-rollout.md) | User supplies a nonempty question. Live evidence is a snapshot at Ask time, not an ongoing reasoning subscription. Preserve this known working path. |
| Recognize the current topic without a prompt | Missing. `notes_recall.prepare` queries on `data['question']`; no transcript-triggered proactive consumer found in active app/service wiring | Incremental session context, topic/relevance queries, revision/cutoff handling, “already discussed” state and bounded scheduling. A timer that sends fabricated user questions is not the desired contract. |
| Proactively decide whether/when to contribute | Missing. Current service accepts Ask/history/source; memory jobs learn, not deliver live suggestions | Explicit contribution/silence decision, relevance/novelty checks, duplicate suppression, cooldown, late-result cancellation, budget admission and auditable decision reasons. Judge model/thresholds unresolved. |
| Context-sensitive contribution | Generic chat can brainstorm using model knowledge; `companion-chat-v3.md` does not establish specialized appointment/study behavior | Adapt to conversational goals and uncertainty. Evaluate appropriate clarification/reminder versus intrusive, irrelevant or overconfident contribution. Medical/therapy/finance use is a target, not validated expert support. |
| Outside knowledge and new ideas | Model knowledge/general answers exist; `ask.py` sends `tools=[]` | No live web retrieval/fact-checking path. Decide when current information is required; implement source attribution/freshness and clearly distinguish sourced facts, model knowledge and suggestions. |
| Personal calendar context | No calendar connector/EventKit/OAuth path in inspected app/service | Choose provider/device scope, permission and sync model; preserve event time/timezone, updates/cancellation, ownership, provenance and revocation. |
| Personal email context | No mail connector/OAuth/ingestion path | Provider selection, bounded authorized ingestion, threading/quoted content, incremental updates, token security, source links and disconnect/erasure contract. |
| Message context | No message connector or import path | Validate supported access for selected platforms before promising complete history. Do not assume unrestricted iMessage access. Preserve conversation participants and private-source visibility. |
| Imported videos, recorded lectures, external audio | Founder motivation, not implemented ingestion. Microphone capture exists; no normal file/URL import or Mac system-audio path found | Pick one supported import source and verify extraction/timestamps/provenance. Headphone playback is not reliably captured by room microphone. Prioritize separately from live conversation contributions. |
| Proactive presentation and user control | Normal streamed chat exists; no proactive item type, delivery channel or per-session contribution controls | Distinguish unsolicited contribution from user-requested answer; decide inline vs card, enable/quiet controls, dismissal/feedback, source inspection and accessibility. Keep private context on the intended user's display; do not automatically broadcast it. |
| Background contribution delivery | Capture has locked-screen evidence; chat is foreground work and cancels on background | Separate capture continuity from analysis/delivery execution. Validate the chosen foreground/background model, battery, network and any notification privacy. No always-on guarantee. |
| Memory/data control | Ordinary note deletion preserves learned knowledge and historic replies; unavailable links removed; `memory_retention.py`, `companion_chat.py` and PR104 | Explicit erasure/account deletion, connector revocation and backup retention require complete end-to-end semantics. Preserve existing deletion behavior until an explicit revised contract is agreed. |
| Public onboarding/accounts/subscriptions | `ExperienceAccountView.swift` explicitly labels signup/billing/account actions unconnected; internal credential enrollment exists | Real identity/account ownership, sign-in/out, recovery, subscription entitlement, deletion and release/legal flows. Provider choice/prices remain undecided. Visual previews are not integrations. |
| Economics, capacity and repeat use | Bounded internal admission/usage ledger; single-instance host; no prospective proactive usage benchmark | Budget per active minute/contribution and failure; measure latency/cost at realistic duration. Repeated voluntary capture/use, usefulness and distraction need a pilot; no evidence yet of retention/product-market fit. |

## Knowledge architecture: reuse and additions

Keep existing source → derived notes → verified memory → retrieval separation. Add source adapters without promoting external content to instructions. Every future source requires ownership, origin, revision, timestamps, participant uncertainty, permitted scope and deletion/revocation behavior. See [knowledge feature map](features/knowledge.md).

A proposed proactive path, **not implemented**:

```text
Deliberately enabled capture + stable transcript updates
    -> bounded current-conversation context
    -> candidate connections from authorized prior sources / outside knowledge
    -> contribution-or-silence decision (relevance, novelty, timing, privacy)
    -> short text with provenance and uncertainty where useful
    -> dismiss / follow up / quiet + evaluation evidence
```

Reuse existing retrieval and context validation where appropriate. Live transcript corrections, source deletion, session stop or owner changes must cancel or revalidate pending contributions. Assistant-generated suggestions must not become independent personal-memory evidence. A contribution cannot claim the user said something merely because another speaker did.

## Proposed delivery order

This is an engineering recommendation for founder review, not new implementation/spending/deployment authorization. No exclusive launch ICP has been chosen. Study discussions are a lower-complexity candidate for the first test, while the full product remains broader.

1. **Freeze one useful proactive moment and its negative cases.** Use synthetic/consented prior notes plus an unfolding conversation. Expected example: a supported sleeping concern is surfaced during a relevant discussion, without a typed question. Freeze cases for already mentioned concern, wrong person, corrected/expired fact, unrelated topic and “say nothing.” Choose capture enable/quiet behavior and display treatment before implementation. Gate: assess relevance and interruption value separately from correctness.
2. **Build the bounded proactive loop over existing notes.** Add explicit event/state contracts, live-context retrieval, decision/silence, duplicate/late-result suppression, user control and contribution persistence. Gate: actual app receives a useful unsolicited text, remains quiet on negatives, stops cleanly, survives replay/reconnect without duplicate contributions and records bounded cost. Start with replay; provider and physical evidence are separate gates. Do not silently reuse an exhausted paid allowance.
3. **Make the loop viable for a real conversation.** Longer capture, interruption/reconnect recovery, periodic durable save, transcript revisions, learning lag, foreground/background delivery, latency and battery. Gate: a consented realistic-duration physical-iPhone session with preserved notes and useful timely contributions; validate supported Mac behavior separately. The five-minute cap blocks realistic lectures today.
4. **Add trustworthy outside knowledge and contextual behavior.** Current-information retrieval when needed, distinguish suggestions from recalled statements, and test study/work/appointment scenarios with appropriate uncertainty. Gate: supported source/freshness where factual currency matters; silence or clarification for ambiguous/high-consequence cases; no claim of specialized readiness based only on a prompt.
5. **Add connected context incrementally.** Suggested order: calendar, email, then a technically supported message source. This order is a proposal. Validate access feasibility first; add shared provenance and source-scope controls with each adapter. Gate: a real authorized source improves a concrete contribution, and update/disconnect/erasure works. Vision includes all three even before delivery. Do not bundle imports, new graph infrastructure or every provider into the first adapter.
6. **Prepare distribution and learn from repeat use.** Real accounts/data controls, appropriate entitlement/billing scope, TestFlight build pipeline and pilot readiness. Start with the approved capture/contribution experience; measure useful contributions per session, missed opportunities, dismissals/quiet use, distraction, repeated voluntary sessions, latency and cost. Set thresholds before running the pilot; do not invent success numbers after the fact.

Steps 2–3 are the central product gap. Connected sources deepen the full vision but are not necessary to test whether proactive participation from captured notes is valuable. User demand may change ordering; retain the baseline rather than restart infrastructure without evidence.

## Audit verification and limits

Inspected code at base above, compared named routes with dated rollout/fixture evidence, searched the active native/backend source for proactive event consumers, calendar/email/message connectors, web tools, import hooks and public auth/billing integration. Absence conclusions are scoped to this repository and active wiring, not a claim about hidden external systems. No live service read, microphone test, paid model call, user-data access or production modification occurred. Documentation checks cover links, code paths, active-versus-historical wording and the exact short-description length. Historical QA remains dated; a feature audit is not fresh runtime acceptance.

Documentation verification: reviewed the final product/map/audit diff; checked all 333 local Markdown link targets across the 18 changed/new documents, canonical wording in the five entry-point documents, character counts and named core code paths; `git diff --check` passed. Repaired one pre-existing historical profile-recall link to its verified archived commit. No app/backend files changed, so no runtime/provider test was warranted for this checkpoint.

## Implementation update after the initial audit

The [local native proactive slice](proactive-native.md) now implements foreground lifecycle, bounded past-note retrieval, decision/draft, idempotent message storage and ordinary chat rendering. The [four-call model screen](proactive-model-screen.md) favors Luna provisionally. This supersedes the initial absence finding for local code only; hosted/release enablement, physical acceptance and the remaining quality gaps are open.
