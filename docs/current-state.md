# Current product, implementation and research knowledge

Updated September 30 after account PR159–180 integration to main `31b284340fda`. Source integration and deployment remain separate. The [merge review](qa/account-merge-review/README.md) records fresh targeted checks and the physical/simulator follow-ups; runtime facts below are last recorded, not a new health attestation.

The [product source of truth](product-source-of-truth.md) and [engineering principles](engineering-principles.md) govern decisions. Use the [TestFlight handoff](execution/testflight-release-handoff.md) for execution order and the [feature maps](features/README.md) for code, contracts and verification routes.

## Product and approved experience

> AI notes that proactively contribute to discussions

The agreed one-liner is retained pending a selected replacement. Current positioning is an **iPhone-first invited AI social presence**: a third participant deliberately brought into a conversation. Granola remains Proven; speed, latency and price improvements are Better goals; useful personal participation is the New hypothesis. Mac remains supported. Repeated voluntary use and broad proactive usefulness are not validated.

One persistent companion chat and a recording library share deliberately captured context. Starting capture does not create a new chat. Capture is internally capped at five minutes; numeric speaker labels are best-effort, never verified identity. Notes and remembered context supply continuity. Calendar/email/messages, fresh outside-information retrieval, voice replies and silently always-on capture are not delivered.

The shared local HTML/CSS/JavaScript companion-room interface in WKWebView is the current iPhone design source of truth. Native controllers retain capture, dictation, storage and credentials. Google appears above Apple; existing components, motion, feedback and haptics must be reused. The earlier separate SwiftUI Agent/Notes mockups are historical. The temporary mascot is not cleared for distribution; the founder will supply the final asset.

## Delivery identities and boundaries

| Layer | Last recorded state | What it does not establish |
| --- | --- | --- |
| Merged main | `31b284340fda`, account/lifecycle PR159–180 including knowledge reconciliation | Full Phase 1 or TestFlight acceptance |
| Reviewed integration source | `afe114a`, exact file tree retained by the account merge | Deployment of later backend fixes |
| Hosted backend | `482394e23dd081cc4a9a1e67ef79f7f4aa3b676e`, deployment `dep-daukpurtqb8s73boufmg`, schema21; prior account backend plus only bounded capture-budget compatibility | Later companion-session and managed backup/restore fixes are not deployed |
| Founder iPhone | Native `1da7e188`, development-signed Release, Google signed in; real capture/profile sign-out, Apple isolation and Google return/relaunch recorded | Physical account deletion and full Release acceptance |
| Isolated simulator | Real Google/Apple lifecycle; latest Apple recovery binary pinned in its receipt | Physical-device or two-independent-person acceptance |
| App Store Connect | Ellis: AI Notetaker; app6817680460; bundle `ai.voicecompanion.phone`; SKU `ellis-iphone-001`; version1.0 Prepare for Submission | No uploaded TestFlight build, review submission or invited testers |

See [live cutover](qa/founder-migration/live-cutover.json), [physical account switching](qa/founder-migration/physical-account-switch.json), [Apple recovery](qa/account-lifecycle/apple-fresh-proof-recovery.json) and the [handoff](execution/testflight-release-handoff.md). Do not infer deployment from branch ancestry or a merged PR.

## Feature state and evidence

| Area | Implemented / bounded evidence | Remaining boundary |
| --- | --- | --- |
| Capture, transcript, saved recordings | Internal Mac/iPhone flow, locked-screen capture and interruption evidence; [V1 acceptance](v1-acceptance.md), [edge cases](reliability-edge-cases.md) | Five-minute cap, best-effort attribution; physical capture/sign-out passed; broader device release checks remain |
| Shared room and note cache | Merged shared UI/cache integration, offline relaunch, revision/deletion invalidation and touch repair; [integration evidence](qa/phase-integration/README.md) | No redesign; account-specific evidence must be read with lifecycle receipts |
| Notes | Transcript-derived generation, passage navigation and bounded physical reopen; [rollout](recording-notes-rollout.md) | No note editing or full cross-device recording-library sync |
| Main chat and dictation | Persistent ordinary messages, attachments/follow-ups, private composer dictation with bounded physical pause/exclusion/resume; [evidence](companion-feel-and-dictation.md) | Source provenance stays internal in release chat; no side chats or TTS |
| Memory and retrieval | Source-scoped learning, supported personal context, correction/time lifecycle, unified notes/transcript recall; [foundation](simple-memory-foundation.md), [rollout](simple-memory-rollout.md) | Bounded acceptance, no general accuracy guarantee or voice identity |
| Ordinary recording deletion | Removes transcript and unavailable source links, retains eligible learned knowledge and existing chat answers; [retention](retained-memory-rollout.md), [UI rollout](native-experience-ui.md) | Distinct from complete account deletion; erased historical answers are not reconstructed |
| Google/Apple accounts | Separate persistent accounts; real enrollment, rotation, populated provider switching/deletion and re-enrollment in simulator; [lifecycle](qa/account-lifecycle/README.md) | Two provider identities belonging to one person do not prove independent-human isolation |
| Automatic refresh and recovery | Native normal-threshold Google/Apple rotation, fresh-proof Google/Apple deletion recovery, persisted restart; [Google recovery](qa/account-lifecycle/automated-google-recovery.json), [Apple refresh](qa/account-lifecycle/native-apple-automatic-refresh.json), [Apple recovery](qa/account-lifecycle/apple-fresh-proof-recovery.json) | Apple recovery completion transition is founder-reported; native network and staged real Apple rejection recovery passed; physical and broader provider-specific lifecycle gates remain |
| Founder migration | Server binding and phone file migration preserved original recordings/outbox and budgets; physical content/relaunch accepted | Explicit one-time Google migration, not account linking; never replay it |
| Revoked-session/capture fixes | Merged code blocks companion sends after revocation and late recording writes after teardown; [review](qa/account-isolation-review/README.md) | Companion fix remains undeployed; capture fix installed and physically exercised |
| Backup/restore | Merged managed snapshots, explicit expiry, online file pruning and deletion-aware offline restore preparation; [retention](qa/managed-backups/README.md), [restore](qa/backup-restore/README.md) | No production duration/enablement, restore activation, or complete historical/off-host/provider-snapshot policy |
| Proactive contribution | Past-note pipeline, durable ordinary chat delivery, controls and bounded model/physical pilot evidence; [Cedar pilot](qa/proactive-personal/README.md), [conversation checks](proactive-conversation-validation.md) | Hosted default v4 remains gated. Later v5–v10 wording trials did not earn selection; expired QA gates are not ongoing rollout authorization |
| Plans, subscriptions, distribution | Freemium plus subscription agreed; Apple app record exists | Prices/allowances/pilot undecided; server plans, real StoreKit paywall and TestFlight release are unfinished |

## Knowledge and model roles

Recording transcripts are source material, not instructions. Generated notes are discovery aids, not independent evidence. Original passages, owner/revision/time and uncertain identity ground verified memories. Ordinary deletion can retain eligible learned knowledge; account erasure has a stronger separate boundary.

The enabled source-scoped learner uses Luna extraction, Sol factual entailment and Jev modality/time judgments, with bounded identity/relationship checks and atomic provenance writes. Legacy/personal-text routes differ. Unified recall discovers original evidence through notes/transcript indexes, ranks it once with Jev and preserves an independent evidence reserve. Luna answers using bounded past evidence, current/attached snapshots and recent chat. The experimental Jev pre-retrieval gate remains disabled by founder decision. [Knowledge map](features/knowledge.md).

The companion v3 personality is internally delivered. Proactive v4 is the selected hosted default; grouped-message capability and candidate wording do not imply that later prompts are accepted. [Conversational trials](proactive-conversational-wording.md) preserve failures and exhausted grants. Exact-request replay proves the exercised mechanics, not fresh model quality or a closed-loop conversation.

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

## Current execution and operating rules

Finish **Phase 1 accounts/data lifecycle**, then Phase 2 selected plans/limits, Phase 3 subscriptions/paywall, Phase 4 Release preparation and Phase 5 pilot. Preserve the current UI. Do not restart completed migration or provider enrollment checks just because a new agent takes over.

Remaining Phase 1 gates: Google-specific negative refresh coverage and final provider-revocation contract; two independent humans' isolation; physical deletion/failure/relaunch; retention duration, production enablement and restore/historical-copy handling. Candidate tests and one-person Google/Apple switching do not waive these gates. The [handoff](execution/testflight-release-handoff.md) owns the detailed remaining work.

The founder authorizes proactive implementation, internal preparation and verified checkpoint merges, with Astra-low execution workers and primary review. Required decisions, credentials, legal acceptance and physical-test readiness remain human gates. Agent-operated simulator steps use native XCTest; passwords/security challenges stay with the founder. No production reset, arbitrary tester invitation or UI redesign is implied.

The separate [TestFlight provider allowance](execution/testflight-provider-budget.md) is $5, with $0.02 reserved for one interrupted physical transcription attempt; billed cost is not yet available. Historical grants remain historical and cannot be reused implicitly. OAuth lifecycle checks and local fixtures did not consume model allowance. Runtime quotas and spending approval are distinct; no automatic paid retries.

Use coordinated backups and current authoritative deletion/spending state; never restore old ledgers over resumed activity. Merged restore preparation deliberately refuses stale application content and does not activate a restore. Inspect live configuration before any rollout rather than treating this recorded snapshot as runtime truth.

## Reading historical documents

Dated plans, experiments and rollout receipts retain their original evidence, failures and limits. A historical “pending” or “deployed” statement applies to that checkpoint, not the entire current product. Start here and in the handoff, then follow the relevant feature map. The [September 28 gap audit](product-vision-audit-2026-09-28.md) is a historical comparison; the September 29 invited-social-presence direction and September 30 account decisions supersede its old next-work sequence.
