# Orchestrated demo → TestFlight delivery

Status: proposed execution plan, September 29, 2026. No workers dispatched by this document. Founder authorizes preparing parallel execution around a chief-of-staff/orchestrator role, with GPT-6 Astra workers using `low` reasoning (the available setting corresponding to “light”). The deliverable remains **AI notes that proactively contribute to discussions**. [Product](../product-source-of-truth.md), [engineering principles](../engineering-principles.md), and [delivery scope](../demo-to-testflight-plan.md) govern every packet.

## Outcomes and operating rules

Deliver a truthful, continuous student demo; recover gracefully from common failures; bound proactive behavior; distribute an independently usable invited beta; learn from students. Existing capture is a foundation, not a rewrite target. Calendar/email/message integrations, subscriptions, redesign and open-ended personality work are outside this critical path.

The orchestrator owns scope, dependencies, assignment, shared contracts, budgets, reviews, integration and release evidence. Workers own complete bounded changes and the verification of their claims. A reviewer must inspect actual behavior/evidence, not merely approve passing unit tests. Human judgment remains necessary for subjective usefulness and device scenarios that cannot be independently exercised.

Use separate worktrees/branches for implementation. Default maximum: three active workers plus orchestrator, with fewer when native build/device resources are occupied. Separate app threads require explicit user authorization to create them; the founder's future execution preference is not a command to launch them now. Once dispatched, coordination messages may be sent within that explicitly authorized workflow. Do not independently create extra workers or expand scope from a packet.

## Phase 0 — establish a trustworthy starting point

Goal: remove ambiguity before workers change the app. No paid provider calls or user-device interaction required.

| Packet | Owner | Work | Result |
| --- | --- | --- | --- |
| P0-A | Orchestrator | Resolve latest verified main, current native build, deployed backend, flags and exhausted budgets; separate experimental branch from release baseline | Release/baseline manifest with commit/build IDs and evidence dates |
| P0-B | Worker 1 | Inventory existing capture, notes, chat, proactive and recovery checks; identify actual gaps | Updated feature evidence map and exact reusable commands |
| P0-C | Worker 2 | Read-only TestFlight readiness audit: signing, release configuration, tester enrollment and preview flows; consult current official requirements | Concrete blocker list, proposed smallest private-pilot access path, no upload |

Exit: baseline manifest reviewed, first demo specified, file ownership assigned, shared interfaces frozen for the first wave. Dated documentation is not live-service evidence. P0-C reports missing account access instead of changing credentials or enrolling testers.

## Phase 1 — verification foundation and deterministic demo rehearsal

Depends on Phase 0. Parallel with non-mutating release preparation.

| Packet | Owner | Work | Acceptance |
| --- | --- | --- | --- |
| P1-A | Worker 1 | Reuse saved events to rehearse capture completion → notes → related discussion → proactive message → follow-up → reopen in the app | Runnable rehearsal, screenshot/result evidence, fixtures explicitly labeled; no fake live-model claim |
| P1-B | Worker 2 | Implement the small verifier runner/evidence receipt defined in verifier-contract.md | Offline by default; fixture checks run; missing required evidence blocks readiness; failing child command produces failure |
| P1-C | Worker 3 | Plan independent tester access and release configuration against actual code | Contract and isolated implementation packet ready; unresolved product/access choices surfaced, no speculative auth rewrite |

The orchestrator edits the shared feature map and owns any shared fixture contract. Workers submit entries rather than all editing the same map. P1-A supplies the stable demo fixture contract before P1-B integrates it; the runner can be built against a minimal fixture first.

Exit: a reproducible local app rehearsal and targeted verifier command. This is not the real-provider demo milestone.

## Phase 2 — harden the three release workstreams

Depends on Phase 1 contracts; independent scoped checkpoints may merge as they pass.

| Packet | Ownership boundary | Work | Acceptance |
| --- | --- | --- | --- |
| P2-A: recovery and local notes | Assigned native controller/view/cache files and UI tests | Persistent on-device summary cache, then permission, interruption, network failure and failed notes/chat recovery | Cached summaries render immediately/offline and survive reopen; refresh never blanks valid content; failure UI preserves data and drafts; no duplicate retry |
| P2-B: proactive limits | Assigned backend policy/service/config files and tests | Quiet, cooldown, stale-result rejection, per-session/account limits and distribution-compatible activation | Cancellation/expiry/quota tests plus actual local socket execution; failed candidates remain unselected |
| P2-C: beta access | Assigned enrollment/config/account files and tests | Implement the selected minimal per-tester access, isolation and revocation flow; remove misleading preview paths from pilot navigation | Two isolated test users, fresh install/enrollment, revoked access, no provider secret in bundle |

P2-A and P2-C must not simultaneously edit a shared controller/view: split exact files or serialize the overlapping commit. Backend identity/enrollment changes touching P2-B's admission contract require an orchestrator-approved interface before either worker implements them. Schema migrations are serialized and have one owner.

Handle the known unrelated-interjection bug as a named acceptance risk with a bounded evaluation, not an unlimited prompt loop. Paid work needs a separately approved ledger allocation. Relevance acceptance is distinct from deterministic timing/control acceptance. Wording polish is deferred. Do not automatically ship Jev because the architecture is available.

Exit: reviewed recovery, control and access checkpoints; remaining relevance/duration risks explicitly recorded. A red acceptance criterion cannot be renamed a limitation to pass this gate.

## Phase 3 — integrate and verify the real demo

Depends on all demo-relevant Phase 2 checkpoints. Orchestrator serializes integration; workers resolve failures in their own areas.

1. Integrate reviewed commits onto latest verified main; rerun changed contracts and one app rehearsal.
2. Build the intended distribution configuration and inspect actual UI; verify proactive activation does not depend on Debug-only arguments.
3. Prepare one short real-provider demo with an approved spend cap. Capture earlier context → finish/save → related conversation → useful contribution → follow-up → reopen. No prerecorded answer represented as live reasoning.
4. Verify Quiet/stop do not deliver a late message and failure recovery remains reachable. Physical participation waits for founder readiness; do all independent checks first.
5. Produce a release-candidate receipt: exact native/backend versions, scenario, outcome, logs/screenshots, spend, unresolved limits and rollback.

Exit: an honest end-to-end demo on the candidate build. Reuse historical microphone evidence only for unchanged paths; do not claim a new physical flow from fixtures. A prompt/provider change invalidates semantic evidence for that changed path, not every unrelated UI check.

## Phase 4 — TestFlight release candidate

Readiness research and metadata drafts can run earlier; archive/upload follow the integrated release gate.

- Orchestrator owns final archive, version pairing, backend enablement and rollback. One release operator; no concurrent deployments.
- Verify fresh install/update, per-tester access, data separation, feedback path, privacy/data explanations and known limits against the actual candidate.
- Keep the five-minute cap explicit until a separate longer-session checkpoint is approved and verified. A short-session beta must not be described as full-lecture capture.
- Confirm current Apple requirements and available distribution access. Prepare review/build information before requesting any missing access or approval.
- Obtain required release action authorization for upload/enabling users; send no tester invitations without explicit permission. Never share production credentials among testers.

Exit: usable invited TestFlight build, matching verified backend, clear short-session instructions and a feedback channel. Public App Store release is outside this plan.

## Phase 5 — student pilot and YC evidence

Friends/family first reveal installation/usability problems; students are the focused product cohort. Capture consented feedback on useful reminders, irrelevant interruptions, missing context, failed recordings and voluntary return use. Define collection/retention before adding telemetry; no silent transcript collection. Separate observed behavior from enthusiasm.

Deliver: reproducible issues, prioritized fixes, actual usage/feedback evidence, updated demo and an honest YC product answer written with the founder. Do not manufacture traction or extrapolate model pass rates into user value.

## Integration and throughput policy

- Dispatch packets small enough to yield one independently reviewable behavior; avoid multi-day “own the entire backend” assignments.
- One writer per file/contract; explicit handoff for overlaps. Shared data migrations, deployment configuration, runtime budgets and release flags are serial resources.
- Each worker gets its own checkout, DerivedData/result directory and ephemeral test storage. Lease the simulator/device; do not run competing UI automation against it.
- Workers report blockers immediately and submit commit + evidence; the orchestrator provides concise milestone updates and batches nonurgent founder decisions.
- Rebase/check impacted integration contracts after shared changes. Merge only verified checkpoints under repository protections. Never batch several unverified branches into a release to save time.
- No nested delegation, production mutation, paid retries, quota increases or real-user seeding without packet authorization. Reuse cached outputs for mechanics; never report them as fresh model behavior.
- On failure, preserve the last working build and exact failing fixture. Diagnose at the affected layer; avoid broad reruns or paid transcription for presentation bugs.

## Budget and escalation

All prior provider grants are exhausted. Default packets have zero paid-call allowance. The orchestrator alone allocates a new founder-approved bounded budget, with named cases, per-call reservations and one ledger; workers cannot share a grant by assumption. A pending access/permission decision stops its dependent work. Independent work may proceed only where the canonical blocking rule and the founder's authorization permit it; never route around a denied prerequisite.

Escalate only a concrete decision: what action, why needed, cost/scope, prepared artifact and consequence of waiting. The orchestrator must not make the founder relay logs or perform checks agents can run.

## First dispatch wave

After execution is explicitly started: orchestrator P0-A; Astra/low workers P0-B and P0-C. No app changes, device use or paid calls in that first wave. Use their findings to assign Phase 1 implementation packets with exact file ownership. This avoids launching three overlapping feature rewrites from stale documentation.

## Founder clarification: autonomy with real verification

Workers have autonomy to implement, diagnose routine failures, run authorized checks and iterate within their packet. Their responsibility includes real behavior, not merely code and automated tests. They cannot advance dependent work past an unverified required behavior. The orchestrator enforces the same gate before integration and release.

LLM workers require an explicit bounded provider allocation and fresh final-configuration output inspection, followed by application-pipeline verification. The active-path check must prove provider → parsing/validation → persistence → client delivery when the checkpoint claims that entire flow; provider-only evaluations remain narrower evidence. Do not require every worker to repeat unchanged physical capture tests or every paid evaluation: match checks to the claim and reuse valid receipts.

Founder is willing to approve further spending, but this clarification does not specify a new dollar/call cap. Prepare and batch concrete budget requests by checkpoint, centrally reserve named allocations and stop at either cap. Within that approved scope, no per-call reconfirmation is needed. No automatic paid retries or using another worker's allocation. See the updated worker packet and verifier contract.


## On-device meeting-note summaries — founder requirement

Add to P2-A as its first independently reviewable slice. Persist successfully fetched/generated summaries on the phone, scoped to the authenticated owner, recording ID, transcript revision and summary-generation version. Keep the backend as the canonical source; opening a note reads the local copy immediately, without requiring network or another LLM generation. Do not add a second note-generation path.

Revalidate when the note opens and when the app becomes active. Proposed implementation policy: coalesce duplicate requests, refresh the visible note first, and avoid a full-library fetch on every foreground transition. Refresh cached library entries only where needed for the displayed list or when sync signals changed revisions. This is an implementation hypothesis to validate, not an arbitrary periodic timer requirement.

A network failure preserves the usable cached summary and offers clear retry/status feedback. Do not replace content with a spinner during background refresh. Match source revision before displaying a summary as current; a known changed/deleted source must not silently present old content as current. A successful refresh atomically replaces the cache. Never overwrite a valid summary with a transient pending/error response. Clear the appropriate entries on note deletion, owner switch/sign-out and explicit data reset; never display another user's cached content. Use platform-protected app storage and keep private contents out of diagnostic logs.

Acceptance includes actual app launch/open, airplane-mode or injected offline read, relaunch persistence, successful background update, failed refresh preserving content, changed/deleted revision behavior, and owner isolation. Reuse saved summary/server fixtures for these cache mechanics; paid note generation is unnecessary unless the generation integration changes. Submit UI screenshots and reproducible state/persistence checks. The worker's packet must identify affected files and avoid overlapping P2-C account ownership changes; agree the cache-clearing contract first.

## Orchestrator acceptance and continuation gate

Each worker sends its completion packet to this orchestrator. The orchestrator inspects the exact commit/diff and raw evidence, verifies that the commands/artifacts support every claimed outcome, and reruns targeted checks when needed. Model output is judged against the predeclared rubric, not the worker's pass label. A review does not automatically consume another paid call; reuse valid receipts unless an unresolved question requires fresh evidence and allowance.

Record one disposition: accepted for integration, changes required, or blocked. Only after acceptance does the orchestrator explicitly authorize the next dependent packet. Worker self-declaration, a green suite, or a PR creation is not that authorization. Workers may complete already-authorized independent work and fix their own failures; they may not expand scope or advance dependent work while acceptance is pending. Review and acceptance do not independently authorize deployment.
