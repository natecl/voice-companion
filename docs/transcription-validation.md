# Initial streaming integration evidence

September 24, 2026. This is a bounded protocol probe, not a completed accuracy benchmark or final provider selection.

Two real streaming requests used synthetic audio: 5.861625 seconds for one voice and 13.7021875 seconds for alternating Samantha/Daniel/Samantha voices. Both completed with live partial events, final word timestamps, speaker fields, and transcript.done. All 18 words in the single-voice sample and all 30 words in the alternating sample match the source text after punctuation/case normalization. The two-speaker sample has one misattributed boundary word; this is a small synthetic sample, not evidence of natural-conversation accuracy.

An important integration finding: interim events lacked word/speaker data; later events supplied it. Chunk-final events are followed by a stitched utterance-final result. transcript.done contained empty text in both runs. The adapter must preserve prior utterances, replace overlapping chunks with the stitched result, and avoid clearing text on empty completion.

The single-voice first partial arrived 1.53 seconds after connection initiation; completion arrived 6.74 seconds. Two-speaker completion arrived 14.65 seconds. These include streaming time and are observations, not service latency guarantees.

Total audio submitted: 19.5638125 seconds in two requests, no retries. At the documented $0.20/hour streaming rate, estimated audio cost is $0.00108688 (about one tenth of a cent). Billing has not been verified; session overhead or billing rules may affect the actual invoice.

Sources: [streaming protocol](https://docs.x.ai/developers/model-capabilities/audio/speech-to-text), [pricing](https://docs.x.ai/developers/models/speech-to-text), checked September 24, 2026. The streaming guide directs clients through a backend proxy; do not embed the API key in the native apps.

## Reproduction and reuse

`scripts/probe_transcription.py --directory <fixture-directory>` reads voice.wav (16 kHz mono PCM16, at most 30 seconds), sends one real-time-paced request, caps wall time at 50 seconds, and writes local events, summary, and a usage ledger. Requires Python 3.11+ and websockets 15.0.1. Reads the ignored repo .env without printing its key. No automatic retries. The default directory is work/transcription.

Local input and evidence are retained in work/transcription-single and work/transcription-pair. A synthetic-only response fixture is versioned under Fixtures for zero-cost parser/UI work. It is real provider output, not fabricated test data. Paid runs are not part of the default build/test command.

## Scope still pending

Subsequent checkpoints integrated these events, microphone capture, local persistence, and the authenticated development relay on Mac/iPhone. See development.md and quality-evaluation.md for current evidence. Natural speech, overlap, representative quality acceptance, retention review, and final provider choice remain pending. These original probes establish protocol behavior only.
