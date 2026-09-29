# P0-B: mechanical baseline repair

Base: `47eadb4c8be3a46593bb6f17250f4c24335ea02c`. Execution split recorded before edits in prerequisite `6980410` (cherry-pick of coordinator `11bff54`). Scope is test maintenance, not changed product behavior or full feature acceptance. No provider spending, native/device use, deployment, or production data access.

## Acceptance and diagnosis

Before edits, the four assigned modules ran 40 tests with exactly four failures. Three migration assertions expected schema 17; current `MemoryStore` intentionally runs migration 18 (`notes_search.migrate`) and 19 (`proactive_store.migrate`). These add notes search and proactive storage. Tests now expect 19 while preserving existing no-backfill, owner/identity, tombstone, integrity and foreign-key checks. Additional assertions inspect empty added tables and compare claims after a second disk reopen. These are historical-schema simulations on isolated SQLite files, not production upgrade evidence.

The fourth failure was `answer_unavailable` in the retained-memory socket replay. Diagnostic comparison found one saved answer request with byte-identical input; its sole changed field was `instructions`. Current `ask.instructions` uses companion-chat-v3 and revised retained-memory wording; the fixture predates that change. Strict transport correctly rejects the unmatched request; the socket service maps that internal assertion to `answer_unavailable`. No storage regression was found in this reproduction.

The renamed historical replay test pins only the historical instructions selected by exact input and requires one unique match. All other request fields still pass through the unchanged exact-fingerprint transport. Original fixtures and production code remain unchanged. A negative test confirms the current prompt cannot silently consume the historical answer and records zero transport calls on rejection.

## Actual behavior and reproducibility

Run from this checkout:

```sh
PYTHONPATH=Backend python3 -m unittest Backend.test_memory_atomic Backend.test_memory_identity Backend.test_memory_transitions Backend.test_memory_retention -v
python3 scripts/verify_feature.py memory-learning --checks-only
python3 scripts/verify_feature.py identity --checks-only
python3 scripts/verify_feature.py memory-lifecycle --checks-only
python3 scripts/verify_feature.py deletion --checks-only
```

The focused run passes 41 tests. The historical test runs authenticated localhost WebSocket requests through `CompanionService`, real recall/context assembly, SQLite answer persistence, history/source reads and database reopen. Five saved provider responses support three persisted answers. Inspected answers retain the corrected community-center location, decline to quote a deleted transcript, and decline to equate a project preference with the owner's preference. The service verifies retained citations report `source_unavailable`; all three turns reopen complete. Existing tests cover stale/deleted source rejection, source-revision invalidation, cross-owner isolation, retained correction ordering and exclusion of unrelated transcript text.

Ignored diagnostic artifacts under `work/p0-b/`: `baseline.log`, `request-delta.json`, `baseline-socket/results.json`, `repaired.log`, `historical-socket.log`, and `historical-socket/{calls,results,summary}.json` plus isolated SQLite state. `summary.json` reports `new_paid_calls: 0`; its recorded reservation total is historical fixture metadata, not spending in this checkpoint. Clean-commit verifier receipts are generated separately under `work/verification/` and supplied in the handoff.

## Feature-map delta and limits

For memory-learning, identity and memory-lifecycle: replace the unresolved 17/19 mechanical mismatch with the explained additive-migration test repair; preserve missing fresh feature/model acceptance. For deletion: replace the unexplained replay failure with explicitly historical prompt/socket/storage regression evidence and strict current-prompt rejection. No current model-quality claim follows from replay, and current native deletion acceptance remains outstanding.

No model, prompt, schema, service or UI implementation changed. Full manifests remain intentionally incomplete without their required provider/native evidence and inspection. Merged, deployed and installed states are unchanged. The coordinator must independently inspect/reproduce, update maps, and accept this narrow checkpoint before advancing dependencies. Rollback is a revert of the test/documentation commit.
