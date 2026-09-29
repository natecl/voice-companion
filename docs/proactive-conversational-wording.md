# Conversational proactive wording candidate

September 29. Prepared, not selected or deployed; no provider calls yet.

Founder found the actual 237-character Cedar reply too formal and dense, longer than the prior 178-character attempt. Character targets alone are insufficient. The v5 candidate removes the one/two-sentence constraint and soft numeric target, requests an ordered messages array with one conversational idea per item, and retains facts, qualifications and silence rules. The native renderer now displays those items in separate bubbles using the accepted styling and right margin. Examples use unrelated names/scenarios so the Cedar/Harbor evaluation is not an exact example copy.

Official [prompt engineering guidance](https://developers.openai.com/api/docs/guides/prompt-engineering) supports explicit instructions and examples; actual model output remains the acceptance evidence.

Prepared three live requests: Cedar prerequisite (five people/basic recording/before features/pending when recorded/calendar afterward), Harbor changed opening (Mina/step-free/upstairs stairs/first-floor option), and acknowledged Cedar (silence). Inspect complete outputs for direct conversational phrasing, separated ideas where useful, preserved qualifiers and no redundant conclusion. Reject a shorter answer that drops material facts. Measure character counts, but don't use length alone as the quality verdict.

The prepare_conversational_proactive.py export runs real local scheduling/retrieval/storage with synthetic decisions. Ten existing contract/readability/conversation tests pass; this is not live wording validation. Exported requests are under work/conversational-proactive/requests.json. The prepared provider runner requires the stopped-capture state and exactly five prior reservations, atomically reserves the remaining three existing slots ($0.06), refuses reruns and stops on errors without automatic retries. Reallocating those phone-test calls requires founder approval. Do not run or change runtime PROMPT until approved and actual outputs reviewed.

Physical test result before this candidate: one delivered Cedar reply, then three model_silence results (not merely duplicate suppression), with no active capture afterward. Harbor was not reached on the phone. Current server and production prompt remain unchanged.


## Separate-message capability

Founder explicitly asks for separate text messages and a working capability, superseding the earlier single-bubble presentation constraint. Opt-in `grouped_messages=True` selects the candidate prompt and strict messages-array schema. Validation rejects empty items, embedded newlines, missing evidence, nonempty silence, and aggregate content beyond the existing 600-character ceiling. It never truncates. The existing durable answer stores items separated by reserved blank-line boundaries; native proactive rendering displays each as a separate bubble. Ordinary replies remain intact. One durable contribution keeps the existing notification, cooldown, reconnect and duplicate semantics; each bubble has its own Copy action.

The feature is opt-in for the local fixture and candidate evaluation; hosted service still defaults to v4 until live wording evidence and deployment. Twenty-five targeted backend tests passed, including grouped save/reopen, no duplicate call, source deletion retention and malformed payload rejection. Synthetic UI behavior is verified separately; no inference quality claim follows from fixture text.

Simulator acceptance: Phone/ProactiveUITests passed on iPhone 17 Pro (iOS 26.5). A synthetic messages-array response traveled through the actual local service and chat sync; two distinct native bubbles appeared with separate frames and at least 80 points of right clearance, preserved draft, one new-message control, functioning Quiet/Stop and two restored messages after relaunch. [Inspected screenshot](qa/conversational-messages/separate-bubbles.png). Five Swift message-presentation XCTest cases also passed via the compiled CoreTests.xctest bundle. Logs/results: work/grouped-messages-ui/. No real microphone/provider calls and no physical install. This checkpoint verifies capability, not candidate model quality or production rollout.

Swift test runner setup: a standalone Linux-style XCTMain harness was unavailable in Apple XCTest. Built the existing CoreTests target and ran `xcrun xctest -XCTest CoreTests.CompanionMessageTextTests /tmp/VoiceCompanion-Grouped-CoreTests/CoreTests.xctest`; all five cases passed. This required no product-code workaround.


## Three approved live calls — v5 not selected

Founder approved reusing the three remaining two-topic phone calls and deploying only a successful result. All three completed with no retries, exhausting the existing eight-call/$0.16 ledger; this screen reserved $0.06, no new funding. Requests and actual responses are in `Backend/fixtures/proactive/conversational-evaluation`.

Cedar contributed two messages (139 and 63 characters), preserving the prerequisite/status/calendar facts but still using a dense semicolon clause and "as of the note"; it also weakened "agreed" to "wanted." Harbor contributed one 115-character message combining several ideas. Acknowledged Cedar correctly stayed silent. Decision/schema/storage checks pass, but conversational voice and chunking acceptance FAIL. No deployment or phone installation is performed for this failed candidate.

Exact live responses replay through the actual service, source validation, durable store and reopen with teacher-forced earlier context. This proves mechanical compatibility, not autonomous conversation quality. The previously verified simulator establishes separate bubble capability. V6 is prepared with more explicit one-idea-per-array-item guidance, shorter conversational examples and preservation of agreement wording; it is not selected or tested live. Further provider calls require a fresh bounded approval. Hosted v4 and the installed margin-only phone build remain unchanged.


## V6 isolated three-call screen

Founder approved a fresh $0.06 / three-call allowance, no retries. The isolated `conversational-v6-20260929-060` ledger reserved all three slots before transport; all completed. Existing phone/runtime allocations and exhausted v5 ledger are unchanged. Exact evidence is under `Backend/fixtures/proactive/conversational-v6-evaluation`.

Cedar now returns three separate messages (89, 44 and 55 characters), retaining agreement, five people, basic recording flow, before features, historical pending status and calendar afterward. Acknowledgment returns silence. Harbor returns one short 67-character accessibility constraint; the alternative room is not repeated, but the requested suitability question is directly resolved. Mechanical chunking and decision acceptance pass. Cedar still uses "as of the note," so the conversational-tone instruction is not fully satisfied. Do not call this full style acceptance or silently lower that criterion. No production selection/deployment or phone installation occurred; founder can judge this actual output before further spending or rollout.

Exact-response replay uses the v6 instructions with the unchanged messages schema, real source validation/storage/reopen and synthetic earlier context. It does not claim a new physical capture, closed-loop conversation or consistent behavior across arbitrary topics. The prepared provider runner is `proactive_conversational_v6_provider.py` and refuses a second run on the consumed ledger.


## Founder rejects v6 tone; v7 prepared

Founder wants the voice more conversational still. V6 remains unselected. V7 shifts from reporting the source to contributing to the immediate decision, allowing a grounded, clearly framed suggestion followed by short supporting messages. It preserves separate-message delivery, decision-critical facts and historical qualifications without forced friendliness. No new calls or deployment.

Proposed bounded next screen: up to $0.20 / ten calls, with no retries. Start with Cedar, a fresh changed-time planning case and an acknowledged/silence case; inspect actual output, then use remaining calls only for necessary revised-prompt checks and fresh transfer cases. No recording or note generation. Evaluate usefulness, natural voice, distinct short messages, factual completeness/qualification and appropriate silence together. This allowance is proposed, not authorized; all previous wording budgets are exhausted.

## Approved ten-call refinement — no candidate selected

Founder approved up to $0.20 / ten calls, no retries, and emphasized purposeful engineering. The isolated `conversational-v7-20260929-200` ledger contains ten completed calls and $0.20 reserved capacity; reservation is not an invoice. Runtime quotas, old grants, personal notes and installed UI were untouched.

The first three calls tested v7 on Cedar, a fresh biology-group scheduling correction and acknowledged Cedar. V7 sounded more direct but dropped the broader before-features agreement; the schedule reply combined beats. V8 used two calls to check stronger preservation/splitting guidance: Cedar retained the agreement but packed recorded status into it, and the schedule reply remained one paragraph. V9 used two calls to test simpler delivery guidance: Cedar still combined status/calendar facts; the scheduling reply dropped the room-availability reason. V10 used the final three calls for a shorter prompt with an explicit one-sentence-per-item delivery contract, those two problem cases and acknowledgment. Both acknowledgment cases returned silence. No automatic retries or repeated identical requests occurred.

Actual final Cedar output:

1. “I'd hold off on calendar integration for now.”
2. “The team agreed to test the basic recording flow with five people first, and those tests hadn't happened when this was recorded.”

The second message remains dense (128 characters), and “first” weakens the explicit broader condition “before adding features.” This does **not** meet the founder's combined tone, completeness and separation requirement. It is not selected or deployed. Continued prompt-only edits have not demonstrated reliable compliance; another nearly identical trial would add little evidence. The next implementation hypothesis is a structured content plan separating the supported agreement, its qualifier and conversational delivery in the same model call, followed by lossless presentation validation. That hypothesis is unimplemented and untested; it is not a reason to substitute template wording or silently drop facts.

Exact requests, responses, usage and message lengths: `Backend/fixtures/proactive/conversational-iteration-evaluation/`. `scripts/evaluations/proactive_conversational_v7_provider.py` bounds batches against the isolated ledger, rejects duplicate requests, counts every reservation and refuses continuation after an uncertain/incomplete attempt. The allowance is exhausted.

Verification: 23 targeted backend tests pass. All ten actual outputs replay with exact prompt/request matching through real retrieval/validation/persistence/reopen (earlier multi-step context is teacher-forced, not closed-loop). Separate message boundaries survive storage; duplicate calls remain suppressed. These tests establish mechanics and preserve the observed style failure, not tone acceptance. No Swift or bubble UI change; the previously verified simulator rendering remains applicable to the unchanged code. Hosted v4 and the installed margin-only phone build remain unchanged. No physical-phone or new microphone claim.

## Structured delivery candidate — local mechanics only

Founder approved changing the response contract after the ten-call screen. `structured_delivery=True` now selects a single Luna response containing `decision`, `facts` (source ID plus exact excerpt), then `messages` (one fact index and conversational text per item; a null index permits one optional suggestion/question). The opt-in is mutually exclusive with the archived grouped candidate. Hosted selection and the default v4 request remain unchanged.

`proactive_delivery.normalize` checks that excerpts occur literally in their selected source, indexes are valid and unique, every selected excerpt maps to one message, silence has no facts/messages, and message boundaries contain no embedded line breaks. It normalizes only user-facing text to the existing blank-line message protocol and existing 600-character aggregate bound. Evidence IDs remain internal; no fact planning leaks into the chat. The default Luna route still uses one model call, one persisted contribution and one deduplication/cooldown identity. Invalid output is rejected with no truncation, repair or retry.

This is structural coverage, **not** proof that the model selected every relevant fact, extracted a complete/atomic fact, or paraphrased it faithfully. Exact quotes can themselves be incomplete. Tone, meaning preservation, useful silence, token-limit fit and real API/schema acceptance need a bounded live screen. The prompt explicitly preserves identity, historical status, before/after scope and uncertainty. No sentence-splitting heuristics, hard per-message character limits, additional inference passes or UI changes were introduced.

The schema uses required fields and closed objects per [official Structured Outputs documentation](https://developers.openai.com/api/docs/guides/structured-outputs); schema compliance does not establish semantic quality.

Local verification: 28 targeted tests pass, including a handwritten Cedar output through the real service, evidence validation, SQLite save/reopen, three intact message boundaries, source-deletion retention and duplicate suppression. Malformed quotes, missing/duplicate mappings, invalid indices (including booleans), nonempty silence, embedded breaks and oversized delivery are rejected. A test explicitly demonstrates that structurally valid but semantically wrong wording cannot be proven correct by this validator. Historical exact-response replays remain passing. No paid calls or native UI changes; previous simulator rendering evidence applies to the unchanged output protocol, not to new model quality.

Export with `python3 scripts/evaluations/prepare_structured_proactive.py work/proactive-structured/requests.json`. Prepared live screen: three fictional requests (Cedar agreement/status, the biology time-change reason, and acknowledged Cedar silence), under `work/proactive-structured/requests.json`. Request up to $0.06 / three calls, no retries, using a fresh isolated ledger if approved. This is not funded yet. Stop after inspecting actual outputs; do not silently select an unsuccessful result. No new recording, notes generation, runtime allowance or personal-data mutation.

## Structured live screen — delivery passes, quality not accepted

Founder approved the prepared isolated $0.06 / three-call screen. All three requests completed without retries in `structured-delivery-20260929-060`; ledger has three completed reservations totaling $0.06 capacity (not verified invoice cost). Prior grants, personal data and runtime quotas are unchanged. The allowance is exhausted.

Real Luna accepted the new schema and fit within the unchanged 600-output-token cap: Cedar used 150 output tokens, scheduling 134, silence 23. All responses passed quote/index validation. Cedar returned three distinct messages of 89, 48 and 52 characters:

1. “The team agreed to test the basic recording flow with five people before adding features.”
2. “Those tests hadn't happened when this was noted.”
3. “So calendar integration should wait until afterward.”

The agreement, quantity, broader prerequisite and historical status survive; actual model-selected separate delivery works. The wording still reads like a source recap, so conversational tone is not accepted. Scheduling also selected the time change, agreement and location but omitted the room-availability reason from facts and messages. This demonstrates the validator's known limit: it can enforce coverage of selected facts, not detect every omitted relevant fact. Acknowledged Cedar correctly returned silence.

Exact requests/responses are in `Backend/fixtures/proactive/structured-delivery-evaluation/`. Thirty targeted tests pass, including actual outputs through real retrieval, validation and save/reopen with exact request matching. Multi-step preceding context remains synthetic/teacher-forced. No new native UI, audio or physical-phone claim. The candidate remains opt-in, PR stays draft, and no rollout occurred. Do not add more prompt rules or purchase another near-identical run without a distinct testable hypothesis; the structural issue is resolved in these cases, while tone and evidence selection remain open.

## Contribution-first candidate — awaiting live evaluation

Founder rejects the bookkeeper voice and approves addressing it. Hypothesis: enumerating excerpts before generating messages encourages the model to paraphrase a fact list. The candidate reverses generation order to `decision`, `messages`, `facts`, and puts message text before its fact index. The response contract's fields/types and existing normalization remain compatible. This uses schema key ordering documented by OpenAI; whether it improves the voice is unproven.

The rewritten instructions prioritize a useful opening question, suggestion or correction tied to the live decision, followed by remembered support. Contrasting examples distinguish participation from accurate recap; the candidate must preserve prerequisites, reasons, quantities, identities and historical uncertainty. No forced chattiness, mandatory question, hard message-length cutoff, UI change, extra call or automatic repair.

Thirty local tests pass. Historical fact-first model outputs replay with their archived requests, not with the new candidate falsely substituted; the parser, storage and separate-message protocol are unchanged. These are mechanical regression checks, not live voice evidence. PR 144 remains draft and hosted selection is unchanged.

The prepared screen (`python3 scripts/evaluations/prepare_contribution_first.py work/contribution-first/requests.json`) contains five fictional cases: the matched Cedar decision, time-change reason and acknowledged silence; a current update that the tests are complete (must not nag); and a fresh venue/budget choice (must help decide). Each has an explicit human-review rubric excluded from the model input. Compare the matched cases to already-paid archived outputs; do not rerun the old prompt. Judge the new opening's usefulness and naturalness along with complete supporting detail and silence. No assumption that a quote/index validator can grade those qualities.

Proposed next allowance: up to $0.10 / five calls, no retries, to run this predeclared screen. Not funded yet; all previous grants remain exhausted. No new recording, notes generation, personal data change or phone installation. Do not deploy before actual output satisfies the combined criteria.
