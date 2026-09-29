# Personal context and identity

Feature ID: `identity` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Keep user/third-party facts separate with provenance. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

Personal context covers life circumstances and relationships, not only work. Source-grounded identity paths preserve the distinction between account owner and people mentioned.

## Gaps and non-goals

No voiceprint enrollment or guaranteed speaker identity. Unknown subjects remain unknown. Current migration test expects schema 17 while the database reports 19.

## Flow and implementation entry points

Source speaker/author context → named/unknown subject judgments → provenance-linked identity/relationship → qualified memory reads.

- [Backend/profile_identity.py](../../../Backend/profile_identity.py)
- [Backend/memory_store.py](../../../Backend/memory_store.py)

## Contracts and dependencies

Speaker number is not named identity. Account ownership of a recording does not make every statement autobiographical. Preserve identity qualifiers through correction, retrieval and deletion.

**Uses:** [Recording library and sync](library.md), [Tester access and account controls](access.md)

**Consumers / coordinated work:** [Automatic memory learning](memory-learning.md), [Past-context retrieval](recall.md), [Memory corrections and time](memory-lifecycle.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: implemented foundations; fresh feature verification required.
- [Feature verifier contract](../verification/identity.json): `python3 scripts/verify_feature.py identity`.
- [Mechanical baseline and unresolved checks](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Named, unknown and third-party subject cases through the active identity path.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

The personal knowledge graph starts with existing subject/provenance links. Prove owner versus third-party attribution and correction continuity; no voice identity or new graph database is inferred.

Diagnose migration expectation and exercise unknown speaker, quoted third-party text and same-name subjects; fresh model evidence is required for changed identity judgments.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [memory-identity.md](../../memory-identity.md)
- [memory-identity-transitions.md](../../memory-identity-transitions.md)
- [verification-rollout.md](../../verification-rollout.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
