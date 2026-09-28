# Founder context

## Current clarification — September 28, 2026

The founder already records school material and important appointments. They sometimes know a past idea is relevant but cannot remember exactly what to ask or where they encountered it. They would skim/search a transcript or ask across all captured material. These are founder-reported experiences, not market validation or a fabricated dated customer incident.

The agreed direction is an AI note-taking app acting as a third smart person at the table. It proactively contributes through text, using both personal context and new ideas/outside knowledge, and adapts to the conversation. Study discussions, work, doctor/therapy appointments and financial conversations are intended contexts; no single launch audience has been selected. Study discussions were an assistant-proposed test setting, not a founder-approved exclusive ICP.

Full vision includes calendar, email and messages. Initial sources are captured notes/conversations. Example: “You mentioned a concern about sleeping last week. It might be worth bringing up now.” The hypothesis is useful contributions leading to repeated voluntary use, not an obligation to record everything. The founder paused application drafting; the YC page must remain unchanged. The current task updates project knowledge and audits gaps, not a from-scratch code rewrite.

See [current product definition](product-source-of-truth.md) and [audit](product-vision-audit-2026-09-28.md).

## Earlier context — September 24, 2026

The following records the earlier discussion. Current positioning and scope above take precedence.

## Intended experience

The user turns voice capture on for a conversation with a friend, a lecture, a recorded lecture, or an everyday appointment such as a visit to their dog's vet.

The broader intended experience during capture (not all in V0):

- Text is transcribed in real time.
- A notes view develops alongside the transcript.
- The user can write notes and the AI can contribute notes.
- The user can ask questions about the captured conversation.
- The AI can respond, potentially by voice.
- Useful questions may surface for the user to ask the person they are speaking with.

Afterward, the user can revisit and ask questions about the captured context. Longer-term interest: codifying everyday life through transcription and connecting useful context across sessions.

## Product emphasis

Context capture is the center. An earlier proposal emphasizing a general thought partner and autonomous execution was corrected by the founder and is not the accepted direction.

“Always-on” describes the source vision; the founder's concrete examples begin with deliberately starting a capture session. Continuous recording throughout the day is not an agreed requirement.

## Technology interest

The founder strongly wants to explore TypeSafe AI's Jev for inexpensive, fast categorical and probabilistic judgments: deciding when to contribute, classifying transcript information, and helping organize user context. This preference does not imply that Jev transcribes audio, writes notes, or stores memory itself.

## Open implementation questions

iPhone is the primary product experience; Mac remains supported. The founder’s iPhone-first everyday consumer-companion direction refines the New in Proven, Better, New; see the product source of truth. V0 is microphone audio to live transcript with best-effort speaker labels and saved transcripts. Mac computer audio is planned after V0. The business model is freemium plus subscription, superseding the earlier entirely-free premise.

Swift/SwiftUI is the working engineering direction. The founder prioritizes modular boundaries and tools that let agents make changes, run the software, observe results, and verify outcomes with minimal unnecessary human intervention.

The final transcription provider, generative model, memory representation, suggestion timing, final product name, pricing, and minimum OS versions remain open. Grok Voice Transcribe 2.0 is the exercised internal V0 integration, with documented speaker-label limitations; broader provider selection remains open.

See [V0 scope](v0-scope.md), [engineering principles](engineering-principles.md), and [transcription direction](transcription-direction.md) for the current delivery constraints. Start simply; do not treat every future possibility as a first-release requirement.
