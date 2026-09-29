# Demo to invited TestFlight pilot

Founder direction, September 29, 2026: prioritize a complete useful demo, targeted failure recovery, bounded proactive behavior, then TestFlight for friends/family with students as the first focused learning cohort. Use pilot evidence to develop the YC application together. Pause open-ended wording optimization; keep its known failures visible. Preserve the agreed one-liner: **AI notes that proactively contribute to discussions**.

This is a delivery plan, not release acceptance. Existing capture QA is reusable within its documented scope. Current source inspection shows Debug-only proactive enrollment, preview sign-in/account flows, and the documented five-minute capture cap. Do not equate founder-device provisioning with independent tester onboarding.

## 1. Complete useful demo

Outcome: demonstrate that something captured earlier helps a later conversation.

Use a short, explicitly fictional student scenario: record a study plan with a changed time/location; finish and reopen the saved transcript/notes; start a related discussion; receive a grounded proactive reminder; ask a follow-up in the same persistent chat. Show Quiet and reopen the conversation to verify durability. Label seeded/simulated data and cached model playback accurately. A deterministic UI rehearsal cannot stand in for an actual model demo.

First checkpoint: inspect and run the existing saved-event/service/native paths, identify missing wiring, and fix only reproducible blockers. Reuse prior physical microphone evidence; reserve a final bounded real-provider/device check for the complete path once local rehearsal works. No scripted agent answer presented as live reasoning. No new paid allowance is implied.

Acceptance: one continuous app flow, correct past source, relevant contribution, grounded follow-up, preserved recording/chat after reopen, and visible user control. Preserve accepted UI; wording polish is not this slice's acceptance gate.

## 2. On-device notes, failure handling and diagnostics

Persist meeting summaries on the phone so they open immediately and remain readable offline. Revalidate on app activation/note open without blanking cached content; coalesce refreshes and respect owner, revision and deletion boundaries. See the phased plan for acceptance.

Exercise denied permission, lost network/provider failure, interrupted capture, failed note generation and failed chat. For each: saved content and draft survive where supported; the displayed message states what happened and what can be done; retry is explicit and cannot create duplicate records or unexpected inference calls. Avoid content-heavy logs. Inspect actual UI recovery with saved events before requesting physical checks. Audit existing tests first; add coverage only for gaps/regressions.

Acceptance: reproducible failure matrix with expected versus observed data retention, user feedback and recovery. Existing microphone/lock-screen QA is historical evidence, not a claim of newly tested full-lecture reliability.

## 3. Bounded proactive pilot behavior

Carry forward deliberate capture, Quiet, cooldown, stale-result rejection and bounded inference. Verify these in the distribution configuration rather than relying on Debug launch arguments. Define account/session budgets and clear exhausted/disabled behavior. Record useful/missed/irrelevant contributions without silently collecting private conversation content.

Known unresolved issue: v4 and the current-focus candidate can interrupt a constellation discussion with a same-club budget fact. Jev's separate gate has not been evaluated on that case and has missed other positive cases. Do not call this solved, silently enable the experimental route, or require perfect prose to investigate the actual relevance boundary.

Acceptance: explicit limits and controls work, no late or duplicate contribution after cancellation, and pilot users are told proactive behavior is experimental. Any remaining relevance limitation must be explicitly assessed before inviting testers.

## 4. Invited TestFlight readiness

Audit signing/App Store Connect setup, install/update behavior, production configuration, and independent per-tester enrollment/ownership. Decide the smallest workable private-pilot access flow; do not build full subscriptions merely to distribute a beta. Verify data isolation, sign-out/access revocation and documented data removal. Replace nonfunctional preview paths with working pilot behavior or clear unavailable states. Provide feedback and diagnostic instructions.

The five-minute cap must be visible. For an initial short-session pilot, disclose it; supporting full lectures is a separate duration/cost/recovery checkpoint. Do not silently raise it. Check current Apple distribution requirements before archive/upload. TestFlight upload and invitations are separate delivery actions; do not contact friends/family without explicit authorization.

Acceptance: a fresh tester can install and access only their own data without a developer-attached phone; provider secrets are absent from the app; release configuration exercises the intended demo; pilot instructions describe actual limits.

## 5. Student learning, then YC

Friends/family can expose installation and usability problems. Students are the first focused product cohort because the founder can reach them; this is a founder choice, not validated demand. Ask what was useful, what interrupted, what failed, and whether they voluntarily return. Distinguish observed use from enthusiasm and model test pass rates. Use concrete learning and an honest product demo in the YC application; connected sources remain future scope.

## Execution boundaries

All historical provider allowances, including the latest current-focus six-call/$0.12 grant, are exhausted. Local fixtures, tests and inspection can proceed without a new grant. Prepare any necessary paid verification before requesting a bounded allowance. Physical checks requiring founder participation wait for explicit readiness. Keep failed prompt experiments out of a verified release checkpoint. Start implementation checkpoints from latest verified main and use focused PRs.

## Parallel execution

The [phased orchestration plan](execution/demo-testflight-phases.md) defines worker ownership, dependency gates, resource limits and the first dispatch wave. Use the [worker packet](execution/worker-packet-template.md) and [verifier specification](execution/verifier-contract.md). These are prepared execution artifacts; workers have not been launched. The verifier foundation is now implemented as an orchestrator prerequisite; see its usage and verification evidence.
