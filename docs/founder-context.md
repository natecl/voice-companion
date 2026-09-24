# Founder context

These notes summarize the founder's clarification on September 24, 2026. They elaborate use cases without replacing the product source of truth.

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
