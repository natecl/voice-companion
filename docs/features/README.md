# Feature and context map

> September 30 integration: account/lifecycle PR159–180 merged to main `31b284340fda`. Hosted backend remains `482394e`, schema21; later backend fixes are not deployed by this merge. The physical capture/sign-out check and isolated native network/Apple-provider rejection recovery passed within their recorded scope. Phase 1 remains incomplete. See the [release handoff](../execution/testflight-release-handoff.md).

September 29 direction: [invited social presence](../social-presence-experience.md) supersedes note-taking-led positioning; see the [revised execution phases](../execution/demo-testflight-phases.md). Earlier implementation and rollout claims below remain dated evidence, not fresh runtime inspection.

Start with the [dedicated context map for your feature](context-map.md): current behavior, gaps, dependencies, evidence and next bounded work.

See the [feature verification map](verification-map.md) for each feature’s executable verifier, required real-path evidence, and implementation gaps.

Knowledge foundations were originally audited at main `660e4c7` on September 28; current status was reconciled at `7079427` on September 30 against source and durable QA receipts. This documentation audit did not re-inspect the live service. Read [current state](../current-state.md) and the [product vision gap audit](../product-vision-audit-2026-09-28.md) for the implementation/vision boundary.

> AI notes that proactively contribute to discussions

The current product direction is an iPhone-first invited AI social presence with personal continuity and text contributions, with Mac support. Capture and notes are foundations rather than the consumer category. Calendar, email and messages belong to the full vision; captured notes/conversations are the initial sources. The existing entry points remain **Capture meeting note** and **Talk to companion**. Granola remains the Proven. See the [knowledge map](knowledge.md) for evidence, derived memory and missing source integrations.

## Read in this order

1. [Product source of truth](../product-source-of-truth.md), [engineering principles](../engineering-principles.md), and [historical V0 boundary](../v0-scope.md).
2. The relevant [per-feature context map](context-map.md), then its named implementation files, acceptance verifier and evidence.
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
| Proactive contribution and connected context | Gated implementation and recorded internal experiments; broader participation acceptance incomplete; connectors absent | [Gap map](../product-vision-audit-2026-09-28.md#capability-and-gap-map) |
| Knowledge provenance and future sources | Current layers plus connector/participation gaps | [Knowledge](knowledge.md) |
| Accounts, budgets and deployment | Separate Google/Apple accounts and deletion deployed internally; later lifecycle fixes local; Phase 1 incomplete | [Operations](features.md#internal-access-budgets-and-rollout) |

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

Broadly accepted proactive participation and spoken participation; calendar/email/message connectors; fresh web retrieval; media import; voice recognition/enrollment; silent continuous recording; Mac computer-audio capture; note editing (generated notes are internally deployed with bounded physical acceptance); side chats; full recording-library synchronization between devices; public account/subscription/distribution operations; explicit memory-erasure UX. These need their own approved slices. Recording remains user-started and internally capped. Do not infer launch readiness from the bounded harness acceptance.

## Keep context useful

Update the affected feature entry when a checkpoint changes behavior, module ownership, a cross-feature contract, verification evidence or a material limitation. Add a lesson only when a failure or decision changes how future work should be done: trigger → cause → guard → evidence. Link evidence instead of copying logs, mutable budget balances, transcripts or secrets. Retain failed evidence, mark superseded guidance, and avoid duplicating canonical policy. No runtime/provider testing is warranted for map-only edits; verify paths, links and factual alignment with code.

## Historical foundation and proactive checkpoint ledger

The entries below preserve their dated implementation/experiment history. They do not select the next release phase or attest current flags, quotas or installed builds. Current work finishes Phase 1 account/data lifecycle before pricing, paywall, release preparation and pilot.

The [simpler memory foundation](../simple-memory-foundation.md) completed its bounded learning/recall checkpoints and [internal rollout](../simple-memory-rollout.md). It reuses existing provenance/lifecycle tables; it is not a new notes-only store or removal of every legacy adapter. Dictation/personality and native UI internal rollout are recorded in [dictation and companion feel](../companion-feel-and-dictation.md) and [UI evidence](../native-experience-ui.md). Next proposed work is the [proactive product gap sequence](../product-vision-audit-2026-09-28.md#proposed-delivery-order). The [Jev gate experiment](../memory-gate-screen.md) is disabled by founder decision.


Historical next-feature selection: [proactive contributions from past notes — MVP implementation plan](../proactive-contributions-plan.md). Founder selected this MVP scope; connected sources and outside knowledge remain later full-vision work. The [local native path](../proactive-native.md) and [seven-call model evidence](../proactive-model-screen.md) are verified within their bounded scope; production enablement and physical acceptance remain pending.

Foundation checkpoint: [proactive foundation](../proactive-foundation.md) implements scheduling, local discovery and model contracts with free replay evidence. The subsequent native and model checkpoints below extend that historical boundary.

Local implementation update: [native proactive checkpoint](../proactive-native.md) and [bounded provider screen](../proactive-model-screen.md). These supersede the earlier missing-implementation status for the local proactive path, not the production or public-release status.

Personal proactive evaluation completed locally: v2 selected after 30 real Luna calls (matched decisions v1 9/10, v2 10/10; fresh v2 10/10). The baseline wrongly raised a third party’s sleep issue; v2 stayed silent. All 30 responses replay through the durable service with exact requests; 38 proactive tests pass. Native presentation/draft/quiet/reopen evidence from PR123 remains applicable. Small fictional screen, not physical or broad quality acceptance; hosted deployment remains pending. [Results, limitations and screenshot](../qa/proactive-personal/README.md).

Local readability refinement: proactive paragraph groups now render as ordinary Agent bubbles without dropping content or changing the durable turn. Candidate wording remains unselected; model QA and rollout pending. [Native rendering evidence](../qa/proactive-readability/README.md).

Readability model screen is incomplete: one Luna result retained Cedar details but failed paragraph grouping; the second request returned an undiagnosed HTTPError and the batch stopped without retry. Three planned calls were never sent and remain held in the original ledger. Candidate v3 is not selected; runtime v2 is unchanged. See the proactive-readability QA receipt.

Founder clarified readability means character amount, not a bubble UI change. The PR129 paragraph-grouping renderer is reverted to the prior chat UI. Candidate v3 remains unselected and its grouping direction is superseded. Preserve useful details while simplifying wording; no new model calls or deployment.

Character-length refinement v4 is selected locally after three authorized Luna calls: one useful 135-character reminder preserved corrected times; unknown-subject and resolved-commitment cases stayed silent. Forty-two proactive tests pass, including exact current-prompt service/reopen replay. Soft 120–240-character guidance never overrides necessary content. Phone UI sources are unchanged; no deployment or app installation. The Cedar proactive allowance is fully reserved with no calls remaining. See proactive-readability QA for limits and receipts.

V4 wording is internally deployed at `839d2c9`; health and 28-database/134-table preservation checks pass, without phone/UI changes or quota increases. [Conversation-level validation](../proactive-conversation-validation.md) now has a seven-step free replay exercising real scheduling, retrieval and durable chat beyond cooldown. Forty-three proactive tests pass; model decisions in this new sequence remain synthetic. Five bounded live-model checks are proposed, not yet funded.

[Conversation-level model screen](../proactive-conversation-validation.md#approved-live-model-screen-result) completed: all five predeclared v4 decisions passed (two useful reminders, three silences), with 197/133-character contributions. All five real responses replay through exact-context service validation and persistence; 44 proactive tests pass. This uses predeclared synthetic prior messages, not a closed-loop physical conversation. No runtime/UI change or deployment needed; $0.10/five-call allowance exhausted.

Shared UI baseline (PR154–155 merged): [shared prototype interface](maps/shared-room.md) uses one bundled presentation for browser preview and iPhone, retaining native capabilities. [Evidence and remaining acceptance](../shared-room-ui.md).
