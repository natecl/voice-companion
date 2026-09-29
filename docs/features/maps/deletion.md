# Note deletion and retained answers

Feature ID: `deletion` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Delete transcript without erasing already sent replies. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

Ordinary recording deletion preserves already-sent agent answers and eligible committed knowledge with bounded existing excerpts. Deleted originals cannot be reopened.

## Gaps and non-goals

This is not complete memory/account erasure or backup erasure. The historical retained-answer replay is explicitly pinned to its recorded instructions. Current prompt requests still reject unmatched saved responses; replay is not fresh model or native deletion acceptance.

## Flow and implementation entry points

Swipe/long press delete → local removal + durable sync → source/index/notes removal + tombstone → preserve eligible retained claims and historical replies.

- [Backend/memory_retention.py](../../../Backend/memory_retention.py)
- [App/Sessions/SessionController.swift](../../../App/Sessions/SessionController.swift)

## Contracts and dependencies

Do not retain a copied full transcript. Distinguish deletion from source revision and legacy personal-text deletion. Source links become unavailable without replacing historical reply text with an error.

**Uses:** [Recording library and sync](library.md), [Automatic memory learning](memory-learning.md), [Companion chat and follow-ups](chat.md)

**Consumers / coordinated work:** [Past-context retrieval](recall.md), [On-device note caching](note-cache.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: implemented foundations; fresh feature verification required.
- [Feature verifier contract](../verification/deletion.json): `python3 scripts/verify_feature.py deletion`.
- [Mechanical baseline and checkpoint results](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Swipe/long-press deletion, source unavailable, preserved replies and reopen.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

The P0 replay failure was instruction fingerprint drift (historical v1 versus current v3), not a demonstrated storage failure. Historical socket/persistence replay remains strict for input/model/options. Fresh current-model and swipe/hold deletion/reopen acceptance remain separate. Coordinate cache invalidation.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [Bounded P0 baseline repair and evidence](../../qa/background-baseline/p0-b.md). Local fixture/storage/socket scope only; no deployment or install.

- [retained-recording-memory.md](../../retained-recording-memory.md)
- [retained-memory-rollout.md](../../retained-memory-rollout.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
