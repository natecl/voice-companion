# First-release companion input and feel

Founder decision, September 26: spoken replies/TTS are outside the first release. Add voice dictation to the text composer; voice recognition/enrollment and manual voice-note labeling remain deferred. Keep the existing transcript → notes → contextual companion foundation.

Current status: draft [PR 99](https://github.com/natecl/voice-companion/pull/99), not deployed or merge-complete. Local native/controller/UI checks and the ten-response v3 personality screen are complete. Real physical-iPhone dictation, permissions and simultaneous capture remain pending founder readiness. The experimental past-memory gate is disabled. Earlier proposed QA sections below preserve checkpoint history.

## Composer contract

- Dictate deliberately: show listening and preview the latest transcription in the compose box, preserving existing typed text. Partial hypotheses replace each other; they are not repeatedly appended.
- Stop dictation finishes recognition and appends one editable segment. It does not send.
- Founder-requested Clear draft removes the whole unsent composer draft (typed and dictated text). During dictation it cancels recognition and any pending Send, discards late callbacks, and clears notices. It does not delete saved recordings, chat history or stop a separate meeting capture.
- Send during dictation finishes recognition, appends the final segment and sends the combined draft exactly once. Failure, interruption, backgrounding or navigation preserves received text without sending it automatically.
- Dictation alone creates no recording, note or learned-memory source. Sending follows the normal companion chat contract. If meeting capture is already active, the same microphone speech also belongs to that meeting; starting/stopping dictation must not stop meeting capture.
- A single microphone feed supplies independently stoppable consumers. Short dictation uses Apple's on-device recognition when supported for the current locale; no silent cloud fallback or additional Grok transcription session. Unsupported recognition explains the limitation and leaves typing available.
- Initial bounds: 60 seconds of dictation, five seconds to finalize. The draft survives incomplete finalization with an explicit notice. These are implementation bounds, not a recognition-quality guarantee.

Apple API reference: [audio-buffer recognition request](https://developer.apple.com/documentation/speech/sfspeechaudiobufferrecognitionrequest). On-device availability and permission behavior require physical-device verification. Local controller/fixture checks are not recognition QA.

## Personality direction for evaluation

Build on the existing attentive-personal-companion prompt, not a new persona or mascot. The ICP is the curious, ambitious, AI-comfortable person in the product source of truth, across their whole life. Desired feeling: an attentive, thoughtful friend with useful intelligence on tap.

- Warm and natural: short, direct answers in ordinary language, matching the user's conversational energy.
- Perceptive: use relevant recorded details to reduce repetition; do not bring up personal information merely to demonstrate memory.
- Independent judgment: disagree respectfully and give reasons; avoid reflexive agreement, canned praise and exaggerated confidence.
- Proportionate: answer a quick factual question briefly, make space for reflection when invited, and ask one useful question only when it helps.
- Grounded: distinguish recall, inference and advice. Make uncertainty specific and preserve source evidence internally without narrating retrieval or adding visible chat citations.
- Personal without pretending: no invented shared experiences, claims of feelings, forced intimacy, or claims to know the user beyond supported context.

Illustrative tone targets (examples, not recorded facts):

| Situation | Desired response style |
| --- | --- |
| User asks where an appointment is | Give the place first, grounded in actual evidence internally; no visible source or memory preamble. |
| User feels overwhelmed by several commitments | “That sounds like a lot at once. Want to sort out what actually needs your attention today?” Adapt to what the user said; do not diagnose or force planning. |
| User proposes an unrealistic plan | “I think the timing is the weak point. You’re fitting three things into the same afternoon.” Use specifics only when supplied. |
| User corrects a fact | Acknowledge naturally and answer from the correction; do not claim a permanent memory write unless the system actually confirms one. |

This direction does not change the deployed prompt yet. The current `Backend/prompts/companion-chat-v2.md` already contains much of it. A focused later prompt pass should assess ordinary chat, quick recall, reflection, disagreement, uncertainty and corrected/unknown identity, preserving evidence rules. No new provider evaluation allowance or quality claim is implied by this document.

## Delivery and QA boundary

Implement composer/controller/audio changes, then run targeted state and shared-capture checks, native build/UI checks with synthetic speech, and an explicitly scheduled physical-iPhone recognition check. Verify stop/edit/send, final-word delivery, permission denial, backgrounding and dictation while meeting capture continues. Reuse fixtures for failure paths; do not repeat paid transcription unless actual capture coexistence needs that evidence. Do not merge or declare the dictation feature complete before required physical speech and coexistence QA passes.

## Candidate implementation evidence

The candidate builds for Mac, iPhone simulator and the signed physical-iPhone target. Fifteen targeted core checks cover draft/final replacement, explicit send once, natural completion, permission failure, late callbacks, finalization timeout, interruptions, shared consumer ownership and the existing live-Ask/capture contracts. All pass. The native Mac UI test runs the actual composer and local companion websocket with synthetic dictation/capture: stop preserves an editable combined draft, a second dictation plus Send submits the final text, and capture remains active. Its screenshot was inspected. This does not prove actual speech recognition or hardware coexistence.

The first UI attempt omitted the fixture's companion-enable launch flag and opened the legacy screen; the test setup was corrected and the focused rerun passed. Logs remain in ignored `work/dictation-*.log`, with the passing screenshot in `work/dictation-screenshots`. No provider calls, server deployment, app installation or production quota changes were made. The deployed companion prompt is unchanged.

Physical acceptance is pending. First, after founder readiness, install the signed candidate and check real on-device dictation → Stop → editable draft, without sending or creating a recording. The new speech permission requires the founder. Then verify final-send and simultaneous microphone capture using a separately bounded, approved test setup; do not treat prior synthetic capture as hardware evidence. Keep the PR unmerged until these gates are satisfied.

## Muse desktop inspection — September 26, 2026

Read-only Computer Use inspection of the founder's installed Muse app (`com.meta.endo`), its Identity panel, and the exposed SOUL.md, IDENTITY.md and MEMORY.md editors. No files, settings or messages were changed. Private memory contents are not copied here. These observations concern this configured instance, not every Muse account, and do not reveal the complete hidden prompt, model or retrieval implementation.

Observed separation:

| Visible layer | What the UI exposes | Applicable lesson |
| --- | --- | --- |
| SOUL.md | A short behavioral document emphasizing practical help, opinions/disagreement, resourcefulness and respectful access to someone's life. Its explanatory note says it starts from a shipped template and may evolve with notification. | A concise, stable behavioral core can carry personality without a long fictional biography. |
| IDENTITY.md | Separate name, character, vibe and optional signature emoji. This instance is explicitly playful and theatrical. The UI says it is read at conversation start and changes when user and agent revise it together. | Distinguish the product's underlying character from optional styling. Do not mistake one user's customization for the default. |
| MEMORY.md | Curated facts, preferences, commitments and longer contextual sections with dated revisions. It includes communication preferences as well as factual context. The explanatory note describes conversation-start reading and nightly tidying and warns it may be out of date. | Remembering how someone prefers to converse can contribute to a personal feel, alongside remembering their life. These UI descriptions are not independent verification of the underlying jobs. |
| Existing chat | Some visible responses are concise, opinionated and conversational; others use longer lists, strong rhetoric and broad claims. | Instructions express intended style; they do not prove consistent behavior or factual accuracy. Evaluate actual responses. |

The visible memory file is substantial and retains older directions alongside revisions; one standing-work entry appears inconsistent with a later visible stop request. This is an observed stale-entry risk, not proof of what Muse currently retrieves or executes. Do not copy this file into our application or use its historical product directions to override the founder's current decisions.

### Proposed application to our companion

Keep our existing storage and source-verification system. Use three logical responsibilities, without building three new memory stores or exposing Markdown editors:

1. Stable character: quietly capable, attentive, candid, naturally warm, occasionally playful when appropriate. Help directly; have a reasoned point of view; do not flatter or lecture. Avoid invented feelings, human identity and guaranteed memory claims.
2. Conversational habits: short by default, deeper when invited; respond to the emotional/content context; ask a question only when it advances the conversation. Recall relevant details naturally rather than announcing the memory mechanism. Do not force every conversation into a productivity exercise.
3. Relevant personal context: bounded, supported facts and communication preferences supplied by the existing harness, with attribution, correction and source rules intact. Preferences may adapt expression, but cannot override accuracy, authorization or identity constraints.

The desired distinctive feeling is: **a quietly sharp, attentive companion who remembers what matters and has something useful to say.** This is a proposed refinement of the agreed attentive-friend direction, not a newly approved fictional persona. No autonomous tools, proactive interruptions, evolving self-authored instructions or new memory architecture are implied.

For the next personality checkpoint, separate style guidance from the unchanged evidence/identity contract in our prompt structure, and review a small set of responses: quick recall, casual conversation, an emotional moment, disagreement, uncertainty, a correction and missing context. Assess whether each feels natural while remaining accurate. Do not deploy new prompts or spend on that evaluation merely because this research was completed.

## Approved personality and message presentation update

Founder request: update the personality prompt using this direction, and show ordinary companion messages without sources in the actual release. This supersedes earlier requirements for visible chat citation links; it does not change note-to-transcript navigation or internal evidence integrity.

Candidate implementation:

- `Backend/prompts/companion-chat-v3.md` is the new active prompt in code. It makes the companion candid, quietly capable and naturally warm, brief by default, attentive to emotion and willing to disagree. The previous prompt remains as historical evidence. Factual grounding, unknown-speaker identity, corrections, uncertainty and tool limitations remain explicit.
- The model still emits internal grounding tags so existing reference validation, saved provenance and invalidation continue to work. The prompt forbids user-facing Sources sections or source-ID prose. Native `CompanionMessageText` removes tags from streamed, saved and interrupted answers; both current main-chat and legacy Ask hide source controls by default. Original answer text/metadata remain intact.
- Developer source-inspection UI is available only in DEBUG builds with explicit `--show-evidence-debug`; release builds cannot enable it. Existing source-navigation tests now explicitly opt into that diagnostic view. Generated note passage links remain unchanged.
- Retained-memory answers no longer have a mandatory “From what I remember” preamble in main chat. Source unavailability must still be explained when relevant or asked. This does not license pretending a deleted transcript is viewable.

Local QA covers streaming citation boundaries, saved/interrupted text, normal brackets, real local socket persistence, hidden default source controls and preserved diagnostic source navigation. Backend storage/validation/context tests pass after correcting a stale schema-17 assertion to the already deployed schema 18. An initial native test invocation used the system Python without fixture dependencies; rerunning with the documented configured Python resolves that setup failure. These checks do not establish model personality quality.

Ten short synthetic prompt cases are frozen in `Backend/fixtures/companion-style/cases.json`: casual conversation, a rough day, useful disagreement, quick recall, unknown speaker, appointment uncertainty, correction, retained knowledge, a general knowledge question and brainstorming with irrelevant retrieved evidence. All fit the existing context/input limits. Proposed live QA is at most ten Luna calls, no retries, reserving up to $0.20 in a separately approved operator allowance. No new model calls or deployment are authorized by updating this candidate. Hold prompt acceptance and rollout until bounded output review passes; physical dictation QA remains independently pending.


Founder clarification: the companion is a normal ongoing conversational chatbot, not restricted to recall questions. General questions, brainstorming, writing, reflection and casual chat need no recording. Existing optional source context enriches relevant replies; it must not force personalization or unnecessary recording disclaimers. The v3 prompt makes this explicit; the QA set includes empty-source conversation and unrelated-evidence distraction. Existing no-recording backend behavior remains unchanged.


Final local verification of the message/prompt candidate: 27 backend contract/storage/context tests, 11 native core checks and two actual Mac UI/local-service tests pass. Normal chat displays “Maya swims.” without its stored grounding tag or a source button; diagnostic source navigation still passes. The iPhone simulator target builds. At this local-check stage, model-behavior scenarios were prepared but not yet run; the subsequently approved live result follows below. No deployment occurred.

## Approved ten-response personality check

Founder approved the proposed $0.20 / ten Luna response allowance. The isolated operator grant `companion-style-20260927-020` raises combined approved envelopes from $5.55 to $5.75 without changing the application's $5 runtime envelope or quotas. Ten calls completed with no retries, each reserving $0.02; this exhausts the $0.20 allowance by conservative reservation, not a claim of invoiced cost. Runtime reservations stayed at 4,956,868 microUSD.

All ten requests use the actual v3 instructions selected by `ask.instructions`, GPT-6 Luna with reasoning none, Standard/default service tier, no tools, no storage, disabled truncation and a 1,000-output-token cap. The operator transport requests non-streaming responses for review; these calls do not establish streaming latency. Native streaming/persistence behavior has separate local evidence. Exact requests, provider responses, reviewed answers and receipts are in `Backend/fixtures/companion-style/{calls,results,provision,budget}.json`; all source material is synthetic.

Reviewed outcomes:

- Casual conversation and the simple science question worked without a recording or a request for one.
- The disagreement case challenged an impossible time budget instead of agreeing.
- Brainstorming produced three names and ignored unrelated clinic evidence, with no fabricated factual citation.
- Quick recall supplied the clinic; the correction selected the community center; retained knowledge answered naturally without the previously mandatory memory preamble.
- The anonymous first-person swimming claim was not assigned to the user. Appointment uncertainty remained uncertain.
- Grounded answers used valid internal p1 tags; general/creative answers did not force citations. None added a Sources section. Native presentation removes those internal tags as separately verified.
- The rough-day answer honored the request not to make a to-do list, but its conversational metaphor about sitting with the user felt more therapeutic than the intended understated register. Record this as a taste limitation for founder review, not a factual failure or evidence of a universally finished personality.

This is a bounded prompt smoke check, not a model benchmark or proof that all conversational modes work. No production prompt deployment occurred, and PR acceptance still depends on outstanding physical dictation QA. Further personality iteration should use actual user feedback or a specifically approved additional test allowance rather than automatic paid reruns.

## How conversation type is handled

There is no explicit normal-chat/brainstorm/retrieval classifier or mode switch. The existing harness supplies the current message, bounded recent history and optional contextual evidence; Luna interprets the request and composes the response. Modes can mix naturally, such as brainstorming using a remembered preference. When memory is enabled, retrieval can run even for ordinary conversation; Luna is instructed to ignore irrelevant evidence. This is not a model deciding whether to call a retrieval tool. Explicit memory controls and the existing exclusion rules still apply. Jev's current role is evidence ranking, not choosing the conversation's personality or intent. Adding an intent router is not part of this slice and would require measured benefit before extra architecture.

### Optional retrieval-gate screen

The founder-approved [sixteen-case Jev screen](memory-gate-screen.md) retained all useful/ambiguous cases under a conservative threshold and skipped seven self-contained cases. It added 174 ms median provider latency; net cost/latency savings remain unproven. No production routing change.

Founder decision after the screen: keep the experimental retrieval gate disabled. Ordinary memory retrieval and Jev evidence ranking remain unchanged. The isolated evaluation is retained for reference only.

## Physical dictation startup failure and callback repair

The current signed candidate was installed and launched after founder readiness. The founder granted permission, but Dictate crashed on repeated startup. Two copied device crash reports (`VoiceCompanion-2026-09-26-233553.ips` and `...233554.ips`, retained privately under `work/dictation-crash/`) agree: `EXC_BREAKPOINT` / `_dispatch_assert_queue_fail` → Swift actor-isolation check → the speech-authorization closure inside `AppleDictationRecognizer.start()`, on `com.apple.root.default-qos`. This is an app callback-isolation defect, not a denied-permission error or a transcription-provider failure.

Repair: construct authorization and recognition-result callbacks in explicit `nonisolated` factories with `@Sendable` signatures. They only resume/yield through thread-safe continuations; mutable recognizer/capture/UI ownership remains on MainActor. The result callback had the same isolation risk even though the recorded crash occurred earlier at authorization. No permission bypass, cloud fallback or paid call was introduced.

Eleven targeted local tests pass: two actual background-queue callback regressions (authorization allow/deny and recognition error), seven composer lifecycle cases and two shared-microphone cases. These tests do not synthesize Apple's successful recognition result or prove hardware speech recognition. Physical Dictate → Stop → edit acceptance remains failed/pending until a founder-ready retest of the repaired signed build. Preserve these crash reports; earlier synthetic UI passes did not exercise this framework callback.

## Stop lost the visible draft: reproduced empty-final boundary

After the callback repair was installed, the founder reported that Stop removed the dictated message from the composer. Exact phone recognition events were not captured, so an empty final result is a reproduced explanation, not a confirmed device trace. The reducer unconditionally assigned every event's text, allowing an empty final hypothesis to erase previously visible speech. A new regression failed on the original code for both Stop and Send, preserving that evidence in `work/dictation-crash/empty-final-before.log`.

The reducer now ignores blank partial resets. A blank final after nonblank speech preserves the last visible text as an editable draft, shows a review notice, and never automatically sends that uncertain partial. A nonempty final remains authoritative, including legitimate revisions; truly empty dictation adds nothing. Existing typed text is preserved and the completed segment appends once.

Verification: 12 focused callback/composer/shared-feed tests pass; two real Mac UI/local-socket tests pass for the empty-final/edit flow and the existing normal-final/explicit-send/capture flow. The retained empty-final screenshot was visually inspected. The signed iPhone build passes. All recognition input in this regression was synthetic; no paid providers were used. The physical Stop/edit retest remains pending readiness; this is not a claimed end-to-end fix on the phone yet.

## Physical Stop/edit/Clear draft retest

Installed and launched signed candidate corresponding to `da0f39a` after explicit founder readiness. The founder confirmed that both requested flows worked: Dictate → Stop retained editable words, and Clear draft removed them. This is founder-observed physical speech/draft evidence, not an independently captured screenshot or recognition-event trace. No Send or paid transcription/model request was part of these steps. The previous callback crash and Stop-loss reports remain preserved above.

Local Clear draft verification additionally passed nine composer tests and one actual Mac UI/local-socket check covering stopped/editable and active dictation clearing; signed iPhone build passed. Pending physical gates: permission-denied UX, interruption draft preservation, explicit Send/final words and simultaneous meeting capture. PR remains draft and the backend prompt remains unchanged.

## Physical Send/capture preflight and budget rollout

Founder approved up to $0.04 inside the existing runtime cap, then separately approved deploying the isolated budget compatibility change. PR 100 (`bb073ff75301e1cf36e87038d99063312aebaea0`) is live on the existing service (`dep-das954gjo6nc73aorvog`). Before changing budgets, SQLite backups passed integrity checks. The explicit transfer changed category caps to STT 1,220,000 / Ask 2,930,000 / Jev 850,000 microUSD, leaving the global 5,000,000 cap and all 4,956,868 reserved microUSD unchanged. Reopening through the updated policy succeeded; prior rows and database integrity were preserved except the intended policy changes. Health and all workers are ready/idle. Daily recording/Ask limits have room; no extra day grant was needed. No model/transcription calls occurred.

Additional preflight finding before any manual run: recording completion can use the remaining, previously funded notes-generation call (25,000 microUSD reservation). STT plus Ask reserves 23,000; including notes totals 48,000, exceeding the newly approved 40,000 screen envelope even though notes funding was already globally reserved. Ask the founder to extend this screen to $0.05 and authorize use of that notes call before starting; do not disable normal behavior to conceal the cost. Background profile learning has exhausted its existing allowance; this check does not fund a new memory-learning evaluation. Use past memory off for the synthetic Send test to isolate composer/live capture and avoid unfunded retrieval.

PR 99 must incorporate PR 100's policy compatibility before any later deployment; deploying its older service-policy code after redistribution would reject the new split on restart. Operator receipts stay in ignored `work/dictation-budget-rollout/`. This preflight is not physical Send/capture acceptance.
