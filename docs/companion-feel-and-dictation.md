# First-release companion input and feel

Founder decision, September 26: spoken replies/TTS are outside the first release. Add voice dictation to the text composer; voice recognition/enrollment and manual voice-note labeling remain deferred. Keep the existing transcript → notes → contextual companion foundation.

## Composer contract

- Dictate deliberately: show listening and preview the latest transcription in the compose box, preserving existing typed text. Partial hypotheses replace each other; they are not repeatedly appended.
- Stop dictation finishes recognition and appends one editable segment. It does not send.
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
- Grounded: distinguish recall, inference and advice. Make uncertainty specific and keep source access available without narrating the retrieval machinery.
- Personal without pretending: no invented shared experiences, claims of feelings, forced intimacy, or claims to know the user beyond supported context.

Illustrative tone targets (examples, not recorded facts):

| Situation | Desired response style |
| --- | --- |
| User asks where an appointment is | Give the place first, with the actual supporting source; no memory preamble. |
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
