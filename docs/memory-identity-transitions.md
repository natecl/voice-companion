# Memory rework checkpoint 1C — evidence-dependent corrections

Schema 6 adds a correction ledger and its identity-link dependencies. This is the internal storage path for an independently accepted correction, exercised with fixture judgments. It is not yet used by the legacy model writer; provider integration remains checkpoint 3. Existing legacy corrections are not retroactively marked verified or automatically reprocessed.

## Behavior

`prepare_correction` returns the current incoming/target evidence and a token derived from claim states, source versions and identity links. Both claims must have established links to the same opaque entity, compatible kinds and temporal order; the incoming correction must be stated. Unknown identity, foreign claims, incompatible facts and legacy name hashes cannot authorize this path.

`apply_correction` repeats validation under the transaction lock and requires the prepared token. It records the exact identity links, makes the incoming fact current (or expired as appropriate), and retains the target as superseded history. Identical successful decisions are idempotent. The token prevents applying a judgment against changed evidence; it is not a client authorization token or a substitute for semantic verification.

Source deletion/revision and claim support writes revalidate registered corrections in the same transaction. If identity evidence or a referenced claim disappears, surviving claims become unresolved. Connected correction chains are conservatively reopened. Deleted facts remain invalid/scrubbed; superseded facts are never automatically restored as current. Possible replacement links are retained when both claims still have source support.

Unrelated source changes leave valid corrections intact. New identity evidence does not automatically retry inference or reapply a correction. An explicit new reviewed decision can use a fresh prepared token to resolve a reopened pair. Reopened decisions stay in history.

The existing duplicate-support contract remains unchanged and covered by prior storage tests. This checkpoint adds evidence dependencies for the new correction path; it does not claim to convert legacy duplicate/supersession decisions into verified entity decisions. That adoption must happen with the new model contracts and their negative-case gates.

## QA evidence

Python 3.13 on the development Mac. Commands:

```sh
python3 -m unittest discover -s Backend -p 'test_memory_transitions.py' -v
python3 -m unittest discover -s Backend -q
```

Ten focused tests execute real SQLite transactions: correction/history persistence, restart/idempotency, deleted bridge reopening, revised-source scrubbing, connected-chain reopening, explicit reconsideration, stale prepared decisions, cross-owner/different-entity/legacy rejection, schema-5 migration, unchanged unrelated context, and support changes during decision preparation. Multiple behaviors share a test where they form one path.

The first focused run exposed two fixture setup errors: an unconsumed bridge-source job was selected before a later fixture source. The setup now explicitly completes that empty-evidence job. The successful rerun exercised the intended claims; no production guard was weakened to pass it.

Final full backend result: **108 tests passed**. Broader execution was justified by shared source invalidation and schema changes. Zero paid provider calls, hosted changes, phone installs or manual QA. Synthetic accepted decisions establish storage behavior only; model identity/correction quality remains unverified.

## Rollout and next step

Additive migration preserves sources, identity links, claims and tombstones; no paid backfill. Old schema-5 binaries reject schema 6. Do not deploy until the concrete hosted migration/rollback gate is approved. Next is reliable background learning and contextual chunking, followed by independent model integration. The live app remains unchanged.
