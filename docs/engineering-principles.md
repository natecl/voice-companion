# Engineering direction and agent feedback loop

Status: Canonical engineering source of truth, explicitly designated by the founder September 24, 2026. Swift/native controllers and the approved shared WKWebView iPhone interface are implemented; the dated foundation sections below record how this direction was established. See development.md and current-state.md for bounded verification and current delivery identities. A functioning provider integration does not imply a universal quality benchmark.

## Authority and application

This document is the canonical source of truth for how we engineer this product. Apply it to stack selection, architecture, implementation, tooling, debugging, testing, review, and delivery. The [product source of truth](product-source-of-truth.md) defines what we are building; this document defines how we build and verify it. The [V0 scope](v0-scope.md) defines the current release boundary.

All implementation plans and changes must follow these principles. Supporting research and vendor recommendations do not silently override them. A later explicit founder decision may revise them; record that revision here and update dependent guidance. If requirements conflict or a material departure is necessary, make the conflict explicit rather than treating an exception as the new standard. Routine implementation choices within these principles do not require repeated approval.

Concrete technology choices below retain their stated provisional status. Canonical principles do not turn an untested stack or provider into a validated decision.

## Shared native codebase

The September 29 shared-prototype revision below supersedes independent SwiftUI recreation of the iPhone companion room. Native capture, dictation, storage/security and Mac support retain their boundaries. Historical technology-evaluation statements below do not mean the current stack is unimplemented.

Use Swift and SwiftUI for native Mac and iPhone apps in one repository. Share product logic and suitable views; keep platform-specific audio permissions, audio lifecycle, interruptions, and window behavior behind clear boundaries. One codebase produces two app builds; it does not automatically provide cross-device data synchronization.

Apple documents sharing code and configuration through multiplatform app targets: [multiplatform development](https://developer.apple.com/videos/play/wwdc2022/110371/), [audio frameworks](https://developer.apple.com/documentation/avfoundation/audio-playback-recording-and-processing).

Build one complete flow on Mac, then immediately bring the same flow to iPhone and verify it on a physical device. Both platforms remain in V0. Exact target organization, storage implementation, backend stack, and minimum OS versions require validation.

## Module boundaries

```text
Platform audio capture
          |
Transcription provider adapter
          |
Shared transcript and speaker model
          |
          +--> Transcript UI
          +--> Session storage
          +--> Future notes, Q&A, and context features
```

- Audio capture: microphone now; Mac computer audio later. Preserve room for multiple sources.
- Provider adapter: connection lifecycle and translation of vendor responses into our own transcript format. Avoid exposing vendor-specific payloads throughout the app.
- Shared session/transcript model: timestamps, speaker labels, partial and finalized results, revisions, and recording state.
- Presentation: shared SwiftUI where appropriate, with native platform behavior.
- Storage: save and reopen transcripts behind an explicit interface. Cross-device sync and audio retention policy are separate unresolved decisions.
- Backend boundary: authorize provider access, protect credentials, and enforce usage limits. Validate whether the selected provider supports short-lived client credentials or requires a relay; do not embed long-lived provider secrets in apps.

Start with clear boundaries within one codebase. Do not create speculative services or elaborate plugin frameworks before V0 needs them. Future features should consume shared transcript data rather than require changes across the capture pipeline.

## Stack selection standard

**Every important behavior should be runnable, observable, and verifiable by an agent, with human involvement reserved for judgment, meaningful risk, and decisions the evidence cannot resolve.**

Research tools for their ability to close the loop, alongside product quality:

| Criterion | Required evidence |
| --- | --- |
| Control | CLI access to build, run, test, and configure |
| Observability | Accessible structured logs, actionable errors, and inspectable state |
| Verification | Automated checks, simulator access, and actual UI inspection |
| Documentation | Current official docs, examples, and explicit API contracts |
| Reproducibility | Predictable dependencies and repeatable setup |
| Modularity | Independently exercisable components and replaceable integrations |

Swift/SwiftUI remains a working direction, not a claim that this tooling evaluation has already passed. Validate build, simulator/device, UI inspection, and debugging workflows with a small working slice before locking in surrounding tools.

## Repeatable feedback loop

```text
Change -> Run -> Observe -> Verify
   ^                          |
   +------ Fix failures ------+
                              |
                    Human judgment when needed
```

Provide one-command builds and relevant checks. Replay saved, consented or synthetic audio fixtures through the pipeline to reproduce failures without asking the founder to speak each time. Provide simulated transcript streams, including revisions and speaker changes, for interface work without paid API calls.

Measure transcription accuracy, speaker attribution, latency, and failures on representative inputs. Make recording, connection, and transcript-update states observable without logging private conversation content by default.

When a reproducible bug is fixed, add meaningful regression coverage where appropriate. Each resolved failure should leave improved tests, diagnostics, or documentation. This is the intended self-improving loop; it is not permission to change product goals, weaken checks, or ship unreviewed risky changes.

Agents should run commands, inspect errors, reproduce problems, and verify routine changes without making the founder a manual relay. Human input remains valuable for product judgment, ambiguous tradeoffs, material risk, and real-world quality. Automated checks alone do not establish microphone quality, battery impact, or whether the experience feels good. Use targeted real-device and human checks for those questions.

## Pull request checkpoints

Founder decision: open a pull request after each completed phase or meaningful checkpoint. Keep each PR focused and independently reviewable, describing the resulting behavior, verification evidence, and known limitations. Attach created PRs to the working task.

Use branches and commits to preserve clear checkpoints. Record the tested commit and checks in the PR so a later regression can be traced to the change that introduced it. Once merged, a checkpoint is part of main's history. Use a revert for a faulty merged change; use rebasing to incorporate newer base-branch work, not as a substitute for rollback. Preserve shared history rather than rewriting it to hide a regression.

The founder explicitly authorizes the workflow: branch -> implement -> test and inspect -> open PR -> review -> merge -> next phase. Agents may merge verified checkpoints without asking again when relevant checks, behavioral QA, and review are complete. This supersedes the earlier requirement for separate merge authorization. Follow repository protections; do not bypass required checks. Surface material unresolved issues or product decisions instead of merging a checkpoint that has not met its acceptance criteria. This authorization does not extend to public release or deployment.

Start each new phase from the latest verified main. If work must continue before a dependency merges, identify that dependency explicitly.

## Behavioral QA at every checkpoint

Passing automated tests alone is not proof that a phase was successfully implemented. Define the expected observable result before implementation, then actually run the behavior delivered by that checkpoint and inspect its output. Automated end-to-end execution is welcome; the requirement is real execution and evidence, not mandatory manual intervention.

Match QA to the claim:

- Development foundation: build and launch the actual apps, inspect the rendered UI, and collect logs.
- Simulated transcript flow: run the simulated stream through the actual app, inspect text revisions and speaker changes, then save, relaunch, and reopen. Clearly label this as simulated-input evidence.
- Real transcription integration: send actual audio through the real provider integration, capture and inspect the resulting transcript, and assess speaker attribution and latency against the reference input. A mocked response does not satisfy this checkpoint.
- Microphone integration: exercise actual microphone capture through the app to the transcript UI and saved session. Injected audio alone does not prove the microphone path.
- iPhone delivery: demonstrate the complete flow on a physical iPhone, including relevant interruptions. Simulator evidence alone does not satisfy device acceptance.

Each PR must report the tested commit, environment/device, input and provenance, reproducible steps or commands, expected result, observed result, and evidence references. Use consented or synthetic fixtures and sanitized logs; do not commit private conversations or secrets as QA evidence. Inspect relevant failure paths as well as the successful path.

If credentials, hardware, or another dependency prevents required QA, mark the checkpoint unverified and report the blocker. Do not claim completion or merge it as a verified checkpoint. Supporting completed work may form a narrower checkpoint only when its limited scope is explicit; it must not be presented as proof of the blocked behavior.

Review the diff and QA evidence before merging. Fix failures and rerun affected checks; ensure the evidence applies to the final implementation commit, repeating checks when changes invalidate it. Preserve meaningful regression coverage and document any residual limitations that do not violate acceptance criteria.

## Fast iteration on verified foundations

Founder priority: move very quickly while maintaining a high-quality, understandable foundation. Achieve speed through small scope, short feedback loops, reusable verification, and clear module boundaries. Do not trade away behavioral QA or build successive features on unexplained failures.

Each slice must have explicit acceptance criteria, a complete working path within its stated scope, appropriate failure handling, inspectable behavior, and reproducible verification. Complete means complete for that bounded slice, not feature-complete for the whole product or a guarantee of zero defects. Document residual limitations honestly; do not relabel a failed requirement as a limitation to pass a checkpoint.

Before merging, verify the delivered behavior, review code and evidence, address acceptance failures and material safety issues, and confirm relevant existing behavior still works. Scale checks to the change and its impact: avoid both superficial tests and broad repeated checks that add no evidence. Keep required checks and protections intact.

When a regression appears, reproduce it against a known input, compare with the last verified checkpoint, and inspect logs and state to isolate its cause. Correct or revert the faulty change, verify the fix, and add meaningful regression protection before dependent work compounds the problem. Do not conceal failures with unexplained retries, swallowed errors, or weakened assertions.

Keep PRs small enough to understand and diagnose. Record decisions and verification evidence as part of each slice, not as deferred cleanup. Prefer simple implementations and explicit contracts; add abstraction only when it serves an actual boundary or requirement. The goal is a succession of working, tested increments that makes the next increment faster and easier to debug.

## Stop for founder-dependent blockers

Explicit founder instruction: when progress requires the founder's permission, access, approval, or decision, stop and wait for the founder to unblock it. State the exact blocker, the action needed, and why it is required. Do not continue into other work while waiting, bypass the gate, repeatedly retry it, or substitute a different implementation or mocked evidence to appear unblocked. Resume only after the founder responds and the required prerequisite is actually satisfied. For manual QA that needs the founder, describe the steps and wait for an explicit ready response before launching the timed check, starting recording, or triggering the event. Do not treat approval of the overall work as readiness for a live test.

Examples include granting microphone permission, providing provider credentials, authorizing device/signing access, or resolving a material product decision. Computer/screen-audio permission is relevant only to later authorized computer-audio work, not microphone-only V0. Do not request permissions that the current slice does not need.

Distinguish founder-dependent blockers from ordinary engineering failures: agents should still diagnose and fix routine code, build, and test failures autonomously within existing authorization. The checkpoint merge authorization remains in force after the required QA and review; it does not authorize bypassing OS permission prompts or other founder-dependent gates.

## Cost-efficient validation

Founder instruction: keep paid API runs purposeful and bounded. Use short fixtures, explicit duration caps and timeouts, no automatic paid retries, and record run counts and estimated usage. Reuse captured synthetic-fixture responses for local development. Repeat paid calls only to answer an unresolved integration or quality question or verify a relevant change. Cost controls must not replace required real-path QA with mocked evidence. Estimates are not invoices; distinguish estimated cost from verified billing.

Founder clarification: do not sacrifice quality to fit a QA allowance. Keep acceptance criteria and necessary validation intact. If the remaining allowance cannot cover required evidence, present a specific additional request and wait for approval; optimize through focused fixtures and replay rather than skipped gates.

## Targeted QA and debugging

Founder instruction: isolate the affected layer and use the narrowest realistic input that reproduces the problem. For transcript rendering or revision bugs, replay saved transcript events through the actual UI; do not call speech-to-text again when that boundary is unchanged. For parsing bugs, replay recorded provider payloads. Exercise the real microphone or paid provider when the changed behavior or unresolved question requires that path.

First reproduce the failure, then run focused verification of the fix and relevant neighboring contracts. Broaden checks based on changed interfaces, shared state, failure risk, or evidence of wider impact, not habit. Reuse prior evidence only where its code, configuration, and dependencies remain applicable. A local fix does not require rerunning every paid end-to-end scenario; a new or changed integration still requires real-path evidence before its checkpoint is complete.

Record what was checked, why those checks cover the change, and which existing evidence remains valid. Optimize time, cost, and feedback speed while retaining meaningful acceptance criteria.

## Purposeful, outcome-driven work

Founder instruction: move as fast as possible in the right direction. Keep engineering, architecture, coding, debugging, and QA purposeful and goal-oriented. Before a meaningful action, identify the outcome it advances, the uncertainty it resolves, and the evidence that will establish success. Choose the smallest action that meaningfully advances that outcome without weakening quality.

Avoid speculative abstractions, unrelated cleanup, repeated investigations, and checks that add no evidence. During debugging, state the failure and a testable hypothesis, isolate its cause, and verify the correction. Record consequential decisions and their rationale; do not turn routine work into documentation overhead. Reassess scope when new evidence changes the best next step. Efficiency means useful progress toward a verified product, not merely more code or more tool calls.

## Simple, clear, and orderly implementation

Founder instruction: keep code, architecture, tooling, and documentation simple and neat. Prefer the smallest understandable solution that meets the requirement, with clear names, focused responsibilities, consistent formatting, and a predictable file structure. Keep module boundaries explicit without introducing unnecessary layers or abstractions.

Avoid duplicated logic, dead code, speculative configuration, and unnecessary dependencies. Clean up artifacts introduced by the current change; do not mix unrelated refactors into a focused slice. Keep errors and state transitions explicit rather than hiding complexity behind clever code. Simplicity must preserve correctness, observability, and necessary failure handling.

Review each checkpoint for readability and maintainability as well as behavior. The next engineer or agent should be able to understand what the code does, why it exists, and how to verify it without reconstructing the conversation.

## Providers must earn their role

Founder clarification, September 25, 2026: remove a model from a role when evidence shows it is not working as intended. Jev is an implementation choice, not a requirement to preserve at the expense of product behavior. Diagnose the affected role, verify the replacement against supported and unsupported cases, preserve failed evidence, and keep useful independent roles only while their evidence supports them. Do not accumulate prompt workarounds or weaken acceptance rules merely to retain a preferred provider.

Founder refinement: prefer Luna for extraction and Jev for independent verification. A false rejection under an application threshold does not by itself prove the model is unsuitable. Diagnose the question, supplied context, and gating separately; test supported and unsupported cases without tuning solely to one success. The temporary Luna-verifies-Luna approach is superseded by this explicit preference. Keep failed evidence and do not deploy a candidate fix with known false acceptances.

Founder clarification: consider edge cases and the user experience when designing automated decisions. Check both false acceptance and lost useful information, how uncertainty reaches the user, and whether stale information could be presented confidently. Preserve source evidence and distinguish latest reported knowledge from a claim that the world has not changed.

Founder-approved refinement, September 26, 2026: evaluate and adopt Luna for source-only identity resolution when bounded evidence supports it, while keeping Jev as the independent fact and lifecycle verifier. The final bounded writer uses low reasoning for identity only. Do not infer authorization to move all verification to Luna, weaken identity guards, or change extraction/answer settings. Preserve failed comparisons and require explicit target claims when matching subjects in multi-person passages.

Implementation application of the approved identity role: recording-subject attribution now uses Luna with low reasoning after the bounded comparison in [memory-chunk-writer.md](memory-chunk-writer.md). Jev continues independent fact, modality, time and lifecycle verification; authenticated personal-text attribution retains its earlier Jev path. This is an evidence-based implementation choice, not authorization to remove independent fact verification or infer account ownership from a recording.

## Memory-system design baseline

Founder decision, September 26, 2026: build and control our own memory system; do not adopt gbrain. Apply the [Dhravya Shah article](https://x.com/DhravyaShah/status/2103314339239428201) across the whole harness, not only the Jev adapter or retrieval checkpoint. Use its findings as the agreed design baseline, including its negative findings. QA establishes whether our implementation delivers that baseline for the companion.

- Learn outside the main answer loop; preserve original source evidence separately from derived memories.
- Chunk with contextual continuity. Use bounded Jev boundary decisions where useful; do not prune individual sentences before learning and lose their dependencies.
- Retrieve relevant evidence and assemble bounded context in the harness rather than relying exclusively on the answering model to request memories.
- Prefer ranking to destructive relevance gates. Keep deterministic ownership, deletion and evidence-integrity rules separate from probabilistic usefulness.
- Use Jev for bounded decisions, not every task by default. The article favors dedicated rerankers on its measured cost-quality tradeoff; select retrieval roles accordingly and verify our integration.
- Preserve uncertainty and sources throughout storage, lifecycle handling, retrieval and answer context. Expiry retires current applicability without erasing the original recording or implying a planned event occurred.

The final bullet applies these principles to our agreed product lifecycle; the article does not itself specify our identity rules, expiry semantics or database schema. Keep that distinction explicit in implementation evidence.


Founder refinement, September 26, 2026: authorize an isolated comparison of gbrain against our memory system before committing to further custom infrastructure. This reopens the build-versus-adopt decision for evaluation; it does not authorize migration, public forking, deployment, new provider spending beyond approved allowances, or weakening our attribution/deletion contracts. Preserve the app and production data while testing pinned upstream code on synthetic inputs. See [comparison evidence](gbrain-comparison.md).

Founder refinement, September 26, 2026: ordinary recording deletion may retain learned memories and use them in answers. Evaluate retention separately from source availability: no broken citations or claims that deleted transcripts remain viewable. Preserve correction and attribution rules. Earlier deletion-cascade tests remain historical evidence; they are no longer the desired ordinary-recording deletion contract. The founder approves up to $0.50 additional provider QA for the gbrain comparison, within the unchanged $5 global cap; reserve each call, preserve responses and prohibit automatic paid retries.

Founder decision after the gbrain screen: keep our backend and address the independent verification failure. Preserve the approved retained-memory deletion direction as a separate slice. The next candidate must demonstrate factual retention and negative-case behavior through the real writer; a passing standalone verifier screen is not enough to deploy it. See [candidate and QA gate](independent-source-verification.md).

Founder-approved verification QA, September 26: up to $0.25 within the unchanged $5 global cap for the independent source verifier. Keep this allocation distinct from gbrain QA. The verified candidate uses Sol for source-only factual entailment and Jev for modality/time; it does not remove independent verification or lower thresholds. Preserve original cited passages, and treat supported retention plus negative-case behavior through the actual writer as the gate. Runtime enablement does not grant fresh spending, and deployment remains separate from merging the verified code.

Founder-approved internal verification rollout: an additional $0.25 for rollout testing and internal learning, within the unchanged $5 global cap. Provision once, preserve prior charges, and do not count allocation transfers as microphone attempts. Retain the existing Render tier. See [rollout contract and evidence](verification-rollout.md).

Founder-approved retained-memory QA, September 26: up to $0.05 within the unchanged $5 global cap, at most six live Jev/Luna calls, no automatic retries. Keep this allocation separate from earlier verification allowances. Provider QA approval is not internal deployment or physical-device readiness. See [retention evidence](retained-recording-memory.md).

Founder-approved retained-memory internal rollout, September 26: deploy the verified checkpoint on the existing Render plan after backup and matching native update. Preserve existing data and usage charges; physical QA still waits for explicit readiness. This does not raise spending caps or waive daily attempt limits. See [rollout evidence and pending phone gate](retained-memory-rollout.md).

Founder-approved notes-generation QA, September 26: up to $0.15 for at most six live GPT-6 Luna calls, within the unchanged $5 global cap. Use short saved/synthetic transcripts, preserve exact responses, and prohibit automatic paid retries. This is generation-quality QA, not ongoing production-note spending, deployment approval, or physical-device readiness.

Founder-approved notes internal rollout, September 26: deploy the verified notes checkpoint on the existing Render plan, with up to $0.05 for at most two notes-generation calls inside the unchanged $5 global cap. Keep this allocation distinct from the exhausted six-call generation QA allowance. Preserve data and previous reservations, prohibit automatic paid retries, and wait for explicit readiness before the physical-iPhone check. This does not authorize a plan upgrade or permanent quota increases.

Founder-authorized notes-first consolidation, September 27: simplify around sourced notes, transcript fallback and bounded relevant personal context. Preserve correction, attribution and retained-knowledge contracts while reducing redundant machinery. Validate the replacement before retiring the known working path; do not mistake the seven-case lexical comparison for full-system answer quality or budget approval. See [checkpoint plan](notes-first-memory-plan.md).

Founder-approved notes-first retrieval QA, September 27: up to $0.15 for at most six Jev rankings and six Luna answers, inside the unchanged $5 global ceiling. Reuse saved recordings/notes, record exact requests and results, and prohibit automatic paid retries. This allowance is distinct from notes generation/rollout and does not authorize deployment. See [implementation and evidence](notes-first-memory-plan.md).

Founder-approved matched retrieval QA, September 27: at most $0.30 and 24 additional provider calls, with the cumulative ceiling raised to $5.30. Reuse exact responses, prohibit automatic paid retries and leave the deployed app unchanged. The operator-only $0.30 extension is accounted alongside the unchanged $5 runtime envelope; it must not silently increase runtime quotas. The [matched comparison](matched-recall-comparison.md) found a notes-first disagreement omission; hold rollout until that acceptance failure is resolved and verified.

Founder-approved source-scoped learning QA: repurpose at most $0.05 of unused unified-recall QA, at most two Luna and two Jev calls, with no retries or increase to the $5.55 combined ceiling. Reserve the child allowance inside the parent grant to prevent double spending. This approval covers verification, not deployment. See the [simple-memory checkpoint](simple-memory-foundation.md#checkpoint-3-verified-result-and-rollout-boundary).

Founder-approved unified-memory internal rollout, September 27: deploy the verified merged foundation on the existing Render plan and disk, enabling unified recall and source-scoped learning together. Preserve data, existing usage charges and quotas; this approval does not authorize new paid model calls or public release. Back up before migration and verify data integrity, serving-process flags, health and authenticated reads. Rollback must preserve schema compatibility and current ledgers. See [rollout evidence](simple-memory-rollout.md).

Founder-approved companion-personality QA, September 27 UTC: up to $0.20 for ten short Luna responses, no automatic paid retries. This is an isolated operator grant, bringing combined approved envelopes to $5.75 while preserving the $5 runtime envelope and all production quotas. It does not authorize production deployment or waive physical dictation QA. Keep request/response evidence and report taste limitations separately from factual/contract failures. See [results](companion-feel-and-dictation.md#approved-ten-response-personality-check).

Founder-approved memory-gate shadow QA: up to $0.08 for sixteen Jev classifications, no automatic retries. This isolated operator allowance brings combined approved envelopes to $5.83 while preserving the $5 runtime envelope and production quotas. Compare against predeclared synthetic labels, preserve uncertainty by retrieving, and measure added latency. This permits evaluation only, not a production retrieval gate. See [screen](memory-gate-screen.md).

## Durable knowledge and feature context

Keep the feature maps and current-state brief aligned when implementation, QA status, a founder decision or a consequential research result changes. Separate deployed behavior, verified local candidates, unverified proposals and deferred/rejected experiments. Preserve historical failures and approvals with explicit supersession notes instead of rewriting them as successful evidence. Link detailed receipts; do not duplicate private source data or turn historical allowances into fresh spending authorization. Documentation-only changes require link/path and contract verification, not unrelated provider or device runs. See [current state](current-state.md) and [feature map](features/README.md).

Founder-approved physical dictation QA refinement: $0.05 total for one short recording, one companion answer and the remaining pre-funded notes-generation call. This supersedes the earlier $0.04 screen envelope; conservative reservations total $0.048. No overall budget increase, automatic retries or new memory-learning funding. Physical readiness remains separate.


Founder-approved capture boundary, September 27: composer dictation takes priority over meeting audio; show the pause and resume capture automatically after dictation ends. Implement the boundary in audio routing rather than trying to remove private questions from transcripts afterward. Verify audio exclusion, timing continuity, resumption, and stop/error cleanup separately from recognition quality. Earlier accidental omission is not evidence of deliberate isolation.
Founder-approved physical dictation QA: up to $0.04 within the existing $5 runtime cap for one short recording and one companion response, no automatic retries. Authorizes transferring $0.02 of unused Ask category capacity to transcription without altering previous charges or increasing total caps. Hosted compatibility deployment remains a separate gate; PR 99 remains pending physical acceptance. See [bounded funding](dictation-physical-qa-budget.md).

Founder-approved private-dictation physical QA, September 27: an additional $0.05 for at most one short recording, one answer and one generated note, no automatic retries. This raises the runtime ceiling from $5.00 to $5.05 (combined recorded envelopes from $5.83 to $5.88). Preserve previous charges and record an explicit operator extension; startup must not fund it automatically. Founder also confirmed readiness. This permits the supporting budget compatibility rollout and native test build, not completion or release of unverified PR 99.


Founder-authorized v3 personality internal rollout, September 27: deploy merged PR 99 on the existing Render service after backup and verify prompt selection, health, data preservation and unchanged usage. No fresh provider QA or budget increase is authorized by deployment. See [rollout evidence](companion-feel-and-dictation.md).


## Experience-led UI implementation — September 27, 2026

Founder direction: actively consult the Libraries.dev skill throughout UI/UX design and implementation. The approved Home mockup is the visual source of truth for typography, white surfaces, icon treatment, rounded controls and visual hierarchy across all screens, including sign-up and pricing. Library defaults and third-party examples must be adapted to that direction. This is design guidance, not a claim that the mockups or effects are implemented.

Before changing an interaction, identify the user's context, intended action, information they need to see, reachable place to touch, immediate feedback and desired feeling. Evaluate the complete transition, including keyboard, loading, empty, denied-permission and failure states. Preserve drafts, capture state and navigation continuity. Validate touch targets, one-handed reach, readable text, reduced motion and actual device behavior at the affected layer. Treat emotional outcomes as hypotheses to check with the founder and representative users.

Use Libraries.dev regularly to evaluate useful feedback for capture, dictation, processing and responses. Read the selected component's reference before implementation; verify native SwiftUI compatibility and dependencies rather than assuming React examples work in the app. Connect effects to real state, preserve audio ownership, stop unnecessary offscreen animation and check performance. Frequent consultation does not require animation on every control. Home's approved styling and product purpose govern which effects earn a place.

The free skill was installed locally as `libraries-dev` from `Jakubantalik/Libraries.dev`, `skills/libraries-dev`. Installation is an agent-environment change, not an app dependency. Other environments must install it separately. Source: https://libraries.dev/skill and https://github.com/Jakubantalik/Libraries.dev/tree/main/skills/libraries-dev. No paid Studio purchase or application package installation is implied.

Founder fidelity correction, September 27: use the approved Home mockup for icon silhouettes (Home, Agent, profile, search and document), composer proportions and page continuity. The composer and external capture plus must share the white canvas without a separate material footer. The inner composer plus opens attachments; the external black plus starts capture. Verify rendered native screens against the reference and carry the shared styling through supporting pages.

Founder revision: replace the inner composer attachment plus with a paperclip. Home and Agent use the same shared composer; the external capture plus is unchanged. This supersedes the attachment glyph specified above.

Founder composer interaction revision: one trailing control in the shared Home/Agent composer. Empty or whitespace-only drafts show mic; nonempty drafts show send. Active dictation keeps Stop until text is ready for review, and an in-flight answer keeps Cancel. The supplied mobile screenshots illustrate the control substitution, not a change to the app branding or chat layout.


Founder all-screen fidelity direction, September 27: compare rendered native Home, Agent, saved notes, live transcript, sign-up, pricing, account and search against the eight supplied final mockups. Match shared typography, iconography, spacing, sizing, borders and shadows using screenshot iteration. Preserve subsequent interaction decisions: upright paperclip, shared Home/Agent composer with mic replaced by send for text, external capture plus, Stop without Pause, and recording-bar tap to open transcript. Visual reference content does not authorize fake authentication, billing, analytics or new product capabilities. Record actual differences and verification limits.

Founder composer revision, September 27: Home and Agent use a single-row composer at rest. The upright paperclip, inline text entry and mic/send action share one row; text begins immediately to the right of the paperclip. Longer drafts wrap and increase the text field height naturally. This supersedes the earlier two-tier composer geometry while preserving attachment, dictation and capture behavior.

Founder navigation revision, September 27: Agent is the main/default surface and first top tab; the recording library is named Notes and is the secondary tab. Keep both tabs available on both root surfaces. The recording bar uses the visible label “View” instead of an up chevron; Stop remains separate.


Founder motion/feedback revision, September 28: remove the repeated Ellis author heading from chat responses. Present user-facing errors and service notices in readable cards. Use the supplied Wispr Flow capture button as the visual reference (charcoal circle, rounded heavier plus, restrained shadow). Add light haptics to deliberate button presses and distinct recording-state confirmation; never tie vibration to streamed tokens or every keystroke. System haptic settings and platform suppression remain authoritative. Use native, interruptible transitions and honor Reduce Motion. Libraries.dev remains a source for useful state feedback, not an instruction to introduce React or decorative effects throughout the native app.

Founder navigation clarification, September 28: Agent remains the primary page with the Agent/Notes selector. Notes opens as a secondary page with a back button to Agent, a Notes title pill and page-specific actions. This supersedes the requirement to retain both top tabs on the Notes page. The Notes content remains the recording library.

Founder dictation revision, September 28: while dictating, replace the inline composer with trash, elapsed time, a real microphone-level waveform and Send (no Pause). Send finalizes recognition, appends to the existing draft and sends the combined message only after successful final recognition. Trash discards only the active dictated segment. Preserve interruption/failure recovery without automatic sending. User notices have a top-right dismiss X; profile/search circles use visible pale-gray borders matching the tabs.

Founder dictation-control correction: use the same circular up-arrow send control as typed messages, not a visible Send text label. Preserve its accessible Send label and finalization behavior.

Founder paperclip-menu revision: call the attachment action “Attach note,” remove Dictate message and Clear draft, and improve Refresh conversation feedback. Preserve drafts during refresh; keep existing history visible while revalidating and do not leave unvalidated source evidence presented as current after a failed refresh. Dictation remains available through the empty composer's microphone.

Founder notice-dismissal refinement: dismissed error cards should fade and gently collapse with surrounding layout movement, respecting Reduce Motion.

Founder incoming-message revision: Agent replies use the supplied Manus-style light-gray, subtly bordered, rounded content-sized bubbles with slightly heavier text, aligned left. Apply to streaming and saved replies; retain the no-repeated-author-label decision.

Founder Agent-bubble correction: use regular body text, remove the persistent copy icon below replies, and expose Copy by long-pressing the reply bubble. This supersedes semibold reply text while retaining the gray bubble styling.


## Note deletion preserves conversation — September 28, 2026

Founder revision: deleting a note removes its recording/transcript but preserves already sent companion answers and follow-ups. Do not replace them with source-deleted notices. Remove unavailable source links and exclude unsupported historical answers from evidence context; learned-memory retention remains unchanged. Notes offer swipe Delete and long-press Share/Delete with confirmation. This supersedes answer-scrubbing behavior for ordinary note deletion; source corrections retain their existing validation rules.

Founder UI refinement, September 28: Notes uses stacked title/preview/time cards without leading document icons. Taps open details; swipes reveal neutral Delete/Share/Copy actions; long-press exposes those same actions. Prefer native gesture arbitration so dragging never triggers navigation.

Founder note-action refinement, September 28: swipe Delete is red, Share blue, Copy the prior muted gray. Use simple outline symbols with consistent weight: trash, curved share arrow, overlapping squares for Copy. The same symbols appear in the long-press menu; retain native destructive-menu semantics.

Founder refinement: hide visible captions beneath the swipe circles; preserve their accessibility labels and the long-press menu names.

Founder onboarding refinement, September 28: replace the empty-chat placeholder with a first agent message introducing the companion, deliberate capture/Notes and composer dictation. Render it as an ordinary reply at the beginning of the main conversation, not as a separate onboarding screen or a repeated author heading.


## Proactive note-taking product revision — September 28, 2026

Founder replaces the old one-liner with “AI notes that proactively contribute to discussions” and adopts the full description in [product source of truth](product-source-of-truth.md#full-product-vision--september-28-2026). Proactive context-aware text contributions are the core New hypothesis. Calendar, email and messages are included in the complete product vision, while deliberately captured notes/conversations are the first source set. The earlier reactive-only release scopes remain historical evidence, not the complete product definition.

Preserve the native capture/notes/chat/memory baseline. This authorization is a documentation and implementation-gap audit, not a code rewrite, provider run, connector authorization, deployment or new spending grant. A proposed roadmap is not implementation acceptance. Source content remains untrusted data; preserve owner, identity, revision, lifecycle and deletion contracts across future connectors. Separate remembered evidence, general model knowledge and new suggestions. For proactive behavior, prove relevance, timing, appropriate silence and user control, as well as factual correctness. Do not infer a particular judge model or always-on architecture from the product description.

Current navigation need not change merely because external positioning is note-taking-led. Medical, therapy and financial settings are intended contexts; current generic chat is not evidence of specialized readiness in those settings. Fresh outside information needs an independently validated retrieval path; general model knowledge is not web research. Connector-specific access, disconnect/erasure rules, realistic capture duration, cost and physical-device execution need bounded checkpoints in the [audit](product-vision-audit-2026-09-28.md).


## Past-note proactive MVP and QA allowance — September 28, 2026

Founder selects proactive text contributions grounded in past captured notes as the next MVP feature, targeting an eventual App Store release before applying to YC. Connected calendar/email/messages and outside-knowledge retrieval remain full-product scope, outside this feature. Founder authorizes up to $0.25 and at most 12 live model calls for this feature's verification, stopping at either limit with no automatic retries. Keep a separate operator ledger; do not silently increase production quotas or repurpose historical allocations. This does not fund new paid transcription, ongoing runtime usage or authorize App Store submission. Physical readiness and deployment gates still apply.

The current request is the [implementation plan](proactive-contributions-plan.md), before code changes. Jev is a candidate role to compare with a simpler LLM path, not a mandatory gate. Preserve the existing Ask flow, provenance and deletion contracts. Distinguish replay, live-model, native-app and physical-device evidence; no one layer establishes all acceptance.


Founder presentation clarification: proactive contributions appear as ordinary agent messages in the persistent main chat, with the same styling and follow-up interaction as other replies. Do not add a separate suggestion card, badge/label or per-contribution dismissal workflow. Internal provenance and trigger metadata remain distinct for validation. This supersedes the suggestion-specific presentation proposed in the [implementation plan](proactive-contributions-plan.md).

Founder authorizes starting the proactive implementation on September 28, following the approved plan and normal checkpoint verification. The earlier planning-only boundary is superseded for implementation; paid QA stays within the separate $0.25 / 12-call grant and deployment/physical readiness remain separate.

Founder-approved proactive physical-test setup, September 28: an additional $0.09 for two recording reservations ($0.02 each) and two note-generation reservations ($0.025 each), with no automatic retries. Runtime ceiling becomes $5.14; preserve all historical charges. Use at most five remaining Luna calls from the existing $0.25/12-call proactive grant, not a second grant. No separate personal-memory learning for these video captures. Enable an expiring, account-scoped internal test and install its real-microphone Debug build; wait for separate physical readiness before capture. Founder selects Luna only for proactive decisions/drafts; this does not change existing memory-model roles.

Founder saved-note formatting correction, September 28: remove visible source-document icons from generated notes. Render readable full-width paragraphs and clear section bullets, with titles contained by the page margins. Preserve supporting-source navigation through the paragraph context menu; source count must never determine the note's horizontal layout.

Founder-approved saved-transcript proactive replay, September 28: a new isolated allowance of at most $0.10 and five Luna calls, no automatic retries, using the two saved video recordings without audio or phone participation. This is separate from the exhausted original proactive grant and leaves runtime quotas unchanged. Founder also explicitly requested resetting app data, past memory, chats and notes. Clear active account content and local app data while preserving credentials, unrelated owners and historical spending ledgers; remove temporary replay source/response copies after inspection. This is an app-state reset, not an assertion of erasure from historical operational backups or external provider retention.

Founder-approved personal proactive evaluation, September 28: a new isolated allowance of up to $0.60 and 30 Luna calls, stopping at either limit, with no automatic retries. Use fictional histories in isolated QA stores, compare baseline and candidate on matched cases, then spend remaining calls only on targeted refinement and fresh validation. Preserve the reset personal account, runtime quotas and historical ledgers. This permits evaluation and verified implementation checkpoints, not production deployment.

Founder-approved Cedar solo phone pilot: up to $0.17 for one short recording, one generated note and at most six Luna proactive evaluations, with no automatic retries. Provision $0.045 into runtime recording/notes capacity and $0.12 in a separate six-call proactive ledger ($0.165 total reserved capacity); leave the remaining $0.005 unallocated. Seed explicitly fictional Cedar history, restrict retrieval to this experiment, suppress personal learning, preserve all old grants and charges, and keep a 24-hour account-scoped gate. This authorizes the supporting compatibility deployment and enabling the phone test; wait for explicit readiness before recording.

Founder interjection readability refinement: the Cedar reminder felt helpful and naturally timed. Prefer short plain-language texts in a small group of normal agent bubbles instead of one dense paragraph. Preserve readable body typography and necessary identity/time qualifiers; keep one durable contribution, one notification/scroll event and one cooldown for the group. Wording validation and deployment remain separate from deterministic rendering checks.

Founder clarification: short interjection messages must retain decision-critical details such as “before adding features,” along with relevant quantities, conditions and recorded status. Split the information across readable messages without dropping the reason the reminder matters.

Founder further clarifies: preserve the useful contribution in full and present it in bite-sized chunks. Do not impose new word-count or bubble-count targets that remove information or merge the remainder into a dense block. One natural idea per bubble, with its necessary qualifiers, is the presentation goal. Existing overall backend response bounds remain unchanged.

Founder asks to optimize message size for readability and engagement. Working UI hypothesis: one natural idea, often a sentence or two, roughly 2–4 mobile lines where practical; no truncation, smaller font, fixed line clamp or information loss. Dynamic Type and actual text length govern final height.

Founder approves reallocating the five remaining Cedar Luna calls to proactive readability QA, with no extra budget. Use the existing six-call/$0.12 ledger (one call already consumed), preserving historical reservations; no retries. This authorizes fictional wording/completeness/silence evaluation, not new recording, notes generation or deployment.

Founder correction: “optimal message size” means character amount, not bubble UI geometry or a new grouping renderer. Restore the existing chat renderer; preserve bubble styling, typography, spacing and interactions. Earlier requests for bite-sized language and complete useful content still stand. A character range may guide wording but must not truncate qualifiers or remove useful information. No universal optimum is established. The unselected v3 paragraph-grouping experiment is historical and is not the current direction.

Founder authorizes implementing character-length refinement while preserving phone UI. Drafting hypothesis: roughly 120–240 characters when natural, shorter or longer as needed to retain useful content. No hard truncation, font/layout changes or bubble splitting. Continue only the three never-sent reserved readability cases with corrected error diagnostics, no retry of the failed request and no new allowance. Deployment remains separate.

Founder approves internal deployment of verified v4 wording and implementing conversation-level validation. Preserve phone UI and current capture controls. Free replay must explicitly distinguish deterministic scheduling/storage checks from synthetic model decisions; acknowledgment, topic relevance and useful follow-up require separate bounded live-model evidence. No new paid allowance is implied.

Founder approves an isolated $0.10 / five Luna-call conversation-level screen, no retries. Use the five predeclared exported fictional contexts; preserve prior exhausted ledgers, runtime quotas and personal data. This does not fund physical recording or authorize enabling a new phone pilot.

Founder approves two-topic phone setup up to $0.21: one recording, one generated note, eight Luna proactive checks, no retries. Provision $0.045 runtime plus $0.16 isolated proactive capacity ($0.205), leave $0.005 unallocated. Preserve old charges; use two fictional seeds plus one live capture, account-scoped 24-hour gate and no personal learning. Supporting compatibility deployment/seed activation are authorized; wait for separate physical readiness before recording. No phone UI change.

Founder bubble-margin refinement, September 29: agent messages extend too far to the right. Increase the trailing breathing room consistently for welcome, saved and streaming replies while preserving bubble styling, body typography and message content.

Founder approves a two-topic test continuation, September 29: up to $0.05 for one additional recording and generated note ($0.045 provisioned). Reuse the seven remaining calls in the original eight-call/$0.16 proactive ledger; no replenishment, retries or expiry extension. Preserve previous captures, chats and charges. Activate a fresh capture registry containing the same two fictional seeds, exclude the interrupted capture from current retrieval while retaining its learning exclusion, and wait for physical readiness. Supporting server compatibility deployment is part of enabling this test.

Founder wording refinement, September 29: companion messages should feel like a person talking, not a synopsis. Preserve useful evidence and qualifications with short conversational sentences and readable chunks; remove formal recap language and redundant conclusions. Keep the accepted bubble UI unchanged. Proactive candidate validation must evaluate actual generated output before selecting or deploying the new prompt.

Founder separate-message clarification, September 29: proactive contributions must support multiple actual chat bubbles, not merely paragraph breaks in one bubble. Preserve each bubble’s accepted styling and margins. Provide an explicit ordered messages model contract and verify model output → validation → persistence → rendered bubbles, with one contribution notification/cooldown and no per-bubble paid calls. This supersedes the earlier prohibition on grouping while retaining ordinary reply behavior.

Founder authorizes reallocation of the three remaining two-topic proactive calls to conversational, separate-message QA, September 29; no additional spending or automatic retries. Deploy/install the matching behavior only if actual outputs and local verification meet acceptance.

Founder approves an isolated $0.06 / three-call conversational v6 screen, September 29, with no retries. Preserve all prior ledgers and runtime limits. Deployment remains conditional on verified behavior and accepted wording.

Founder approves an isolated allowance of up to $0.20 / ten Luna calls for conversational proactive refinement, September 29, with no automatic retries. Start with three purposeful wording/transfer/silence cases; inspect actual outputs before further calls. Preserve exhausted ledgers, runtime quotas, personal data and accepted bubble styling. Select or deploy only after factual, conversational and separate-message acceptance.

Founder sequencing correction: the orchestrator must build, exercise and review verification tooling before workers start, so every packet includes working verifier commands. GPT-6 Astra/low workers receive bounded file ownership and acceptance criteria. Workers submit real-path evidence to the orchestrator, which inspects it and explicitly releases dependent work; a passing script never self-authorizes continuation. Summary caching and demo/TestFlight sequencing remain specified in docs/execution/demo-testflight-phases.md.

Founder clarification: verification is organized by product feature, not only execution packet. Each feature has an implementation map and a linked executable verification contract covering its automated checks, actual behavior and inspection. Workers use those feature verifiers; planned or missing checks remain explicitly incomplete. See docs/features/verification-map.md.

Founder further clarifies: every product feature also needs its own context map, separate from its verifier. Before assignment, the map must identify current behavior, missing capability, code/contract boundaries, dependencies, evidence limits and the next bounded work. Workers read their map before implementation and submit state/evidence deltas to the orchestrator for review. See docs/features/context-map.md.

Founder social-presence revision, September 29: prioritize an invited third intelligent participant with personal continuity and judgment about when/how to contribute; note-taking-led positioning is superseded. Reuse capture/notes as foundations and the existing provenance/identity/temporal store for linked personal knowledge. Do not infer a graph-database rewrite, TTS, public sharing or always-on authorization. Acceptance must distinguish grounded recall from a useful contribution, test silence/corrections/topic changes, and inspect actual model → durable messages → app behavior. Preserve accepted message UI. See docs/social-presence-experience.md and the revised phase plan; consumer copy and scenario details there are proposals, not deployed capability.

Founder interface refinement: explore a non-traditional, personable social-companion home/live-conversation experience rather than the existing note-taker/dictation-led shell. This supersedes the prior plan’s blanket layout-preservation constraint. Prototype the full state flow and obtain concrete visual review before replacing the native shell; preserve capture, draft, Quiet/End, accessibility and durable-message contracts. See docs/social-presence-experience.md.

## Bounded background execution split — September 29, 2026

Founder authorizes background execution while the founder and primary chat personally redesign the UI. Baseline is origin/main `47eadb4c8be3a46593bb6f17250f4c24335ea02c`. The subsequent coordination revision narrows this background coordinator to P0 verifier diagnosis/repair and canonical execution-split documentation, with one GPT-6 Astra/low worker and independent evidence review. Primary chat `01a0d1ef-b102-75e0-9198-a184db8cfb85` directly coordinates separate audit, cache, recovery, proactive and distribution lanes. The original optional cache/recovery continuation under this coordinator is superseded; no additional worker or dependent slice starts here.

The five directly coordinated lanes are:

| Lane | Owner / file boundary |
| --- | --- |
| Baseline/verifier | This coordinator and one bounded Astra/low worker: affected backend regression tests, evidence and canonical split documentation |
| Offline note cache | Chat `01a0ec46-429c-72e1-97b6-ca4a111e6fd6`: `RecordingNotes.swift`, `RecordingNotesView.swift` functional behavior, cache and dedicated tests |
| Proactive controls | Chat `01a0ec46-44a2-7782-9687-ec3c4c3ce1c1`: `proactive_service.py`, `proactive_policy.py` and dedicated tests |
| Capture recovery | Chat `01a0ec46-4681-7f92-a6ab-d9dde5da6e1b`: native lifecycle/recovery only after its exact ownership report |
| Distribution/access audit | Primary-assigned read-only audit using the existing isolated `distribution-access-audit` checkout; no implementation or upload |

Primary coordinates shared-file/contract ownership before edits and accepts each lane's exact source, raw evidence and behavioral claims before dependencies advance. A lane's green tests or self-declared completion do not release another lane. This coordinator remains the only writer of canonical execution-split guidance. Primary owns the visual redesign; functional lanes preserve it and report interface conflicts before proceeding. All lane PRs remain for primary review/merge.


Primary owns companion character/identity, colors, typography, layout, navigation, visual styling, icons and decorative motion. Background changes must preserve these; minimal functional recovery/cache integration requires a clear existing contract and stops for primary review if it conflicts. No shared design-component edits. No simulator/device lease is assumed. Founder-dependent manual QA waits for explicit readiness.

This wave has zero paid-provider allowance and permits no deployment, upload, tester invitation, production reset or secrets in evidence. Preserve both the original project checkout and dictation-qa-budget reference checkout without branch/file changes. Use isolated managed worktrees. The coordinator inspects and reproduces worker evidence, maintains truthful feature maps, opens a focused PR and leaves it for primary review/merge. This wave does not authorize workers to advance dependencies or merge independently.
Founder native redesign approval, September 29: the reviewed companion-room prototype supersedes the old neutral Home mockups for the next UI checkpoint. Lavender/plum palette, companion home, two-line Notes entry on the left, Invite affordance on the right, horizontal Notes navigation, and a single capture status above the composer. No redundant listening label under the companion or home search control. The redesign takes priority over old navigation; preserve note swipe/hold Delete, Share, Copy, draft/capture continuity, accessibility and durable data. Plus starts deliberate capture without a second invitation screen. Friend invitations and final companion artwork remain unfinished; do not invent delivery or share private content through the placeholder. Validate actual native behavior before installation or release.

Founder capture-bar refinement, September 29: keep the circle red, with “Listening” directly beside it during active capture. This supersedes the plum capture-indicator choice above; connection, paused and finishing states retain their truthful labels.

Founder Notes navigation refinement, September 29: keep Notes entry on the left and Invite on the right. Notes enters from the left and exits back to the left, with the companion returning from the right.

### September 29 founder revision: prototype fidelity

The approved companion-room prototype is the component-level visual source of truth for the native redesign. Port its palette, type, icon paths, spacing, controls and navigation instead of reinterpreting the screen. Keep the approved prototype stable while comparing native evidence. Preserve real controllers and note swipe/hold actions; disclose platform-specific presentation differences and do not equate a successful install with physical behavioral acceptance.

### September 29 founder revision: one shared prototype interface

After reviewing discrepancies in typography, controls and motion, the founder confirmed literal shared UI code, with the approved companion-room prototype as the source of truth. The iPhone presentation will use a bundled local HTML/CSS/JavaScript interface in WKWebView; its browser preview uses the same assets. This supersedes separate SwiftUI recreation for the companion room, not native capture, dictation, storage, security, or the shared Mac foundation. Keep the working native presentation as a rollback until the replacement passes behavioral and physical-device checks. Simulated prototype replies/capture must never enter the production bridge. No credentials are exposed to JavaScript, remote navigation is blocked, and text from recordings/models is data rather than HTML or executable instructions. Platform safe areas, keyboard and accessibility remain explicit verification requirements.

Founder motion revision, September 29: matching the initial prototype timings is insufficient after hands-on feedback that all motion feels too fast and abrupt. Revise the approved prototype and shared presentation together toward slower, smoother transitions, keeping direct manipulation tied to the finger. Chat left-swipe opens Notes; the existing menu and note swipe actions remain. Preserve white backgrounds and original purple action accents while replacing lavender surface washes with neutral gray. Button haptics must be wired to the native device; simulator event success is not evidence of physical tactile quality.

Founder checkpoint revision, September 29: merge the reviewed UI as the internal baseline, then review/integrate the phased-plan changes without altering its presentation. Preserve shared UI assets and interactions; functional integration must be verified behind the existing interface. Remaining physical/release checks stay explicit TestFlight gates.


## Release authentication — September 29, 2026

Founder decision: ship both Google and Apple sign-in, with Google above Apple in the sign-in UI. Neither provider is deferred. Preserve the approved shared interface. Implement and verify real enrollment, stable ownership and session lifecycle; preview buttons do not establish authentication. Follow the existing small-checkpoint, real-path QA and founder-dependent blocker rules. This decision grants no new paid-model allowance and does not select prices or a pilot cohort.

Founder TestFlight clarification, September 29: functional frontend wiring for Google/Apple sign-in and necessary account/privacy pages is authorized. This supersedes the blanket UI-code freeze. The established UI design system is the source of truth: preserve existing screens, styling, typography, colors, spacing, motion and visual character. Reuse current components and patterns for additions; do not redesign or restyle existing UI. Verify actual app behavior and visual consistency.

Founder execution clarification, September 29: proactively implement, verify, review and merge checkpoints toward TestFlight readiness without repeated routine approvals. Reuse existing UI components and elements, including animations, transitions, button-press feedback and haptics; the established UI/UX system remains the source of truth. Do not invent a replacement interaction or visual system. Founder authorizes a new total allowance of $5 for provider/API testing toward TestFlight readiness. Track reservations and actual usage, stop at the cap, and do not automatically retry paid calls. This allowance excludes hosting upgrades, subscriptions and other purchases. Existing budget history and no-automatic-paid-retry rules remain in force. Legal acceptance, purchases outside the specified allowance, required product decisions and physical-test readiness remain distinct gates.

Founder account decision, September 30: keep Google and Apple as separate Ellis
accounts with persistent sign-in; do not implement automatic or explicit account
linking for this release. The founder selects Google as the destination for
existing pre-authentication development data. Verify the exact legacy source and
Google identity, preserve unrelated owners and all budget history, and rehearse
the coordinated server/local migration before cutover. This does not authorize
moving Apple account data into Google or inferring identity from email.

Founder QA workflow revision, September 30: automate live simulator interaction
and inspection instead of repeatedly asking the founder to tap routine controls
or report screenshots. Use native UI tests and real backend/state evidence for
sign-in navigation, sign-out, relaunch, account switching and recovery where the
available tooling supports them. This does not change the UI design system.
Request founder input only for an actual access/credential/security challenge,
required decision or judgment, or physical behavior that automation cannot prove
(such as microphone quality and haptics). The readiness rule applies when the
check needs founder participation; it is not a new permission gate for each
agent-operated simulator action. Keep live-provider evidence distinct from
fixtures and preserve private result bundles containing account identifiers.

Founder release-sequencing clarification, September 30: the existing mascot is
temporary and the founder will provide the final mascot later. Its unresolved
distribution rights are an asset gate before distributing that image, not a
reason to stop account, plan, paywall or other release preparation. Do not ship
the unlicensed placeholder or invent a replacement design. Plans and a working
paywall remain in the requested release scope; creating the App Store record
does not mean the app is ready for submission or that billing may be skipped.

Founder sequencing instruction, September 30: move through the TestFlight plan
in order. Finish Phase 1 account/data-lifecycle acceptance before beginning
Phase 2 pricing/limits, then Phase 3 paywall/subscriptions, Phase 4 release
preparation and Phase 5 pilot. Preserve already completed Apple setup, but do
not use a pending account check as a reason to advance to a later phase.

Founder orchestration instruction, September 30: the primary agent coordinates
parallel execution by GPT-6 Astra workers at low reasoning effort, owns shared
contracts and device/deployment control, and independently reviews and verifies
the results. Optimize speed and efficiency through bounded file ownership and
parallel work within the current phase; retain its acceptance gates before
advancing. Workers do not self-approve, deploy or merge their own output.
