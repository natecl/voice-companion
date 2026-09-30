# Durable evidence for chat during capture

> Historical snapshot-storage checkpoint. The deletion-invalidates-answer behavior and schema number below describe that implementation; ordinary recording deletion now preserves learned knowledge and historic replies under the retained-memory contract, while unavailable sources cannot be reopened. See [current state](current-state.md) for selected behavior and current evidence boundaries.

September 26, 2026. Checkpoint 6A3, additive schema 14. This backend foundation persists the exact live excerpts used by a question independently of finalized recording memory. Hosted routes, native UI and model instructions are unchanged.

## Behavior

Context assembly freezes selected live excerpts after checking its payload budget. The returned packet can be committed through the same `CompanionChat.complete` provenance boundary as finalized evidence. Snapshot references include an owner-scoped snapshot ID as well as recording ID, revision, passage ID and exact character range. Citation remapping and follow-up dependencies retain that identity. Only selected excerpts are saved, bounded to 9,000 serialized bytes and 1,000 snapshots per owner; originals remain on the recording path. Repeated identical snapshots reuse the same content key.

Snapshots do not enter source indexing, extraction jobs, embeddings or learned memory. They represent historical captured speech at a fixed cutoff, not current verified facts or account-owner identity. Anonymous speaker labels remain anonymous. Later speech cannot mutate a prepared answer's evidence.

When a recording is first synchronized or revised, compare each frozen excerpt with the same passage/range. Appending speech and finalizing unchanged used words preserves the snapshot, saved answer and conversational continuity. Rewriting or removing used words scrubs affected answers and descendants, and invalidates in-flight completion. Recording deletion atomically removes every snapshot and dependent answer/citation, including uncited follow-ups; the source tombstone prevents replay from recreating deleted evidence. Failed/cancelled generation can release an unused snapshot through `release`; referenced snapshots cannot be released this way.

Finalized-source dependencies keep their existing revision/qualification rules. Live snapshots are historical evidence rather than an independent current-state memory store. The upcoming conversational model gate must verify that newer canonical corrections take precedence over older captured speech. No model-quality claim is made by this storage checkpoint.

## QA

Development Mac, Python 3.13: full backend suite **284 tests passed**. New real-SQLite coverage includes reopen, append/finalize, follow-up citation hydration, deletion, attempted resurrection, changed used text, stale completion, owner isolation, idempotent freezing, safe unused release, no learning/index jobs and migration from schema 13 preserving existing chat/source data. Existing migration assertions advance to schema 14.

A separate two-process run saved a live-source answer before a canonical recording existed. The second process finalized the recording with additional speech, reopened the original context, saved an uncited follow-up, then deleted the recording. Both turns remained complete across finalization; deletion invalidated both and left zero snapshot rows. Receipt: `Backend/fixtures/live-snapshot-qa.json`. No provider or transcription calls; QA reservation remains $2.28/$2.40.

## Limits and integration

Matching is deliberately exact by stable passage ID and used character range. A transcriber that resegments earlier passages can invalidate an answer conservatively even when the broad meaning survives. Validate the native snapshot/passage contract during service/app integration rather than guessing an alignment or weakening deletion handling.

The persistent-chat streaming service still needs authenticated request validation, context-sensitive duplicate IDs, failure cleanup/recovery and the conversational provider prompt. It must release unused prepared snapshots when generation fails and commit all returned evidence/history dependencies before reporting a saved answer. Runtime wiring, native main chat/library and physical acceptance remain pending. Rollout requires a canonical backup, tested migration copy and separate deployment approval; do not run a schema-13 binary on schema 14.
