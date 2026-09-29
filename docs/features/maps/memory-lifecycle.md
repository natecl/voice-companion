# Memory corrections and time

> Release planning reference: [September 29 handoff](../../execution/testflight-release-handoff.md). This link does not expand the feature’s existing verification claims.

Feature ID: `memory-lifecycle` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Corrections, uncertainty and expiry preserve history. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

Corrections, provenance history and bounded expiry exist. Uncertain undated facts can remain qualified; active source-scoped additions do not imply automatic duplicate consolidation.

## Gaps and non-goals

Universal natural-language temporal understanding is not established. Verified expiry is bounded; no memory-management inbox. The bounded P0 migration regression now checks schema 19 and durable reopen without adding notes or contributions.

## Flow and implementation entry points

Supported observation + identity/time/relation → qualified correction or abstention → atomic lifecycle history → applicable reads/expiry.

- [Backend/memory_store.py](../../../Backend/memory_store.py)
- [Backend/memory_related.py](../../../Backend/memory_related.py)

## Contracts and dependencies

A newer note does not prove correction. A passed date does not prove completion. Preserve evidence and history while qualifying applicability; unresolved relationships must not overwrite established facts.

**Uses:** [Personal context and identity](identity.md), [Recording library and sync](library.md)

**Consumers / coordinated work:** [Automatic memory learning](memory-learning.md), [Past-context retrieval](recall.md), [Note deletion and retained answers](deletion.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: implemented foundations; fresh feature verification required.
- [Feature verifier contract](../verification/memory-lifecycle.json): `python3 scripts/verify_feature.py memory-lifecycle`.
- [Mechanical baseline and checkpoint results](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Changed temporal/relationship judgments on real model output; never infer event completion.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

Add a temporary schedule exception versus lasting preference case to the MEMORY-1 packet. Receiving a correction should change relevant context without blindly erasing a prior enduring preference.

Migration-test drift is repaired. Test correction chains, ambiguous time and deletion ordering before changing model judgments.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [Bounded P0 baseline repair and evidence](../../qa/background-baseline/p0-b.md). Local fixture/storage/socket scope only; no deployment or install.

- [memory-temporal-reads.md](../../memory-temporal-reads.md)
- [memory-expiry.md](../../memory-expiry.md)
- [uncertain-memory-time.md](../../uncertain-memory-time.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
