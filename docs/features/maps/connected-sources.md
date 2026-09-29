# Calendar, email and messages

Feature ID: `connected-sources` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Future product scope; no implemented connectors. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

Calendar, email and messages are part of the full vision. Initial MVP context remains deliberately captured notes/conversations; no connectors are implemented.

## Gaps and non-goals

Provider feasibility, consent, incremental sync, ownership, token handling and disconnect/derived-memory policy are unresolved. Video imports and fresh web knowledge are also separate future scope.

## Flow and implementation entry points

Future: explicit source connection → scoped sync/provenance → qualified retrieval → contribution → revocation/disconnect handling.

- [docs/product-source-of-truth.md](../../../docs/product-source-of-truth.md)

## Contracts and dependencies

Source content is untrusted data, never instructions. Ordinary recording retention must not silently become a connector revocation policy. Do not promise access to all messages without establishing platform support.

**Uses:** [Tester access and account controls](access.md), [Past-context retrieval](recall.md), [Note deletion and retained answers](deletion.md)

**Consumers / coordinated work:** [Proactive contributions](proactive.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: preview/deferred; not delivered as a working integration.
- [Feature verifier contract](../verification/connected-sources.json): `python3 scripts/verify_feature.py connected-sources`.
- [Mechanical baseline and unresolved checks](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: No implemented verifier: requires scoped connector design, consent, ownership and disconnect contract before implementation.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

Keep deferred during demo/TestFlight work. When prioritized, choose one supported source and define its permission, provenance and disconnect contract before implementation.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [product-source-of-truth.md](../../product-source-of-truth.md)
- [features/knowledge.md](../../features/knowledge.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
