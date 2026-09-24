# V0 quality evaluation

Status: evaluation plan set before new provider runs, September 24, 2026. Engineering screening thresholds below are provisional and do not establish product-market fit or natural-speech quality.

## Bounded first screen

Three synthetic fixtures: held-out alternating Samantha/Daniel voices, the same conversation with deterministic Gaussian noise at 12 dB signal-to-noise ratio over the full clip, and a longer alternating conversation below the current 55-second app limit. These use macOS speech synthesis, not recordings of real people. No overlapping speech is included in this first screen; it needs separate measurement with natural conversation. No automatic paid retries.

Screening targets fixed before collecting responses:

- Clean and longer-clip word error rate <= 10%; noisy clip <= 20%.
- Speaker mismatch <= 10% among correctly aligned words after the best one-to-one mapping of provider labels to reference speakers; unassigned labels count as wrong. Report word-match coverage alongside it. This is not time-based diarization error rate and excludes substitution/deletion errors already measured by WER.
- First nonempty partial <= 3 seconds after sending starts; completion <= 3 seconds after audio.done is sent. These are single-run observations, not p95 guarantees.
- All runs must finish, retain text and timestamped speaker labels, and reduce through the app's actual Transcript implementation without duplicate chunks.

WER is standard Levenshtein substitutions + deletions + insertions divided by reference word count, with lowercasing and punctuation stripped except internal apostrophes, so possessives remain lexical differences. Speaker scores use the same deterministic optimal alignment; report ambiguous alignments as a limitation. Numbers use written words in the references, so no numeric-format normalization is needed.

A failed screen stays failed and is investigated; do not move thresholds after seeing results. Passing synthetic checks only unlocks representative natural-speech evaluation. Before any manual recording, explain its steps and wait for the founder's explicit readiness.

## Remaining acceptance

Natural single/multi-person conversation, realistic background noise and overlap, specialist vocabulary in spontaneous speech, physical input-route and permission-denial checks, battery/resource measurements, and sessions beyond the current development cap remain open. The near-limit clip tests continuity within that cap; it is not evidence that a lecture-length session works. Cross-device comparison and the final retention/provider decision remain separate.

## Observed first-screen results

Three requests, one attempt each. All three passed the predeclared synthetic screen.

| Synthetic clip | Duration | Word errors | Speaker mismatch on matched words | Match coverage | First text | Finalization |
| --- | --- | --- | --- | --- | --- | --- |
| Clean, three turns | 18.97 s | 1/50 (2%) | 0% | 98% | 1.13 s | 0.35 s |
| Same clip, added noise | 18.97 s | 3/50 (6%) | 0% | 96% | 1.13 s | 0.33 s |
| Longer clip, six turns | 43.07 s | 1/114 (0.88%) | 0% | 99.12% | 1.08 s | 0.39 s |

All reduced outputs retained final words, timestamps, and two speaker labels. The longer clip extends the clean script with three additional turns; the samples are not statistically independent. The clean substitution was “laboratory's” for “laboratory,” retained as an error. No score was corrected by hand. Noise is a nominal 12 dB target computed against full-clip RMS, not a recording of realistic room noise. The duration is within the development cap, not a long-session resource benchmark.

Total submitted audio: 81.013375 seconds, estimated $0.00450074 at $0.20/hour. Billing is unverified. Latency is measured from actual send timestamps, excluding the connection handshake for first-text latency. These are individual observations, not latency percentiles.

Machine-readable scores and audio hashes are in quality-results.json. Sanitized synthetic response events, reference turns, and timing summaries are in Fixtures/quality. No provider session identifiers or private conversation data are included. The scorer invokes the app's actual Swift Transcript implementation, avoiding a separate approximation of its chunk-replacement logic.

## Reproduce without a provider call

```sh
swiftc App/Transcription/Transcript.swift scripts/quality_reduce.swift -o work/quality-reduce
cp -R Fixtures/quality work/quality-cached
python3 scripts/score_quality.py work/quality-cached/clean --reducer work/quality-reduce
python3 scripts/score_quality.py work/quality-cached/noisy --reducer work/quality-reduce
python3 scripts/score_quality.py work/quality-cached/near-limit --reducer work/quality-reduce
python3 -m unittest discover -s scripts -p 'test_score_quality.py'
```

Three scorer regression checks cover edit counts/alignment and normalization. The earlier cached two-voice response also reproduced its known zero word errors and one speaker mismatch out of 30 words. No new provider call was used to validate scoring.

To generate fresh synthetic audio, run scripts/build_quality_fixtures.py on macOS (Samantha/Daniel at rate 165). Voice versions may change across OS releases; hashes identify the exact tested audio. A fresh paid probe is explicit: scripts/probe_transcription.py --directory <fixture-folder>, adding --max-seconds 60 for the longer fixture. The default cap remains 30 seconds; no automatic retries. Do not rerun paid probes for scorer or UI changes.

Natural human speech and representative multi-person conversation remain unverified by this screen. Grok remains a working integration, not a final provider-quality guarantee.
