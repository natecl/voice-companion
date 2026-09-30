# Memory rework checkpoint 2B — durable bounded chunk pipeline

> Historical deterministic chunking checkpoint. Default-off and later-step statements below apply to this foundation stage; they do not describe the selected deployed memory pipeline. See [current state](current-state.md) for selected behavior and current evidence boundaries.

This checkpoint implements the deterministic chunking/storage path and exercises it through the real writer with fixture provider adapters. It is **off by default** (`MemoryWriter(..., chunking=False)`); hosted startup does not enable it. Jev semantic boundaries and live chunk-provider acceptance remain checkpoint 2C. Deterministic splitting is groundwork/fallback, not a claim of equivalent semantic quality.

## Behavior

Small sources retain their original passages, provider requests and stage names. An oversized source gets a durable plan with stable chunk IDs, source revision, processing contract, original passage/character ranges and bounded preceding-text overlap. The planner preserves all primary text exactly, including Unicode and escapes. It retains speaker/time metadata but never fabricates finer audio timestamps; character ranges are not word-aligned audio times. Original recordings remain unchanged.

Each extraction request is bounded to 10,000 serialized bytes with at most 32 chunks. The extraction parser retains the eight-candidate-per-call limit. Support and lifecycle judgments are planned in batches under their existing 28,000-byte ceilings; oversized individual requests fail explicitly rather than lose evidence. The parent write allows at most 256 proposed claims (32 × 8) and retains the owner-wide storage cap. Real usage remains governed by the canonical budget ledger, not an increased allowance.

Schema 7 stores each source/job-bound plan and completed chunk result. Existing metered request caches use chunk-specific stage names. Source revision/deletion invalidates plans, staged claims and cached responses. Completed claims map back to original passage IDs, and exact repeated claims are consolidated with source support preserved. Semantic paraphrase deduplication and cross-chunk correction reasoning are not claimed here; they require the later model contracts. Candidate lifecycle lookup still uses stored prior claims, not partially committed neighboring chunk output.

The entire recording's claim batch commits atomically after all chunks complete. A failure therefore cannot expose half a recording as fully learned. Completed chunks remain staged for reviewed recovery. Migration creates no plans and initiates no historical processing.

## Recovery and costs

`resume_chunk_job` is an internal explicit recovery operation for interrupted chunk jobs only. It checks owner, source revision and stored plan; it does not automatically retry or reset reservations. Finished chunks reuse their stored results. If a model attempt may have been charged but has no cached response, its existing reservation still blocks replay (`paid_retry_requires_review`). Failed budget/auth/provider jobs are not eligible for this recovery shortcut.

Stored plans reject a changed processing contract, including chunk version, model/rubric identifiers and extraction request configuration. Any change in chunk selection/mapping/completed-result semantics must bump the chunk version. Reprocessing under a different contract requires a separately reviewed recovery path, not an implicit paid backfill.

## QA evidence

Python 3.13 on the development Mac, temporary SQLite databases and fixture provider adapters:

```sh
python3 -m unittest discover -s Backend -p 'test_memory_chunks.py' -v
python3 -m unittest discover -s Backend -q
```

Ten focused tests cover:

- Exact primary-text reconstruction, deterministic IDs, Unicode/escaped text, multiple speaker turns and bounded overlap/request size.
- Unchanged small-source path.
- Oversized source → chunk planning → actual writer → staged results → deduplicated source-backed claims.
- Eight large candidate outputs batched without dropping candidates or exceeding verification limits.
- Interruption after a saved chunk, reopening storage and explicit resume without repeating completed calls.
- A charged/uncertain attempt remaining blocked after explicit resume.
- Deletion during extraction scrubbing plans/cache and rejecting late results.
- Foreign/stale recovery rejection, processing-contract mismatch, and schema-6 migration without automatic plans.

Final full backend suite: **123 tests passed**. The wider run covers shared storage, writer refactoring, cache/budget compatibility and prior failure isolation. These calls used fixtures; **zero paid calls**, deployment changes or physical-device tests. Semantic boundary quality, live model behavior on fragments, latency and actual costs remain unverified.

Next: bounded Jev boundary design and live provider QA before enabling hosted chunk processing. The whole checkpoint 2 acceptance gate remains open until that integration passes.
