# Voice Companion

> AI notes that proactively contribute to discussions

An iPhone-first AI note-taking app intended to act like a third smart person in conversations, with Mac support. Proactive text contributions and calendar/email/message context are the agreed product vision, not delivered features. Working name: Voice Companion. The installed internal V1 build records microphone audio through the hosted service, supports locked-screen capture, saves transcripts locally, and answers typed questions during or after a conversation with fixed source references. Recording remains capped at five minutes; speaker labels are best-effort. See the [V1 runbook](docs/v1-runbook.md) for use, setup, quotas and known limits, and [final acceptance](docs/v1-acceptance.md) for evidence. The [V0 runbook](docs/v0-runbook.md) retains local Mac relay instructions and historical scope. This private repository is not a public release.

## Current knowledge and delivery status

Start with the [current product and implementation brief](docs/current-state.md) for decisions, model roles, deployed versus candidate behavior, research outcomes and remaining gates. The [feature map](docs/features/README.md) connects those decisions to code and targeted QA. PR 99 is merged and internally deployed: native dictation/plain-message behavior passed bounded acceptance, and backend v3 personality rollout passed health, prompt-selection and data-preservation checks. The experimental Jev retrieval gate remains disabled.

## Current direction and gap audit

The [full product description](docs/product-source-of-truth.md#full-product-vision--september-28-2026) defines the target. The [implementation audit and proposed build sequence](docs/product-vision-audit-2026-09-28.md) shows what remains, and the [knowledge feature map](docs/features/knowledge.md) separates source evidence, generated notes, memory, model knowledge and future connected context. This is an internal capture/notes/chat foundation; proactive usefulness and repeat use are not yet validated.

## Product source of truth

[Proven, Better, New](docs/product-source-of-truth.md) is the authoritative product definition agreed with the founder. It takes the framework applied by Mark Pincus and Garry Tan to the voice companion idea as its starting point. Granola is the **Proven**.

## Engineering source of truth

[Engineering principles and agent feedback loop](docs/engineering-principles.md) is the canonical authority for how we select tools, design, implement, debug, test, review, and deliver this product. Product direction and engineering principles are complementary sources of truth. Provisional technology choices still require evidence.

## Feature context

Start with the [feature map](docs/features/README.md) to locate implemented behavior, code boundaries, targeted QA and [learned lessons](docs/features/lessons.md). It is a navigation aid; the canonical product and engineering documents retain authority.

The completed narrow notes slice is [transcript-derived notes](docs/recording-notes-plan.md). Its storage and bounded generation are verified; service/native integration is verified locally. The [internal rollout](docs/recording-notes-rollout.md) is deployed with the matching iPhone app installed; the physical-iPhone capture → notes → supporting passage → restart/reopen check has passed.

The [unified memory foundation](docs/simple-memory-foundation.md) is internally deployed: notes and transcripts discover original evidence, Jev ranks it alongside an independent evidence reserve, and a source-scoped background learner maintains verified personal/contextual knowledge. Ten reviewed answer cases and bounded writer QA pass. [Rollout checks](docs/simple-memory-rollout.md) confirm preserved data, healthy workers and authenticated reads; the existing provenance/correction tables remain intentionally shared.

## Knowledge documents

- [Product source of truth and one-liner](docs/product-source-of-truth.md)
- [Founder context and examples](docs/founder-context.md)
- [V0 scope and delivery sequence](docs/v0-scope.md)
- [V0 implementation plan](docs/v0-implementation-plan.md)
- [V1 companion-on-tap plan](docs/v1-implementation-plan.md)
- [Engineering principles and agent feedback loop](docs/engineering-principles.md)
- [Transcription direction and unresolved selection](docs/transcription-direction.md)
- [Synthetic quality screen and remaining acceptance](docs/quality-evaluation.md)
- [Permission, empty-transcript, and microphone-disconnect QA](docs/reliability-edge-cases.md)
- [Initial streaming validation evidence](docs/transcription-validation.md)
- [Source index: videos and X posts](docs/sources/README.md)
- [Video 1 transcript](docs/sources/transcripts/01-pincus-tan.txt)
- [Video 2 transcript](docs/sources/transcripts/02-state-of-startups.txt)
- [Garry Tan X posts supplied by the founder](docs/sources/garry-tan-x-posts.md)
- [Jev research and possible implementation role](docs/jev-research.md)
- [Automatic memory research and proposed harness](docs/automatic-memory-research.md)
- [Automatic memory implementation plan and PR checkpoints](docs/memory-implementation-plan.md)
- [Memory foundation contract and local QA](docs/memory-foundation.md)
- [Automatic learning, provider QA and cost accounting](docs/memory-learning.md)
- [Memory recall acceptance and rollout](docs/memory-recall.md)
- [Personal companion profile plan](docs/personal-profile-plan.md)
- [Companion memory rework plan](docs/memory-rework-plan.md)

Sources and research inform the product; they do not silently change its definition. Implementation proposals remain hypotheses until accepted by the founder.

## Development

See [development commands and foundation QA](docs/development.md). The shared SwiftUI source is in `App/`; `project.yml` generates both native app targets and their UI tests.

## Internal memory checkpoint

The enrolled iPhone can synchronize session evidence and ask with past context. The active recording learner uses Luna extraction, Sol factual entailment and Jev modality/time judgments; older evidence below describes its historical roles. Release chat hides source controls while Notes retains passage navigation. See [acceptance](docs/memory-recall.md#final-physical-acceptance-and-checkpoint-review) for the recovered correction, bounded tests, and known conservative retention miss. That checkpoint’s $0.28 QA allocation is historical and exhausted; use current operator receipts and explicit scope-specific approval before new paid QA. This is an internal trial, not a public release.


## Companion rework rollout

The reviewed memory/main-chat backend is enabled on the existing Render Starter plan. Fresh migration/backup, budget accounting, constrained embedding capacity and authenticated hosted access have been verified. The matching physical iPhone checks now cover capture while chatting, saved-source recall, correction answers, attachment/follow-up and deletion surviving relaunch. The response-wording, named-project location and independent recording-verification fixes are deployed. A bounded [hosted check](docs/verification-rollout.md) verified retention of a fragmented preference and sourced recall; this is not a general memory-accuracy guarantee. See [internal rollout evidence and limits](docs/companion-internal-rollout.md); earlier acceptance documents describe their historical checkpoints.

The [recording-deletion retention checkpoint](docs/retained-recording-memory.md) preserves learned knowledge separately from removed transcripts. Live provider, exact replay and simulator QA pass. The [internal rollout](docs/retained-memory-rollout.md) is deployed with updated native builds; the bounded physical-iPhone deletion, recall and reopen check has passed.


Current next feature: [proactive contributions from past notes — MVP implementation plan](docs/proactive-contributions-plan.md). Founder selected this MVP scope; connected sources and outside knowledge remain later full-vision work. The plan and bounded $0.25 / 12-call QA approval are recorded; no proactive implementation or new live verification is claimed.
