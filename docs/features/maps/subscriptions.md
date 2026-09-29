# Sign-up and pricing previews

Feature ID: `subscriptions` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Current preview surfaces; real purchase/subscription implementation is deferred. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

Freemium plus subscription is the agreed business model. Preview UI exists; working purchase/subscription integration is not claimed.

## Gaps and non-goals

Purchases, entitlement state, restore and billing lifecycle require a separate implementation. They are outside the current demo/private-pilot critical path.

## Flow and implementation entry points

Current: account/pricing preview navigation. Future: authenticated purchase → entitlement verification → restore/cancel lifecycle.

- [App/ExperienceStyle.swift](../../../App/ExperienceStyle.swift)
- [App/ExperienceAccountView.swift](../../../App/ExperienceAccountView.swift)

## Contracts and dependencies

Do not let preview buttons imply a completed purchase or available entitlement. Use homepage typography and approved styling without treating screenshots as a backend contract.

**Uses:** [Tester access and account controls](access.md)

**Consumers / coordinated work:** None required in this map.

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: preview/deferred; not delivered as a working integration.
- [Feature verifier contract](../verification/subscriptions.json): `python3 scripts/verify_feature.py subscriptions`.
- [Mechanical baseline and unresolved checks](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Verify pilot navigation accurately marks or excludes unavailable sign-up/pricing flows.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

For the pilot, inspect and hide or clearly mark unavailable purchase flows. Do not start a billing integration without a bounded product packet.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [native-experience-ui.md](../../native-experience-ui.md)
- [execution/demo-testflight-phases.md](../../execution/demo-testflight-phases.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
