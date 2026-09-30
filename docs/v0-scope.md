# V0 scope and delivery sequence

> Historical/bounded delivery document. The [current product definition](product-source-of-truth.md), [current implementation state](current-state.md) and [TestFlight handoff](execution/testflight-release-handoff.md) govern the full vision and current sequence. Older one-liners, exclusions and pending stages below retain their original checkpoint meaning.

Status: Founder decisions consolidated September 24, 2026.

## Delivery sequence

Build Proven, then Better, then New. **Proven remains Granola**, as defined in the [product source of truth](product-source-of-truth.md). V0 is a deliberately narrow slice of that reference experience, not a replacement definition of Proven.

## V0: voice in, transcript out

Support **Mac and iPhone**, with iPhone now leading subsequent product priorities. The user starts a microphone recording session, sees a live transcript with best-effort speaker labels, stops recording, and can revisit the saved transcript.

```text
Start recording
      |
Microphone audio (Mac or iPhone)
      |
Transcription + best-effort speaker labels
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

## Accepted internal-trial boundary (September 24, 2026)

The founder explicitly accepts best-effort diarization for V0. Prioritize immediate display of received text, reliable capture, stopping/finalization, and saved reopening. Speaker labels can arrive later, change, or be wrong; these limitations do not block this narrow internal trial. Preserve the failed strict speaker evaluation as evidence rather than changing it into a passing result. Formal natural-speech word-accuracy benchmarking is also deferred by founder decision.

This is a foreground, five-minute, local-storage development build using a bounded relay on the Mac. It is not the always-on companion or a public subscription release. No cross-device synchronization is provided. Stronger attribution becomes necessary before features rely on identifying the user, assigning memories, or deciding whom an AI response addresses. Best-effort numeric speaker labels do not establish personal identity. See the [internal V0 runbook](v0-runbook.md) for use, evidence, and remaining limits.
