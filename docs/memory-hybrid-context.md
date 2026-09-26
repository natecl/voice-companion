# Hybrid candidates and selected evidence

Checkpoint 5C: opt-in backend foundation, not installed Ask integration or final relevance selection. No schema change, deployment, paid calls, or native change.

`memory_hybrid.retrieve` combines up to 50 lexical and 50 semantic candidates with reciprocal-rank fusion (constant 60). One candidate per source passage prevents repeated overlapping windows from winning by count. The highest-ranked semantic window supplies exact original text when both paths find the passage. No probabilistic rejection threshold discards low-scoring source evidence. `use_memory=False` skips retrieval and embedding entirely; natural-language instruction interpretation belongs to the caller.

`memory_context.select` rereads selected references in one SQLite transaction. It ignores candidate-supplied text or lifecycle assertions, checks owner/live revision, and supplies source origin, capture time/timezone, speaker labels and whole-passage claim qualifications. Semantic similarity cannot establish identity or turn expired/history/conflict evidence into a current fact. Claims are explicitly scoped to the whole passage rather than falsely attributed to an embedding window. Unknown recording speakers remain unknown.

The bounded selected-evidence packet has a content fingerprint. `valid` rehydrates only its selected references and qualifications. Unrelated new notes do not invalidate it; selected source changes/deletion, claim changes, identity changes and read-time expiry do. This is an internal consistency contract, not a client-authentication token. Callers must validate at the answer delivery boundary and propagate provenance to saved derivatives; those integration steps remain pending.

## Evidence

- Default suite: 235 tests passed, then six focused context tests passed after adding identity-link/mutation coverage (236 tests total).
- Real pinned BGE model → SQLite → hybrid fusion → hydration → validation, using the existing frozen six paraphrase cases at 10/100/1,000 sources: all designated sources in top five. Maximum query plus validation at 1,000 sources: 20.116 ms on the local Mac; predeclared target under 100 ms. Long-passage late evidence, exact spans, cached vectors and deletion also passed. Reproduce with `work/semantic-venv/bin/python Backend/evaluate_semantic_store.py --cache work/embedding-models --hybrid`.
- `Backend/fixtures/memory_semantic/hybrid-proof.json` records results. Storage tests exercise owner separation, stale references, expiry boundaries, revision/deletion, identity-link changes, lifecycle changes, altered packet text, deduplication, excluded recordings and explicit memory-off.
- Existing synthetic transport tests are replays, not new paid audio runs. Zero provider API calls for this checkpoint.

## Remaining boundaries

Rank fusion is candidate discovery, not evidence that every returned passage is useful. Final reranking, irrelevant-query evaluation, token/character context budgets, attached/live recording assembly, cache-coverage diagnostics and background indexing integration remain pending. `hybrid` reports which retrieval paths ran, not full semantic cache coverage. Current hydrated packets can contain long lexical passages and must not yet be injected wholesale into answers. Hosted resource/latency acceptance remains separate from local evidence.
