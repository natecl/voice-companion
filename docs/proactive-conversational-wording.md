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
