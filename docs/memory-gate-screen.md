# Jev past-memory gate: bounded shadow screen

Founder decision after review: leave the experimental past-memory gate disabled. It was never integrated into production; no runtime toggle or deployment is required. Reconsider only after a new explicit decision and evidence of benefit. The conservative routing screen was promising, but did not demonstrate an efficiency improvement. Existing chat, attached recording and live transcript stay available; the proposed gate only concerns past retrieval. No runtime files or flags changed.

Founder approved $0.08 for sixteen Jev calls, no retries. The operator ledger is `memory-gate-20260927-008`, separate from production. Combined approved envelopes are $5.83; runtime cap remains $5. Provider reservations are bounds, not an invoice.

## Frozen method

Sixteen synthetic cases and expected decisions were prepared before paid execution. Seven clearly self-contained messages, seven benefiting from past context, two ambiguous messages. Requests contain message, short recent history and attachment availability, never retrieved evidence or expected labels. This is an isolated shadow screen, not live-user traffic or an end-to-end answer comparison.

Jev `jev-1.13.0` uses one Choice question. Skip only when `unnecessary` probability is at least .95 and confidence at least .60. All other results, malformed outputs and failures retain retrieval. Thresholds were fixed before execution. TypeSafe's [documentation](https://docs.typesafe.ai/introduction) describes typed Choice decisions with probability and confidence; accuracy and speed here come from this run, not vendor guarantees.

## Observed results

- 16 live calls completed; no retries, no fresh Luna or transcription calls.
- Seven of seven self-contained messages would skip past retrieval.
- All nine useful/ambiguous messages retain retrieval: zero false skips in this small screen.
- Median provider round-trip: 174 ms; mean 176 ms; maximum 272 ms. Measured on Render; excludes phone network, downstream retrieval and answer generation.
- Critical limitation: the follow-up “And what time is it?” received the wrong top label (`unnecessary`, probability .57, confidence .36). The conservative threshold prevented the harmful skip. Do not use argmax alone.
- Weekend advice, birthday advice, corrections, cross-recording comparison and a quoted classifier instruction retained retrieval.

The labels express expected usefulness, not proven downstream answer quality. Short synthetic histories do not establish performance over real, long or multilingual conversations. The attached-only case does not prove an integrated gate preserves an actual attachment: there is no production integration yet.

## Efficiency comparison

Ran actual local `notes_recall.collect` against five synthetic recordings using the cached local embedding model. All sixteen questions produced five candidates, so the existing path would call Jev ranking sixteen times. The gate would add sixteen classification calls and retain nine ranking calls: **25 calls instead of 16**, with seven potentially larger ranking/context workloads removed. No baseline rankings or answers were purchased in this screen.

Thus 44% fewer retrieval attempts does not mean 44% cheaper or faster. Cost breaks even only when the seven avoided ranking calls and any downstream token savings exceed sixteen gate calls. On latency, using this screen's mean, each skipped retrieval would need to save roughly 402 ms on average to offset the gate across this message mix. This is an analytical break-even, not a measured end-to-end speedup. Local CPU timings are not comparable to hosted provider round-trips. Empty libraries already avoid paid ranking, so a gate there would be pure overhead.

Recommendation: keep current retrieval behavior for now. If pursuing this optimization, measure matched end-to-end latency/token costs and answer quality before activation; retain the conservative fallback and explicit-context guarantees. Avoid building a larger intent router from this narrow result.

## Reproduce without paid calls

```sh
PYTHONPATH=Backend python3 scripts/evaluations/memory_gate_screen.py Backend/fixtures/memory-gate/calls.json
python3 -m unittest discover -s scripts/evaluations -p test_memory_gate_provider.py
PYTHONPATH=Backend work/semantic-venv/bin/python scripts/evaluations/memory_gate_baseline.py
```

The screen script can also consume the saved JSONL transport output to validate exact request matching, parse results and regenerate the summary. Committed cases, exact request/responses, local baseline, provision receipt and ledger receipt are in `Backend/fixtures/memory-gate/`. Local checks cover malformed/uncertain fallbacks, threshold behavior, grant idempotence, cached responses, failure reservations, sixteen-call cap and unchanged runtime budget. Paid operator transport is not part of these replay commands.
