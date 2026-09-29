# Current product, implementation and research knowledge

Updated September 28, 2026 against main `660e4c7` for the proactive AI note-taking vision. Last recorded backend rollout: `4dd5b70` (PR104); latest installed native fix: `3954284` (PR106). This audit did not query the live service or rerun physical/provider QA. See [UI rollout evidence](native-experience-ui.md#approved-internal-rollout--september-28-2026).

The [product source of truth](product-source-of-truth.md) and [engineering principles](engineering-principles.md) are canonical. This brief consolidates their current application; it is not a replacement specification. Earlier plans and failed experiments remain evidence, not current requirements.

## Product and intended feeling

> AI notes that proactively contribute to discussions

- **Proven:** Granola. This is the reference product, not a claim that we have copied every Granola feature.
- **Better:** faster responses, lower latency and price, and recognizable improvements. These are goals; the implementation has not established a universal comparative advantage.
- **New:** an iPhone-first AI note-taking app that proactively contributes useful personal context, questions and ideas through text during conversations. Mac remains supported. Proactive participation is the product hypothesis; a local gated implementation now has simulator and bounded model evidence, while production participation remains disabled.

Prior ICP hypothesis (not yet a validated launch segment): a curious, ambitious, AI-comfortable person who thinks out loud and wants useful perspective without repeatedly explaining their life. The founder, Mark Pincus and Garry Tan are reference personas, not a restriction to founders or developers. Whole-life context includes relationships, family, pets, interests, study, appointments, work and goals.

The experience should feel like an attentive, quietly sharp friend: personal intelligence on tap, candid and naturally warm, concise when appropriate, willing to disagree. It must not invent familiarity, emotional experiences, identity or capabilities. The companion supports casual conversation, general questions, brainstorming, writing and reflection without a recording; relevant captured context enriches those interactions.

Two actions: **Capture meeting note** and **Talk to companion**. Voice notes and meetings are one source type. One persistent main chat works during and between captures; recordings live in a library. Starting a recording does not create a chat. “Ask about this” attaches a recording. The Manus pill is a layout reference, not a required design system. Muse informs feel, not feature parity or autonomous-agent scope.

## Current product vision and gaps

The [full product description](product-source-of-truth.md#full-product-vision--september-28-2026) includes calendar, email and messages as context sources. Initial sources remain deliberately captured notes/conversations. Existing general chat supports the experience, but current positioning is note-taking-led rather than a generic messaging assistant. The core hypothesis is that useful unsolicited contributions earn repeated voluntary use. A first exclusive audience, contribution policy and connector providers remain unresolved.

The [implementation audit](product-vision-audit-2026-09-28.md) identifies missing proactive trigger/context/decision/delivery, connected sources, fresh outside-information retrieval, realistic recording duration and public account/data operations. The [knowledge map](features/knowledge.md) separates current evidence/memory layers from proposed additions. No runtime changes follow from this documentation revision.

## Internal UI

The [native experience UI checkpoint](native-experience-ui.md) implements the approved visual direction. Agent is the primary/default screen and first top tab; Notes is the secondary recording library. Notes now uses a secondary-page header with Back to Agent, a Notes title pill and search/options. Both share a single-row composer with an upright paperclip, inline text and mic/send control. Drafts wrap naturally up to five visible lines, then scroll. The recording bar has a View label and separate Stop control. Saved notes and account use full pages; live transcription uses a sheet. Authentication and subscription screens remain previews. The UI rollout and subsequent rounded-note long-press fix (source `3954284`) are installed and launched on the physical iPhone. Installation is verified; full physical behavioral acceptance and Mac UI automation remain pending. Actual screenshots are in the [gallery](qa/native-experience/index.html).

## Delivery status and acceptance

| Area | Last verified status | Evidence / remaining boundary |
| --- | --- | --- |
| Microphone → live transcript → saved recording | Internally delivered on Mac/iPhone; locked-screen iPhone capture and interruption preservation exercised | [V1 acceptance](v1-acceptance.md), [edge cases](reliability-edge-cases.md); five-minute internal cap, best-effort speaker labels |
| Persistent companion and contextual Ask | Internally delivered during/after capture, with history and recording attachments | [Companion rollout](companion-internal-rollout.md); ongoing chat is not autonomous action |
| Notes/summary beside transcript | Internally deployed; physical capture → notes → passage → reopen passed | [Notes rollout](recording-notes-rollout.md); generated after terminal capture, no manual note editing, server reads need connectivity |
| Automatic memory, personal context, correction and deletion retention | Internally delivered with bounded verification; unknown speakers stay unknown | [Retention rollout](retained-memory-rollout.md), [verification](verification-rollout.md) |
| Simpler unified memory | Internally deployed at `145f4c8`; schema 18, preserved old rows and ledgers, authenticated reads checked | [Foundation](simple-memory-foundation.md), [rollout](simple-memory-rollout.md); no new physical acceptance claimed by that rollout |
| Composer dictation | PR 99 bounded native acceptance complete; candidate installed on physical iPhone | [Input and feel](companion-feel-and-dictation.md); first physical attempt exposed an authorization-callback actor crash; repaired with background-callback regressions, subsequent Stop loss repaired; founder confirmed physical Stop/edit and Clear draft on `da0f39a`; subsequent permission/background-interruption, explicit Send and private capture-pause/resume checks passed (details and evidence limits in the linked acceptance) |
| v3 personality and plain-message chat | Internally deployed; ten live synthetic Luna responses reviewed; local presentation QA passed | [Results](companion-feel-and-dictation.md#approved-ten-response-personality-check); v3 is internally deployed; one response sounded too therapeutic |
| Jev pre-retrieval classifier | Evaluated, never wired into production; founder explicitly left it disabled | [Screen](memory-gate-screen.md); useful classification does not establish net efficiency |

PR 99 completed its bounded acceptance and final review. The signed native candidate is installed. Backend prompt v3 is now internally deployed; no public-release readiness claim follows from these checkpoints.

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
       release: plain message, source inspection in DEBUG
```

There is no active intent classifier or retrieval tool chosen by Luna. The harness supplies context; Luna interprets the conversational request. Current live/attached context is separate from past-memory retrieval. The disabled gate experiment would only have skipped past retrieval, never those explicit contexts.

“Thin personal layer” means supported relevant knowledge in the existing store, not a second profile database or a work-only form. Account ownership of a microphone does not identify its speaker. Named people, related people and the user must remain distinct. Voice enrollment and manual speaker labeling are deferred.

Notes aid discovery; they do not replace original evidence or independently verified retained knowledge. The final path is unified notes/transcript recall, not strict notes-only retrieval. The historical `NotesFirstRecall` class and `VOICE_ENABLE_NOTES_RECALL` flag now select unified recall and source-scoped learning. Deterministic overlapping chunks are active in that learner; semantic boundary calls and cross-source duplicate consolidation are disabled for this route. Existing normalized provenance, identity and correction tables remain deliberately shared.

Compatible observations remain source-scoped. Corrections still need supported identity, relation and applicability; an extraction hint alone cannot authorize or suppress them. A newer recording is not automatically a correction. Ambiguous dates remain qualified, and a bare weekday is not automatically next Tuesday. Retirement from current applicability does not prove an event occurred or erase source history.

Ordinary recording deletion removes transcript, notes and source indexes, but can preserve committed knowledge and bounded supporting excerpts. It does not mean “forget everything.” Deleted originals must never open through a broken reference. Ordinary recording deletion preserves old answers and removes unavailable source links; source revisions remain a distinct invalidation contract. Newly generated retained-memory answers can survive. Explicit erasure/account deletion and backup retention remain separate future product work.

## Models and providers by role

| Role | Current implementation / boundary |
| --- | --- |
| Hosted microphone transcription | Grok Voice Transcribe 2.0 (`grok-voice-transcribe-2.0`); best-effort diarization |
| Short composer dictation | Apple on-device Speech; supported locale required, no silent cloud fallback |
| Main companion responses | GPT-6 Luna, reasoning none, default tier in tested requests; v3 uses 1,000-output-token bound |
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

PR 99 is merged and personality v3 is internally deployed. No further paid transcription run is needed for accepted paths. Continue product UX work on the agreed narrow foundation. Public distribution, onboarding/account/subscription operations and broader release acceptance remain separate from internal feature completion.

Core remaining product work: production acceptance/enablement of the local proactive path, calendar/email/message context and fresh outside-information retrieval. Separately deferred: TTS, silently always-on capture, Mac system audio, voiceprints, manual speaker labeling, side chats, note editing, full cross-device recording-library sync, autonomous tools and explicit memory-management UX. A mascot or self-editing SOUL/MEMORY files are not an agreed implementation requirement. No additional research or feature is automatically authorized by being listed here.


### Private composer dictation refinement — September 27

Founder-approved behavior: pause meeting audio while dictation captures the companion message, visibly indicate it, then resume automatically. The question is excluded from meeting transcripts/notes; other simultaneous speech is also omitted. Candidate routing uses same-length silence for the meeting stream and original audio for on-device dictation, preserving session timestamps. Prior physical omission was not deliberate routing and does not verify this change. See [dictation evidence](companion-feel-and-dictation.md). The bounded physical pause/exclusion/resume check now passes: the founder saw the paused indicator; direct iPhone Mirroring inspection confirmed both meeting statements in the transcript and generated notes, and the private arithmetic question/answer only in chat. Stop/edit/Clear also have prior founder-confirmed physical evidence. The physical background-interruption check also passes by explicit founder confirmation: editable dictated text remains, the stopped notice appears, and nothing sends. Permission-denied UX subsequently passed with an empty composer and no crash; access was restored. Final PR review and focused tests passed. The founder approved an additional $0.05 for this one run; PR 101 deployed explicit budget compatibility, raising the runtime ceiling to $5.05 and combined approved envelopes to $5.88. This supersedes the earlier budget totals above; allowances are not invoices or authorization for repeat runs.

Native UI follow-up (September 28): active composer dictation now offers trash, timer, PCM waveform and Send; existing typed text is preserved and appended before a successful send. Notices are dismissible, and profile/search outlines are stronger. Focused native tests and simulator behaviors pass; physical dictation/visual acceptance remains distinct. See [UI evidence](native-experience-ui.md#dictation-composer-and-dismissible-notices--september-28).

Latest UI refinement: paperclip menu contains Attach note, Use past memory and Refresh chat; Dictate message and Clear draft are removed. Refresh retains the visible conversation while loading and shows explicit completion feedback. Notice dismissal fades/collapses with Reduce Motion support. Agent replies use the founder's light-gray rounded bubble reference. See [UI follow-up evidence](native-experience-ui.md#paperclip-menu-and-refresh-follow-up).


September 28 local UI checkpoint: Notes swipe Delete and long-press Share/Delete verified with synthetic simulator notes. Deletion now preserves prior chat answers in the backend candidate, removing unavailable links without presenting a source-deleted notice. This historical pending status is superseded by the PR104 rollout below; existing erased answers are not recoverable. See [UI QA](native-experience-ui.md#note-actions-and-preserved-chat--september-28).


September 28 internal UI rollout complete: PR104 backend is live at `4dd5b70`; matching native app installed in place and launched on the founder’s iPhone. Includes welcome-message onboarding, stacked note cards with icon-only swipe actions, shared composer/dictation, refined motion, and preserved historical replies after note deletion. Verified all 20 databases/106 tables unchanged and no new paid usage. Physical feel/performance is not newly claimed. See [rollout receipt](native-experience-ui.md#approved-internal-rollout--september-28-2026).


Current next feature: [proactive contributions from past notes — MVP implementation plan](proactive-contributions-plan.md). Founder selected this MVP scope; connected sources and outside knowledge remain later full-vision work. The [local native checkpoint](proactive-native.md) is implemented and simulator-verified, with seven bounded model calls including three retrieved-evidence silence cases. The [model evidence](proactive-model-screen.md) records $0.11 conservative reservations under the $0.25 / 12-call grant. Production enablement, broader quality and physical acceptance remain pending.

September 28 phone-test preparation: [bounded proactive test](proactive-phone-test.md) scopes the next physical check to two video excerpts, Luna only and five remaining feature-QA calls, with a separately approved $0.09 recording/notes extension. Preparation is not physical acceptance or broad rollout.

The bounded proactive phone setup is now internally deployed (PR 115), with a signed real-audio Debug build installed and launched on the iPhone 16 Pro. The account-scoped gate expires September 29 around 13:25 Eastern. Allowances are provisioned; no new paid calls/captures have run. See [rollout evidence](proactive-phone-test.md#internal-setup-deployed). Physical acceptance awaits founder readiness.

Personal proactive evaluation completed locally: v2 selected after 30 real Luna calls (matched decisions v1 9/10, v2 10/10; fresh v2 10/10). The baseline wrongly raised a third party’s sleep issue; v2 stayed silent. All 30 responses replay through the durable service with exact requests; 38 proactive tests pass. Native presentation/draft/quiet/reopen evidence from PR123 remains applicable. Small fictional screen, not physical or broad quality acceptance; hosted deployment remains pending. [Results, limitations and screenshot](qa/proactive-personal/README.md).

September 28 authorized backend rollout: PR124 commit `734bb3d` is now hosted and v2 prompt selection verified. Health passed; 24 databases / 112 tables retained identical rows and usage. Continuous-speech repair is deployed too. Normal-phone proactive participation remains gated, with no new allowance or phone installation. [Rollout evidence](qa/proactive-personal/README.md#authorized-backend-rollout--september-28).

Cedar solo phone test setup is deployed at PR126 `ce2dfec`: fictional prior seeded without learning, one live capture/one generated note/six proactive calls funded within $0.17, expiring account gate active, compatible phone app launched with test enabled. Zero paid calls during setup; founder readiness still pending. [Setup and script](qa/proactive-personal/README.md#cedar-solo-phone-pilot-setup).

Cedar physical pilot passed its narrow useful-reminder check: founder saw one relevant past-note interjection; hosted evidence confirms completed capture, saved main-chat turn around 19 seconds after start, ready notes, no personal-learning job, and $0.065 reserved usage. Recording ended before the cooldown, so post-acknowledgment silence and longer-session usefulness remain untested. [Observed result and limits](qa/proactive-personal/README.md#physical-cedar-pilot-result--september-28).

Local proactive readability checkpoint: explicit paragraphs render as grouped ordinary Agent bubbles with full content and one durable turn. Simulator delivery/draft/quiet/relaunch and core text checks pass. Candidate v3 wording is unselected and awaits separately authorized model QA; hosted v2 and phone installation are unchanged. [Evidence and screenshot](qa/proactive-readability/README.md).
