# V0 scope and delivery sequence

Status: Founder decisions consolidated September 24, 2026.

## Delivery sequence

Build Proven, then Better, then New. **Proven remains Granola**, as defined in the [product source of truth](product-source-of-truth.md). V0 is a deliberately narrow slice of that reference experience, not a replacement definition of Proven.

## V0: voice in, transcript out

Ship on **Mac and iPhone**. The user starts a microphone recording session, sees a live transcript with speaker diarization, stops recording, and can revisit the saved transcript.

```text
Start recording
      |
Microphone audio (Mac or iPhone)
      |
Transcription + speaker diarization
      |
Live transcript with timestamps and speaker labels
      |
Stop -> finalize -> save transcript
```

Speaker labels such as Speaker 1 and Speaker 2 distinguish speakers within a session; named identity recognition is not an agreed requirement. Transcript text and speaker assignments can be revised as results finalize. The app must accommodate those revisions.

V0 excludes AI notes, coauthoring, Q&A, voice replies, proactive questions, cross-session memory, and Jev-based judgments. These remain part of the broader vision or future experiments.

## Audio sources

V0 captures the microphone on both platforms. **Mac computer audio is explicitly planned for later**, including capturing microphone and computer audio together for calls and recorded lectures. Do not silently expand V0 to include it.

A microphone does not reliably capture audio playing through headphones. Consequently, V0 does not yet fully serve computer-based calls or recorded lectures. Keep audio capture modular so adding another source does not require rebuilding transcription and presentation.

## Business model

The founder revised the initial free-product premise to **freemium plus subscription**. Zero inference cost is not a requirement. Evaluate accuracy, speaker attribution, latency, reliability, integration effort, and cost together. Free-tier allowances, subscription prices, and billing implementation remain undecided.

## Completion expectations

The same basic flow must work on Mac and a physical iPhone: start, stream microphone audio, display and revise speaker-labeled text, stop, finalize, and reopen the saved transcript. Verify failure and interruption handling as well as the successful flow. Exact quality thresholds and supported OS versions remain to be established.
