# V1 implementation plan — companion on tap

> Historical/bounded delivery document. The [current product definition](product-source-of-truth.md), [current state](current-state.md) and [release handoff](execution/testflight-release-handoff.md) govern positioning, selected implementation and the current sequence. The September 28 gap audit is historical. Older one-liners, exclusions and pending stages below retain their original checkpoint meaning.

Status: checkpoints 1–3 and 5 verified, including physical-iPhone Ask while listening and speech captured after the answer completes. Jev checkpoint 4 is deferred by founder decision. Checkpoint 6 is complete for the founder-only internal trial; see [final acceptance](v1-acceptance.md) and [runbook](v1-runbook.md). Preserve the five-minute cap and monetary budgets. See [live Ask evidence](v1-live-ask-validation.md) and [Jev decision](v1-jev-decision.md). Canonical authorities remain the product source of truth and engineering principles.

## Outcome

An iPhone user starts listening, puts the phone away, and later opens the conversation and taps Ask. The companion answers from what it has heard so far without requiring a recap. The same interaction works after recording stops. GPT-6 Luna interprets the question and generates the response directly using the versioned [companion personality and behavior prompt](../Backend/prompts/companion-v1.md). Founder selected Luna on September 24, with reasoning explicitly off (`none`) and Standard processing to prioritize quick responses; this supersedes the earlier Flex choice. No comparative model testing is planned. Saved-conversation latency has bounded integration evidence; see the operating contract for request limits and the no-upgrade/no-retry policy.

Consumer positioning: an iPhone-first listening companion that understands the conversation—and, over time, the context of your life—so you can turn to it without starting from scratch. V1 delivers the current-conversation portion. The PBN foundation and one-liner remain unchanged: “Granola with an AI that listens alongside you and can join the conversation.”

## Scope and boundaries

Included:
- iPhone operation independent of the Mac, with repeated sessions and bounded paid usage.
- User-started microphone capture continuing while locked/backgrounded, explicit recording state, safe interruption handling, and saved reopening.
- Explicit in-app Ask, typed questions, and text answers during/after the selected conversation.
- Direct Luna answering for recall, summary, perspective and mixed questions; no Jev dependency.
- Inspectable transcript references for claims about the conversation; clear separation of the companion's suggestions from statements in the transcript.
- Local session and Q&A history, deletion, and the existing best-effort speaker labels.

Deferred: Jev routing, voice questions/replies, proactive interjections, automatic memories, past-conversation retrieval, task execution, web browsing, computer audio, cross-device sync, Watch/AirPods controls, and public billing/distribution. A mascot is a design exploration, not a delivery dependency. Ask from the Lock Screen and starting capture from outside the app are separate enhancements; V1 starts in-app and supports locking afterward. No promise of recording through phone calls or continuing after force-quit.

## Checkpoint 0 — settle the operating contract

Confirm the smallest authenticated backend/hosting option, a development spending cap, and access to the selected answer model, GPT-6 Luna. Prefer the existing Swift apps and relay boundary; change stack only for an evidenced need. Research current official API behavior, pricing, and retention before choosing. Credentials remain server-side. Do not promise on-device processing: cloud services receive audio or selected text even when transcripts are stored locally.

Proposed initial trial boundary: invited users, one active recording per user, configurable duration/daily usage caps, and clear cap messages. Preserve V0's five-minute limit until longer capture is deliberately verified. A 30-minute maximum is a proposed first practical target, not an approved unlimited-recording promise. Define exact duration and budget before the corresponding paid run.

Output: a short decision record with request/data flow, authentication/revocation, retention/deletion responsibilities, expected per-session spend, and numeric responsiveness/evaluation targets set before measuring. Ask the founder only for decisions/access/costs that cannot be resolved from existing authorization. Pause for those blockers.

## Checkpoint 1 — independent, repeatable iPhone sessions

Replace the Mac-dependent development connection with an authenticated service reachable directly from the iPhone. Keep provider credentials off-device, validate usage on the server, bound concurrency, and clean up disconnected sessions. Retain the working provider adapter and transcript/storage contracts. Use separate transcription and Ask budgets; no unbounded retries. Mac compatibility remains maintained through shared contracts without requiring every new iPhone interface feature on Mac.

Acceptance:
- Physical iPhone records, stops, saves, and starts another session with the Mac relay off.
- Revoked/invalid credentials and exceeded limits fail clearly before provider spend.
- Cancellation/disconnect releases connections; usage accounting prevents duplicate or runaway requests.
- Configuration and release artifacts do not contain provider keys.

QA: local server fixtures for authorization/quotas/cleanup; one bounded real-device integration only after explicit founder readiness. Deployment is a separately identified action with its access/cost decision resolved first.

## Checkpoint 2 — pocket-ready capture

Add background/locked-screen capture, explicit visible recording status, and a straightforward Stop path. Choose the simplest supported status/control surfaces; validate any Live Activity lifecycle independently rather than treating its presence as proof of active audio capture. Model recording, interrupted, reconnecting if supported, stopped, and finalizing honestly. For V1, safe stop with a marked gap and explicit restart is acceptable; seamless automatic resume is not required.

Acceptance:
- Start in-app, lock the phone, speak, unlock, stop, and verify the actual spoken content and saved result.
- Calls/audio interruptions and input removal do not silently imply continued capture. Preserve received text and expose the interruption.
- Explicit Stop ends capture and billable streaming; background status ends too.
- A bounded longer recording verifies duration, storage growth, battery/resource observations, and finalization before increasing the cap. No endurance claim from short tests.

QA: cached/replayed events for status UI, local microphone checks for route lifecycle, and a tightly budgeted real background capture for end-to-end proof. Wait for founder readiness before locks, calls, speech, or other manual triggers.

## Checkpoint 3 — direct Ask on a saved conversation

Use the verified direct Luna baseline. Tap Ask, type a question, receive a streamed text answer from the selected conversation. Preserve question/answer history within that session. Use stable transcript passage IDs and a bounded context snapshot; references open the cited passage. Unknown information should produce an honest limitation rather than an invented answer. Perspective questions may request general reasoning, but that reasoning must be distinguished from transcript facts.

Acceptance:
- Recall, summary, and perspective requests work through the direct path.
- References resolve to actual session passages and support the associated transcript claims in reviewed examples.
- Missing information, wrong-conversation context, unassigned speakers, quoted malicious instructions, cancellation, and provider failure are handled without fabricated evidence or lost transcript.
- Session deletion removes associated local Q&A. App relaunch restores the saved conversation and answer history.

QA: versioned synthetic conversations and fixed questions, local UI/provider-event replay, then bounded functional QA of the selected Luna integration, without a comparative model evaluation. No new transcription needed. Validate reference existence in code; support/faithfulness also requires semantic review, not just valid IDs. Select the simplest context strategy that fits the bounded session; do not silently discard earlier conversation when limits are reached.

## Checkpoint 4 — Jev judgment layer (deferred by founder)

The following is the historical evaluation plan, not an active V1 requirement. The founder accepted deferral September 25 after reviewing the failed quality gate. See [decision and evidence](v1-jev-decision.md).

Use Jev Choice for one narrow decision per Ask: recall, summary, perspective, or mixed/uncertain. Input is the question plus bounded same-session context where needed. Application code chooses the answer policy; Jev does not generate prose, store memory, or certify truth. The fallback can use the direct grounded-answer path without blocking the user.

Evaluate before enabling routing: use a small labeled set covering ordinary questions, ambiguous requests, mixed intent, and attempts to manipulate the routing. Separate examples used to develop the prompt from a held-out evaluation. Pin the model/question version and set thresholds before the held-out run. Compare routed versus direct answers for route correctness, harmful routing mistakes, answer quality, total response latency, and total cost. Do not equate model confidence with correctness. Start with one judgment per explicit Ask, not repeated calls on every transcript update.

Acceptance:
- Correct routing on the predefined cases, with explicit treatment of mixed requests.
- Jev outage, timeout, malformed response, and uncertainty trigger the direct path without duplicate answer calls.
- Routing demonstrates a defined benefit without an unacceptable quality/latency regression. If it fails, report the failed result and resolve scope with the founder rather than forcing it into production or quietly removing the planned Jev role.

TypeSafe's official [introduction](https://docs.typesafe.ai/introduction), reviewed September 24, describes typed decisions rather than prose generation. Accuracy, price, and latency for this workload still need measured evidence. Future Jev decisions about whether/what past context to retrieve stay outside V1; a separate retrieval component would fetch the data.

## Checkpoint 5 — Ask while listening

Reuse the verified direct question/answer path during an active session. Each Ask gets an immutable transcript snapshot and an explicit context cutoff. Capture continues independently while a text answer is generated. The answer is not silently rewritten as subsequent speech arrives. Keep app/provider state separate so an answer failure cannot stop recording and a transcription failure is not hidden by a successful answer.

Acceptance:
- Physical iPhone records actual speech, answers a typed question about it, continues capturing later speech, then stops and reopens both transcript and answer history.
- Show when the most recent speech has not yet transcribed; never imply the answer includes unheard/unprocessed audio.
- References remain resolvable when partial transcripts are revised. Preserve the cited snapshot or version rather than pointing at unrelated replacement text.
- Stop during an Ask ends capture immediately; Ask cancellation does not cancel capture. Test these boundaries locally first.
- One active Ask per conversation initially; new asks wait or require deliberate cancellation rather than racing or duplicating spend.

This is the defining companion checkpoint: the user can turn to it without recapping the conversation. It does not require the model to listen for its name or interrupt autonomously.

## Checkpoint 6 — internal V1 acceptance and handoff

Run focused regressions appropriate to the final changes. Demonstrate the complete physical-iPhone path using an actual conversation and actual answer generation, with source references inspected. Test missing information and one representative failure alongside the happy path. Verify shared Mac build/core behavior to prevent regressions; full iPhone feature parity is not required.

Package the installed internal build, setup/runbook, evidence, known limits, and usage estimates. Record whether the companion's answer was useful without a recap. Do not replace practical usefulness with test counts or make an arbitrary questions-per-session threshold the sole acceptance criterion.

## Module boundaries and observability

Keep focused interfaces within the current codebase: audio capture; transcription adapter; transcript/session storage; context snapshot builder; answer client; UI. Server owns authentication, provider secrets, and enforced budgets. Add no vector database or general agent framework for a one-conversation scope.

Measure capture-to-first-text, Ask-to-route, Ask-to-first-answer, completion, cancellation, and provider usage with request correlation IDs. Avoid recording private transcript/question content in routine telemetry. Timing should distinguish network/provider latency from app handling. Keep paid test inputs explicit and bounded, retain reusable sanitized fixtures, and use no automatic paid retries.

## Checkpoint workflow

Branch → implement the smallest complete behavior → targeted QA and inspect evidence → focused PR → review → merge when acceptance passes. Founder has authorized routine verified checkpoint merges. Human-dependent QA requires an explanation and explicit ready signal; stop for permission, device, account, or spending blockers. Preserve failures and known limitations. This plan authorizes no implementation by itself; execution begins when requested.
