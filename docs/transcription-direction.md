# Transcription direction

Status: Conversation research recap, September 24, 2026. No provider has been benchmarked or integrated. Recheck current official documentation before implementation; this document records the direction discussed, not a completed selection.

## Requirements

Mac and iPhone microphone capture, live transcription, speaker diarization, timestamps, and support for revising partial results. Evaluate accuracy and speaker attribution alongside latency, reliability, integration complexity, and cost. The business model is now freemium plus subscription; the earlier requirement to avoid all per-minute API costs is superseded.

## Current candidates

**Grok Voice Transcribe 2.0** is the provisional leading cloud candidate discussed. The founder meant Grok, not Groq. Verify its streaming protocol, speaker-label behavior, authentication, quotas, retention, and actual performance before committing.

Official references: [announcement](https://x.ai/news/grok-voice-transcribe-2), [model documentation](https://docs.x.ai/developers/models/speech-to-text), [speech-to-text integration](https://docs.x.ai/developers/model-capabilities/audio/speech-to-text).

**Muse Voice Transcribe** was discussed as a comparison candidate, including its live speaker attribution. Verify current availability and integration details.

Official references: [model page](https://dev.meta.ai/models/muse-voice-transcribe), [integration documentation](https://dev.meta.ai/docs/speech-to-text).

On-device Apple speech recognition and FluidAudio were considered under the earlier free-product premise. They are alternatives rather than the agreed implementation. On-device transcription and diarization must be evaluated separately for device support, quality, and resource usage.

Official references: [Apple SpeechAnalyzer session](https://developer.apple.com/videos/play/wwdc2025/277/), [FluidAudio repository](https://github.com/FluidInference/FluidAudio).

## Evidence needed for a decision

Compare candidates on the same representative, appropriately sourced audio: single-speaker speech, multi-person conversation, noisy speech, specialist vocabulary, and overlapping speakers. Measure transcript accuracy, speaker attribution, time to useful text, revision behavior, failures, and actual billed usage. Vendor rankings and advertised latency are not evidence of performance on our workload.

Keep the provider behind an adapter so a later evidence-based change does not require rewriting the app. Exact quality targets and the final provider choice remain open.
