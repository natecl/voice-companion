# Memory rework checkpoint 0 — recovery baseline

Scope: executable offline reproduction and frozen acceptance specifications. No application behavior changed, provider calls, schema migration, or deployment. Reproducing a failure is not fixing it.

## Versions and dependencies

- Verified main: `060fd857ba6c5c0b82be9541c93b4b3c5dcd8289` (PR 30), refreshed from origin at checkpoint start.
- Draft PR 31 remains open and draft. Its code was not merged or copied into this implementation branch.
- Draft replay checkout: `6c592825c198aa001c1121161c2119b19f51c4d5`; application implementation is `85e72cd`, with subsequent documentation commits.
- Last observed deployed implementation: `85e72cd`, schema 3. Deployment was not re-queried or changed for this offline checkpoint; refresh before rollout.
- The approved plan, product guidance and prior audit were carried over as documentation only. Profile recall from PR 31 will need explicit replacement/revalidation in the later retrieval checkpoint.

## Reproduction

Python 3.13 on the development Mac. Each run constructs temporary SQLite databases and uses the actual store, writer and candidate selection functions. The saved Maya judgments came from the earlier fictional QA case; IDs/times were sanitized. They are recorded evidence, not new inference. Network connection paths are blocked, no provider client is constructed, and budget reservations raise an assertion.

From repository root:

```sh
python3 Backend/reproduce_memory_baseline.py
python3 Backend/reproduce_memory_baseline.py --backend /path/to/historical-checkout/Backend
python3 -m unittest discover -s Backend -p 'test_profile.py' -q
```

The runner intentionally asserts historical failures. After a repair it should fail against repaired code; run it against the pinned historical checkout to reproduce old behavior. Do not change historical expectations merely to keep the runner green. New acceptance tests must assert the corrected behavior.

| Probe | Verified main | Draft replay | Required repair |
| --- | --- | --- | --- |
| Uncertain Maya correction | New claim, different identity | Same | Preserve unresolved replacement; apply only supported correction |
| Old correction target | Missing from latest-50 pool | Same | Relevant evidence before limits |
| Accepted oversized source | Worker exits; next job queued | Same | Bounded processing and per-source fault isolation |
| Name normalization | Same key without identity evidence | Same | Evidence-backed entities/mentions |
| Older paraphrased interest | Profile recall not yet present | Relevant fact absent from eight candidates | Semantic/relevance candidate coverage |

Recorded results are in `Backend/fixtures/memory_rework/baseline-main.json` and `baseline-draft.json`. Existing profile tests: **6 passed**. The name-key probe establishes a representation limitation, not independent proof of every downstream false merge.

## Frozen acceptance specification

`Backend/fixtures/memory_rework/acceptance_cases.json` contains 24 synthetic cases with inputs, expected behavior, forbidden outcomes, target checkpoint and development/held-out split. It covers identity, uncertainty, corrections, temporal handling, deletion, retrieval, worker recovery and the new chat/library experience. These are specifications, not 24 passing automated tests. Convert the affected cases into executable gates as each checkpoint is implemented. Freeze additional numerical/date-boundary semantics before the relevant implementation. Preserve failures; do not tune prompts on held-out cases. Any exposure-driven tuning requires fresh held-out cases before live evaluation.

Checkpoint 0 passes its bounded goal: current failures are reproducible without spending, and the next changes have explicit targets. Production correction quality remains failed; all later checkpoint gates remain pending.
