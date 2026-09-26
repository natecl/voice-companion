# Memory rework checkpoint 2C — semantic boundaries

Optional Jev boundary selection now refines the durable chunk plan before extraction. Both chunking and semantic boundaries remain off in hosted startup. This is a bounded backend integration checkpoint; it does not establish broad conversation quality or activate production learning on longer sources.

## Behavior and limits

Only nearby whole-turn boundaries receive independent Jev questions. Clear topic splits require split probability at least 0.80. Continuations and uncertainty retain the hard-size fallback with preceding overlap. One long utterance has no useful whole-turn boundary and makes no boundary call. Speaker changes alone are not topic changes. Original primary text is preserved and validated against the source before persisting a plan.

Boundary responses use the existing metered cache. Explicit recovery reuses completed judgments; uncertain paid attempts remain blocked. Refined plans cannot replace plans whose extraction has started. Source deletion/revision invalidates staged work, and a late semantic plan cannot restore it. The processing contract is independent of dictionary ordering after source serialization.

The threshold is an initial conservative policy with six-case evidence, not a calibrated universal quality guarantee. Cross-chunk semantic consolidation and corrections remain checkpoint 3. No device behavior or transcription path changed.

## Real provider evidence

Environment: isolated QA code and synthetic SQLite on Render, separate from the hosted application and production memory database. Inputs are fictional. Existing canonical $1 QA ledger used; no new allocation or retries. Models: gpt-6-luna and jev-1.13.0.

Command (explicit paid run, not routine regression testing):

```sh
python evaluate_memory_chunks.py /var/data/voice-companion/profile-qa/chunk-v1 --budget /var/data/voice-companion/memory-budget.sqlite
```

Expected and observed:

- Frozen six-case boundary set: preserve question/answer, correction, story, ambiguous continuation; split two explicit topic changes. **6/6 passed in one batched Jev call.**
- Oversized synthetic source: original opening fact “Project Maple meets on Tuesday” and ending fact “Project Cedar meets on Friday” both survive extraction, independent support/lifecycle judgment, and atomic storage. **Both retained across three chunks.** The long single utterance exercises the hard-limit fallback; semantic selection is checked separately, not falsely credited for this path.
- **8 calls total** (3 Luna, 5 Jev), $0.08 reserved under the predeclared ten-call/$0.10 ceiling. Cumulative ledger: 70 calls, $0.70 reserved, **$0.30 remaining**. Reservations are not verified billing.

Synthetic request/response and actual stored claim results are checked in under `Backend/fixtures/memory_boundaries/recorded`. These responses support free regression replay; do not repeat the paid run merely to rerun tests.

Local execution covers lossless semantic planning, uncertainty fallback, absence of useful boundaries, writer persistence after source serialization, cached decisions after interruption before plan save, source deletion, and the recorded provider gate. Full backend results are recorded in the checkpoint PR.
