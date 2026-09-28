# Feature and context map

Reconciled against main `660e4c7` on September 28, 2026 and recorded rollout evidence. This documentation audit did not re-inspect the live service. Read [current state](../current-state.md) and the [product vision gap audit](../product-vision-audit-2026-09-28.md) for the implementation/vision boundary.

> AI notes that proactively contribute to discussions

The product vision is an iPhone-first AI note-taking app that proactively contributes context, questions and ideas through text, with Mac support. Calendar, email and messages belong to the full vision; captured notes/conversations are the initial sources. The existing entry points remain **Capture meeting note** and **Talk to companion**. Granola remains the Proven. See the [knowledge map](knowledge.md) for evidence, derived memory and missing source integrations.

## Read in this order

1. [Product source of truth](../product-source-of-truth.md), [engineering principles](../engineering-principles.md), and [historical V0 boundary](../v0-scope.md).
2. The relevant feature below in [feature details](features.md), then its named implementation files and evidence.
3. [Knowledge feature map](knowledge.md) and [full-vision gap audit](../product-vision-audit-2026-09-28.md) for missing capabilities and proposed next checkpoints.
4. [Learned lessons and debugging routes](lessons.md) before changing a known failure path.

Canonical product/engineering documents retain authority. Maps describe verified code and bounded evidence; plans describe intent. Older checkpoint documents may say “not deployed” or describe deletion cascades that later checkpoints superseded. Read their dates and follow the current rollout links below. For live quota, credential, flag or deployment state, inspect the actual system rather than treating a dated document as current runtime truth.

## Feature index

| Feature | Current boundary | Detail |
| --- | --- | --- |
| Microphone capture and live transcript | Internal Mac/iPhone flow; speaker labels best-effort | [Capture](features.md#capture-and-live-transcript) |
| Transcript-derived notes | Internally deployed; local native and bounded physical-iPhone QA pass | [Notes plan](../recording-notes-plan.md) |
| Recording library and evidence sync | Local saved transcripts; backend evidence outbox, not full cross-device library sync | [Library](features.md#recording-library-and-evidence-sync) |
| Persistent companion chat | One main chat; ordinary conversation and contextual questions; v3 personality/plain-message behavior internally deployed | [Companion](features.md#companion-chat-and-source-navigation) |
| Composer dictation | Bounded physical acceptance passed; native candidate installed | [Dictation](features.md#composer-dictation) |
| Automatic learning | Source-scoped background extraction, independent verification, atomic writes | [Learning](features.md#automatic-memory-learning) |
| Personal context and identity | Whole-life facts/relationships with provenance; no voice enrollment | [Identity](features.md#personal-context-and-identity) |
| Corrections, time and maintenance | Qualified lifecycle and bounded expiry; source-scoped additions; no memory-management UI | [Lifecycle](features.md#corrections-time-and-maintenance) |
| Retrieval and answer context | Unified notes/transcript discovery, one Jev ranking, independent evidence reserve; pre-retrieval classifier disabled | [Recall](features.md#retrieval-and-answer-context) |
| Recording deletion and retained memory | Transcript removed; eligible learned knowledge retained with unavailable-source label | [Deletion](features.md#recording-deletion-and-retained-memory) |
| Proactive contribution and connected context | Full product vision; missing from active implementation | [Gap map](../product-vision-audit-2026-09-28.md#capability-and-gap-map) |
| Knowledge provenance and future sources | Current layers plus connector/participation gaps | [Knowledge](knowledge.md) |
| Internal access, budgets and deployment | Explicit enrollment, admission caps, persistent single-instance service | [Operations](features.md#internal-access-budgets-and-rollout) |

## System flows

```text
Capture meeting note
  microphone -> transcription relay/provider -> transcript events
       -> local session/library -> durable evidence outbox -> backend source
            +-> generated notes -> note index -> original passage discovery
            +-> source-scoped learning -> verified claims + evidence + lifecycle
            +-> background indexing -> lexical/vector source retrieval

Talk to companion (the same main chat during and between recordings)
  question + optional recording/live snapshot + recent chat
       + relevant past evidence -> bounded context -> Luna answer
            -> saved turn + internal evidence/provenance
                 -> release UI: ordinary text; chat evidence inspection in DEBUG

Delete recording
  local library removal + durable deletion sync
       -> remove backend transcript/index/snapshots; tombstone source
       -> preserve eligible learned claims + bounded supporting excerpts
       -> preserve historical answers; remove unavailable source links
       -> new retained-memory answers cannot open the deleted recording
```

These are data dependencies, not a guarantee that background learning has finished when transcription stops. An answer can use original transcript evidence before any derived memory is committed.

## What is not delivered by these maps

Proactive text or spoken participation; calendar/email/message connectors; fresh web retrieval; media import; voice recognition/enrollment; silent continuous recording; Mac computer-audio capture; note editing (generated notes are internally deployed with bounded physical acceptance); side chats; full recording-library synchronization between devices; public account/subscription/distribution operations; explicit memory-erasure UX. These need their own approved slices. Recording remains user-started and internally capped. Do not infer launch readiness from the bounded harness acceptance.

## Keep context useful

Update the affected feature entry when a checkpoint changes behavior, module ownership, a cross-feature contract, verification evidence or a material limitation. Add a lesson only when a failure or decision changes how future work should be done: trigger → cause → guard → evidence. Link evidence instead of copying logs, mutable budget balances, transcripts or secrets. Retain failed evidence, mark superseded guidance, and avoid duplicating canonical policy. No runtime/provider testing is warranted for map-only edits; verify paths, links and factual alignment with code.

## Current consolidation and follow-up

The [simpler memory foundation](../simple-memory-foundation.md) completed its bounded learning/recall checkpoints and [internal rollout](../simple-memory-rollout.md). It reuses existing provenance/lifecycle tables; it is not a new notes-only store or removal of every legacy adapter. Dictation/personality and native UI internal rollout are recorded in [dictation and companion feel](../companion-feel-and-dictation.md) and [UI evidence](../native-experience-ui.md). Next proposed work is the [proactive product gap sequence](../product-vision-audit-2026-09-28.md#proposed-delivery-order). The [Jev gate experiment](../memory-gate-screen.md) is disabled by founder decision.


Current next feature: [proactive contributions from past notes — MVP implementation plan](../proactive-contributions-plan.md). Founder selected this MVP scope; connected sources and outside knowledge remain later full-vision work. The plan and bounded $0.25 / 12-call QA approval are recorded; no proactive implementation or new live verification is claimed.

Local candidate: [proactive foundation](../proactive-foundation.md) implements scheduling, local discovery and model contracts with free replay evidence. No hosted/native integration or live model acceptance yet.
