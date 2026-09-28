# Proactive contributions from past notes: MVP implementation plan

September 28, 2026. Planning base: main `d45e7a6`. No feature code or provider calls are delivered by this plan.

## Agreed outcome and boundaries

Founder decision: make unsolicited, useful text contributions grounded in past notes the next MVP feature, with an App Store release desired before the YC application. Calendar, email, messages and outside-knowledge retrieval stay in the [full product vision](product-source-of-truth.md); they are not requirements for this feature. The exact positioning remains **AI notes that proactively contribute to discussions**.

A successful moment: during deliberate capture of a relevant conversation, the app surfaces “You mentioned trouble sleeping last week. It might be worth bringing up now.” The prior statement, subject and date must be supported. This is a reminder, not a diagnosis. Useful study/work connections are equally in scope; no exclusive launch audience has been selected.

Implementation choices below are engineering proposals to verify, not proven quality or additional founder decisions. Preserve microphone capture, saved notes, ordinary Ask, one main chat and existing navigation. No silent recording, spoken interruptions, external actions or new source connectors. App Store submission and production deployment are separate from checkpoint merge authorization.

## Proposed experience

- Deliberately start capture. Show a visible per-session “Suggestions on” state with a Quiet action; explain the feature on first use. Proactive analysis never starts outside an active capture. Default-on during deliberate capture is a proposed UX, not permission for background recording.
- Founder clarification: surface each proactive contribution as an ordinary agent message in the existing main conversation, using the same bubble, typography and interaction behavior as other agent replies. No separate suggestion card, badge, label, dismiss control or interaction flow. Do not fabricate a user question or add a repeated author heading. Keep regular message typography and source provenance internally, consistent with release chat's hidden-citation contract.
- Permit a follow-up through the existing composer. A proposed session-level Quiet control can stop further proactive messages without stopping capture; it is not a separate interaction on each message. Do not jump the scroll position when the user is reading older messages; show a new-message affordance instead.
- Begin with foreground delivery. Going to the background cancels pending contribution work; existing capture continues according to its verified lifecycle. Returning evaluates only fresh context, without a backlog of stale interjections. Locked-screen proactive delivery is not established by existing background audio support.
- Fail quietly for a single analysis failure, but distinguish unavailable suggestions from intentional silence with a discreet status if the feature cannot operate. Capture and typed Ask remain usable. No repeated error cards, automatic paid retries, notification spam or vibration on each transcript update.

## Processing path and responsibilities

1. **Observe stable conversation updates.** A dedicated coordinator consumes committed/revised transcript events from `App/Sessions/SessionController.swift`. Track capture ID, owner, transcript revision/cutoff and a local generation counter. Never analyze composer dictation as meeting audio. Avoid calls on every interim token.
2. **Build a bounded live context.** Use recent finalized text plus enough earlier context to interpret the subject and what has already been covered. Begin with a small recent window and a hard input limit; measure misses before expanding. Do not summarize the entire conversation with another paid call at every tick.
3. **Retrieve prior evidence locally.** Reuse `Backend/notes_recall.py:collect`, excluding the active capture. Derive the initial search input from stable recent text, without creating a fake chat question. Notes guide discovery; original passages and validated retained claims ground factual content. Cap candidates and include relevant correction context. Empty results end the attempt without a model call.
4. **Judge and draft.** Compare the two routes below with identical captured context and candidates. The chosen route returns either `silence` or one short contribution with evidence IDs. No forced contribution when evidence is weak.
5. **Revalidate and save.** Recheck owner, source lifecycle, current transcript revision, enabled state, capture activity and duplicate key before atomic persistence. Reject expired results. Source validation is not proof that the model phrased every fact correctly; the quality screen also reviews entailment and unsupported additions.
6. **Deliver once.** Send an explicit contribution event to the native controller. Use a durable unique ID so reconnect/history refresh cannot create a second bubble. Persist as an assistant contribution, not as an invented user/assistant pair. Duplicate-suppression and session Quiet state survive reconnection.

Application code owns access, date arithmetic, cancellation, budgets, revision checks and delivery. Model judgments assess semantic relevance and whether something is already addressed. Unknown speakers remain unknown. Neither summaries nor generated contributions become independent evidence of user biography.

## Jev and LLM comparison

| Candidate | Calls after local retrieval | Purpose |
| --- | --- | --- |
| A: LLM baseline | One bounded Luna decision-and-draft call | Choose silence or produce a supported short contribution. |
| B: Jev-assisted | One Jev request with independent relevance/novelty judgments, then at most one Luna draft call | Test whether selective drafting improves usefulness or reduces total cost despite the extra decision call. |

Do not call the current `NotesFirstRecall.prepare` unchanged for this comparison: it already invokes Jev ranking and would contaminate the LLM-only baseline. Reuse local collection and source validation separately, while leaving existing Ask retrieval unchanged.

Jev is optional and must earn its role. Include an explicit none/uncertain outcome; confidence is not a correctness guarantee. Batch independent questions over the same bounded state, but never treat parallel judgments as if one consumed another's result. Pin the evaluated model version, disable SDK automatic retries and record actual token use. If B adds no demonstrated value, ship the simpler A path. Do not enable the previously rejected pre-retrieval gate.

Research basis: [TypeSafe structured decisions](https://docs.typesafe.ai/concepts/system-one), [batching](https://docs.typesafe.ai/patterns/fan-out), [confidence](https://docs.typesafe.ai/confidence), and our [historical gate screen](memory-gate-screen.md). Current documentation supports capability, not this product's accuracy or latency. The September 28 research found sparse recent evidence, with no verified end-to-end proactive-note outcome. Verify provider contracts again when implementing an adapter.

## Proposed state and service contract

Keep this a small module in the existing service, not a new microservice or memory rewrite. Proposed files include a native `ProactiveCoordinator.swift` and backend `proactive_service.py`, `proactive_policy.py` and provider adapter; final names follow actual responsibilities.

Request: authenticated owner (resolved by server), capture ID, attempt ID, transcript revision/cutoff, enabled generation and bounded current context. Never accept an arbitrary owner from the payload. Reuse existing validated live-source schemas where possible.

Result: `silence`, `contribution`, `unavailable` or `cancelled`; bounded reason code, contribution ID/text when present, internal evidence references and evaluated cutoff. Keep diagnostic reasons out of ordinary bubbles. Validate schema, lengths and allowed evidence IDs before accepting output.

Proposed scheduling hypotheses: wait for a stable finalized update, at least 20 seconds between attempts, one in flight, and at least 60 seconds between visible contributions. No new text means no attempt. These are starting values for replay/QA, not claims about ideal timing. Coalesce incoming updates, invalidate incompatible revisions, and use only the latest eligible window. Do not queue missed contributions. Generation deadlines and session caps are explicit configuration with conservative defaults.

Persist contribution kind/context separately from user-authored turns, adapting `companion_chat.py` and `CompanionConnection.swift` without breaking old histories. Ordinary note deletion continues to preserve historical messages while removing unavailable links; invalid pending evidence must be discarded. Eligible retained memory remains subject to the existing retention contract, not an implicit new erasure policy.

## Delivery checkpoints

| Checkpoint | Implementation and evidence | Exit condition |
| --- | --- | --- |
| 1. Contracts and reproducible cases | Freeze positive/negative fixtures, event schema, cadence and metrics. Build a local replay runner using isolated synthetic data. | Expected outputs are reviewed before prompt tuning; no production state or paid calls. |
| 2. Bounded backend path | Local discovery, A/B adapters, silence handling, source validation, budgets, cancellation and idempotent persistence. Exercise actual local socket/storage behavior using replayed provider responses. | Supported fixture contribution delivered once; invalid/stale/duplicate attempts suppressed; Ask and deletion contracts intact. This proves plumbing, not model quality. |
| 3. Bounded live model screen | Execute the exact small matched screen below, preserve requests/responses and score quality, latency and cost. | No harmful false contribution in mandatory negatives; positive case works; choose a route or record inconclusive evidence. No automatic extension or threshold tuning on only the winning example. |
| 4. Native integration | Wire capture updates, foreground lifecycle, main-chat contribution display, session Quiet and ordinary chat follow-up and unavailable status. Consult Libraries.dev against native compatibility and established styling. Run actual Mac/simulator app with replay and inspect screenshots/interactions. | No phantom user message, scroll jump, duplicate, lost draft or capture interruption; readable/accessibility and reduced-motion behavior verified. |
| 5. Physical acceptance and staged rollout | On readiness, exercise the chosen route during one short consented iPhone conversation using existing test notes, then quiet/stop/reopen. Verify matching service deployment only after rollout authorization. | Real-path result recorded; pending work stops, capture persists and history reopens. Prior simulation/provider-only evidence is not physical acceptance. |

Each meaningful checkpoint gets a focused PR, diff review, reproducible evidence, known limits and required checks. Merge only its verified bounded scope. Keep runtime feature disabled until rollout gates pass; rollback disables contributions while preserving capture, notes, Ask, historical messages and usage accounting.

## Frozen acceptance cases

- Positive: the sleeping concern is relevant now, supported and not yet discussed. Show one qualified reminder.
- Positive: an earlier lecture's relevant concept helps a study discussion without a typed question.
- Silence: unrelated discussion or empty library.
- Silence: the current conversation already covered the fact, or the same suggestion was delivered.
- Silence/qualification: unclear subject, quoted example, wrong person, corrected claim or obsolete event; never turn another speaker into the user.
- Cancellation: Stop, Quiet, owner switch, background, revised transcript or changed source invalidates a pending result.
- Reliability: reconnect/replayed event yields one durable contribution; failure preserves capture and draft; no catch-up burst after returning.
- Untrusted input: a note/transcript telling the app to ignore instructions cannot alter access rules, evidence scope or the contribution policy.

Run the full contract suite with local fixtures. For model evaluation, record expected contribution/silence, evidence support, relevance, novelty, appropriate tone and timing; measure total provider calls, tokens, cost and time from stable transcript to display. Source checks and zero duplicates are hard requirements. A tiny screen does not establish recall across all conversations or product-market fit; measure missed useful moments and distraction in a later pilot.

## Approved budget and verification limits

Founder approved **up to $0.25 and at most 12 live model calls**, stopping at whichever limit is reached first, with **no automatic retries**. This is a new isolated feature-validation allowance, not reuse of an older grant or an increase to production quotas. No calls are spent by this plan. Reserve conservatively before each call; count failures/attempts and every hidden ranking/verification call; reconcile usage afterwards without erasing previous charges.

Proposed allocation: three matched cases (one useful connection, one already-addressed case, one wrong-person/corrected case), each with A's one LLM call and B's Jev plus at most one LLM call: **at most nine calls**. B silence uses no drafting call; do not spend savings automatically. Reserve the remaining **at most three calls** for integrated model-path confirmation if the comparison warrants it and the dollar cap allows. This screens feasibility; it is not a statistically meaningful A/B benchmark.

No new paid transcription or ongoing runtime usage is funded by this model-call allowance. Local/synthetic replay needs neither. Before physical QA, check the remaining authorized transcription capacity; obtain a separate bounded allowance if needed, then explain the physical steps and wait for explicit readiness. Do not start a timed check based on general implementation approval. If the model screen is inconclusive or budget expires, stop live spending and report the missing evidence.

## Separate App Store readiness work

The feature's first verified foreground slice is not launch readiness. Longer real-session capture/recovery, defined background behavior, account/sign-in and ownership, explicit data/account deletion, privacy disclosures, cost limits and distribution need their own verified checkpoints. Subscription implementation depends on the chosen launch offer. Keep these visible before submission; calendar/email/message connectors and outside retrieval can follow the MVP.
