# Automatic memory learning

Feature ID: `memory-learning` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Source-scoped extraction/verification with atomic storage. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

The source-scoped recording path retains provenance and supports background learning. Recorded configuration uses Sol for independent factual entailment, Jev for bounded time/relation judgments and Luna for extraction/identity; inspect hosted composition before changing roles.

## Gaps and non-goals

Compatible additions remain separately sourced; earlier cross-recording consolidation and semantic boundary calls are not enabled in this route. A completed job may contain zero accepted claims. Current mechanical suite has an unresolved schema-version expectation.

## Flow and implementation entry points

Source job → deterministic overlapping chunks → Luna extraction → independent factual verification → modality/time/identity judgments → atomic evidence and claims.

- [Backend/memory_evidence_writer.py](../../../Backend/memory_evidence_writer.py)
- [Backend/memory_store.py](../../../Backend/memory_store.py)

## Contracts and dependencies

Proposal is not fact. Preserve original passages, owner/revision and failed evidence. Stale/deleted sources cannot commit later; do not backfill historical data or automatically retry paid calls.

**Uses:** [Recording library and sync](library.md), [Personal context and identity](identity.md), [Memory corrections and time](memory-lifecycle.md), [Tester access and account controls](access.md)

**Consumers / coordinated work:** [Past-context retrieval](recall.md), [Note deletion and retained answers](deletion.md), [Proactive contributions](proactive.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: implemented foundations; fresh feature verification required.
- [Feature verifier contract](../verification/memory-learning.json): `python3 scripts/verify_feature.py memory-learning`.
- [Mechanical baseline and unresolved checks](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Real extraction/verification on bounded source, accepted/rejected claims and resulting durable memory.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

Diagnose the recorded schema 17/19 test mismatch without weakening migration checks; then verify changed extraction/verification through worker and durable storage.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [independent-source-verification.md](../../independent-source-verification.md)
- [verification-rollout.md](../../verification-rollout.md)
- [uncertain-memory-time.md](../../uncertain-memory-time.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
