# Engineering direction and agent feedback loop

Status: Canonical engineering source of truth, explicitly designated by the founder September 24, 2026. Swift/SwiftUI is the accepted working direction, subject to validating the development workflow. The native foundation workflow has been exercised; no provider benchmark has been completed. See development.md for the bounded verification evidence.

## Authority and application

This document is the canonical source of truth for how we engineer this product. Apply it to stack selection, architecture, implementation, tooling, debugging, testing, review, and delivery. The [product source of truth](product-source-of-truth.md) defines what we are building; this document defines how we build and verify it. The [V0 scope](v0-scope.md) defines the current release boundary.

All implementation plans and changes must follow these principles. Supporting research and vendor recommendations do not silently override them. A later explicit founder decision may revise them; record that revision here and update dependent guidance. If requirements conflict or a material departure is necessary, make the conflict explicit rather than treating an exception as the new standard. Routine implementation choices within these principles do not require repeated approval.

Concrete technology choices below retain their stated provisional status. Canonical principles do not turn an untested stack or provider into a validated decision.

## Shared native codebase

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
