# Current product, implementation and research knowledge

Reconciled against code through `0b286af`, draft [PR 99](https://github.com/natecl/voice-companion/pull/99), and the last verified internal backend rollout `145f4c8` (PRs 95–97). September 27, 2026 UTC / September 26 local. This documentation pass did not redeploy, inspect live runtime state again, run providers or repeat physical QA. Read the [feature map](features/README.md) for code ownership and targeted tests.

The [product source of truth](product-source-of-truth.md) and [engineering principles](engineering-principles.md) are canonical. This brief consolidates their current application; it is not a replacement specification. Earlier plans and failed experiments remain evidence, not current requirements.

## Product and intended feeling

> Granola with an AI that listens alongside you and can join the conversation.

- **Proven:** Granola. This is the reference product, not a claim that we have copied every Granola feature.
- **Better:** faster responses, lower latency and price, and recognizable improvements. These are goals; the implementation has not established a universal comparative advantage.
- **New:** an iPhone-first companion that listens alongside the user during deliberate capture and can participate when addressed. Mac remains supported.

ICP: a curious, ambitious, AI-comfortable person who thinks out loud and wants useful perspective without repeatedly explaining their life. The founder, Mark Pincus and Garry Tan are reference personas, not a restriction to founders or developers. Whole-life context includes relationships, family, pets, interests, study, appointments, work and goals.

The experience should feel like an attentive, quietly sharp friend: personal intelligence on tap, candid and naturally warm, concise when appropriate, willing to disagree. It must not invent familiarity, emotional experiences, identity or capabilities. The companion supports casual conversation, general questions, brainstorming, writing and reflection without a recording; relevant captured context enriches those interactions.

Two actions: **Capture meeting note** and **Talk to companion**. Voice notes and meetings are one source type. One persistent main chat works during and between captures; recordings live in a library. Starting a recording does not create a chat. “Ask about this” attaches a recording. The Manus pill is a layout reference, not a required design system. Muse informs feel, not feature parity or autonomous-agent scope.

## Delivery status and acceptance

| Area | Last verified status | Evidence / remaining boundary |
| --- | --- | --- |
| Microphone → live transcript → saved recording | Internally delivered on Mac/iPhone; locked-screen iPhone capture and interruption preservation exercised | [V1 acceptance](v1-acceptance.md), [edge cases](reliability-edge-cases.md); five-minute internal cap, best-effort speaker labels |
| Persistent companion and contextual Ask | Internally delivered during/after capture, with history and recording attachments | [Companion rollout](companion-internal-rollout.md); ongoing chat is not autonomous action |
| Notes/summary beside transcript | Internally deployed; physical capture → notes → passage → reopen passed | [Notes rollout](recording-notes-rollout.md); generated after terminal capture, no manual note editing, server reads need connectivity |
| Automatic memory, personal context, correction and deletion retention | Internally delivered with bounded verification; unknown speakers stay unknown | [Retention rollout](retained-memory-rollout.md), [verification](verification-rollout.md) |
| Simpler unified memory | Internally deployed at `145f4c8`; schema 18, preserved old rows and ledgers, authenticated reads checked | [Foundation](simple-memory-foundation.md), [rollout](simple-memory-rollout.md); no new physical acceptance claimed by that rollout |
| Composer dictation | PR 99 candidate; local state/shared-feed/UI QA and builds passed | [Input and feel](companion-feel-and-dictation.md); first physical attempt exposed an authorization-callback actor crash; repaired with background-callback regressions, subsequent Stop loss repaired; founder confirmed physical Stop/edit and Clear draft on `da0f39a`; permission/interruption, Send and capture coexistence gates remain |
| v3 personality and plain-message chat | PR 99 candidate; ten live synthetic Luna responses reviewed; local presentation QA passed | [Results](companion-feel-and-dictation.md#approved-ten-response-personality-check); v2 remains last deployed prompt; one response sounded too therapeutic |
| Jev pre-retrieval classifier | Evaluated, never wired into production; founder explicitly left it disabled | [Screen](memory-gate-screen.md); useful classification does not establish net efficiency |

PR 99 is draft and unmerged. Its signed-device build predates the later message-presentation edits; subsequent Mac/iPhone simulator build results do not mean a current candidate was installed on the phone. No public-release readiness claim follows from these checkpoints.

## Current memory harness

```text
Recording transcript (source, owner, revision, time, identity uncertainty)
  +-> Luna generated notes -> revision-bound note search index
  +-> original transcript lexical + local semantic index
  +-> source-scoped background learning
        Luna extraction -> Sol factual support -> Jev modality/time
        -> relationship / identity checks where needed
        -> atomic supported observations + lifecycle + source evidence

Main chat message + bounded recent chat + attached/live snapshot
  +-> when past memory enabled: unified evidence discovery
        notes -> original passages
        transcripts + supported personal references + retained knowledge
        -> deduplicate original evidence
        -> one Jev usefulness ranking + independent two-excerpt reserve
        -> bounded related/correction expansion + integrity checks
  -> Luna answer -> durable chat + internal evidence dependencies
       deployed: source controls
       PR 99 release candidate: plain message, source inspection in DEBUG
```

There is no active intent classifier or retrieval tool chosen by Luna. The harness supplies context; Luna interprets the conversational request. Current live/attached context is separate from past-memory retrieval. The disabled gate experiment would only have skipped past retrieval, never those explicit contexts.

“Thin personal layer” means supported relevant knowledge in the existing store, not a second profile database or a work-only form. Account ownership of a microphone does not identify its speaker. Named people, related people and the user must remain distinct. Voice enrollment and manual speaker labeling are deferred.

Notes aid discovery; they do not replace original evidence or independently verified retained knowledge. The final path is unified notes/transcript recall, not strict notes-only retrieval. The historical `NotesFirstRecall` class and `VOICE_ENABLE_NOTES_RECALL` flag now select unified recall and source-scoped learning. Deterministic overlapping chunks are active in that learner; semantic boundary calls and cross-source duplicate consolidation are disabled for this route. Existing normalized provenance, identity and correction tables remain deliberately shared.

Compatible observations remain source-scoped. Corrections still need supported identity, relation and applicability; an extraction hint alone cannot authorize or suppress them. A newer recording is not automatically a correction. Ambiguous dates remain qualified, and a bare weekday is not automatically next Tuesday. Retirement from current applicability does not prove an event occurred or erase source history.

Ordinary recording deletion removes transcript, notes and source indexes, but can preserve committed knowledge and bounded supporting excerpts. It does not mean “forget everything.” Deleted originals must never open through a broken reference. Old answers depending on original evidence can invalidate; newly generated retained-memory answers can survive. Explicit erasure/account deletion and backup retention remain separate future product work.

## Models and providers by role

| Role | Current implementation / boundary |
| --- | --- |
| Hosted microphone transcription | Grok Voice Transcribe 2.0 (`grok-voice-transcribe-2.0`); best-effort diarization |
| Short composer dictation | Candidate Apple on-device Speech; supported locale required, no silent cloud fallback |
| Main companion responses | GPT-6 Luna, reasoning none, default tier in tested requests; v3 candidate uses 1,000-output-token bound |
| Notes and learning extraction | Luna, separate requests/contracts from chat |
| Independent recording factual entailment | GPT-6 Sol in the enabled source-verification path |
| Recording-subject identity | Luna with the independently evaluated identity configuration; does not infer owner from anonymous speech |
| Modality/time and bounded relationship judgments | Jev; deterministic code retains authority over ownership, revision and commits |
| Candidate evidence ranking | Jev with independent discovery reserve; not a truth verifier or exclusive hard gate |
| Semantic source discovery | Pinned local `BAAI/bge-small-en-v1.5`, FastEmbed CPU; retained deleted-recording claims remain lexical |
| Whether to retrieve memory | No classifier enabled; experimental Jev gate is disabled |

Inspect active hosted branches before changing roles: legacy/personal-text routes differ. Provider names are implementation choices with dated evidence, not permanent guarantees or a reason to preserve a failing role.

## Research and decisions that changed the implementation

| Source / experiment | Durable conclusion | Limits |
| --- | --- | --- |
| [Pincus/Tan source transcripts](sources/README.md) and pasted X posts | Preserve Granola as Proven; conversational intelligence is the New; founder refined it toward mobile consumer life | Transcript errors possible; pasted X publication metadata unknown; vision is not product-market-fit proof |
| [Supermemory-inspired research](automatic-memory-research.md), [audit](memory-system-audit-2026-09-26.md) and article baseline in [engineering principles](engineering-principles.md#memory-system-design-baseline) | Learn outside the answer loop, preserve continuity/evidence, retrieve bounded relevant context, prefer ranking over destructive gates, use Jev for specific measured roles | Supermemory is inspiration, not an integration; implementation still needs behavioral evidence |
| [gbrain comparison](gbrain-comparison.md) | Founder chose to keep and simplify our system for control and product fit | No adoption/migration; an evaluated alternative is not deployed code |
| [Notes discovery comparison](notes-retrieval-comparison.md) | Notes can improve discovery, but omitted summary details require direct transcript fallback | Small candidate-recovery screen, not answer-quality superiority |
| [Matched comparison](matched-recall-comparison.md) | Duplicated summaries/originals and hard usefulness pruning lost disagreement evidence | Failed strict notes-first candidate preserved; do not call it a win because answers were shorter |
| [Unified foundation](simple-memory-foundation.md) | Rank original excerpts once; independent reserve restores frozen disagreement; source-scoped additions simplify learning without removing correction guards | Ten reviewed answer cases, bounded writer QA; not universal memory correctness or a proven billing reduction |
| [Read-only Muse inspection](companion-feel-and-dictation.md#proposed-application-to-our-companion) | Separate stable character, conversational habits and relevant personal context logically | Visible SOUL/IDENTITY/MEMORY files are one instance; nightly-job descriptions not independently verified; no private content copied |
| [Personality screen](companion-feel-and-dictation.md#approved-ten-response-personality-check) | General chat and brainstorming worked without forcing memory; factual safeguards survived tested cases | Ten synthetic responses, no broad benchmark; therapeutic tone remains a taste limitation |
| [Jev gate](memory-gate-screen.md) | Seven safe skips, zero false skips with conservative thresholds across sixteen cases; wrong top label on a follow-up caught by uncertainty | Added 174 ms median; hypothetical 25 model calls vs 16 rankings in the test mix; savings unproven; disabled by decision |

## Operational and engineering knowledge

Use the canonical principles: purposeful small slices, simple modular code, agent-observable behavior, narrow QA at the affected layer, no paid retries, and honest acceptance boundaries. Reuse exact requests/responses only when the actual request matches; a changed prompt or context can invalidate a cache. Never substitute mocked transcription for a claimed real microphone/provider test.

The last verified host uses existing Render Starter, one instance and persistent disk, with automatic deployment off. Back up consistently before migration, preserve usage ledgers and source tombstones, and inspect the serving process rather than a shell's environment. Schema-18-compatible rollback must preserve later data and charges.

Spending permission, runtime/daily quotas, deployment approval and physical readiness are separate. Latest completed screens reserved $0.20 for ten personality calls and $0.08 for sixteen gate calls; both are exhausted. Combined approved envelopes total $5.83, with unchanged $5 runtime envelope. These are historical approvals/reservations, not invoices or permission to reuse another scope's remaining balance. Consult operator receipts for actual usage before a new run; do not include credentials/private recordings in knowledge docs.

## Remaining narrow-release work

1. Finish the explicitly scheduled physical-iPhone dictation check: real recognition, Stop/edit, explicit Send/final words, permission failure and coexistence with meeting capture. Wait for founder readiness before starting. Preflight any required provider allowance separately.
2. Review and finish PR 99 only after its acceptance gates pass; deploy/install the verified candidate with appropriate authorization. Do not merge an incomplete checkpoint just because its documentation is current.
3. Continue product UX work on the agreed narrow foundation. Public distribution, onboarding/account/subscription operations and broader release acceptance remain separate from internal feature completion.

Deferred: TTS, proactive participation, silently always-on capture, Mac system audio, voiceprints, manual speaker labeling, side chats, note editing, full cross-device recording-library sync, autonomous tools and explicit memory-management UX. A mascot or self-editing SOUL/MEMORY files are not an agreed implementation requirement. No additional research or feature is automatically authorized by being listed here.
