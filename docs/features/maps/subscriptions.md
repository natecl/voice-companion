# Subscriptions and paywall

> September 30 delivery context: [release handoff](../../execution/testflight-release-handoff.md). This map distinguishes source implementation from recorded deployment, installation and bounded verification; historical receipts do not attest current runtime state.

Feature ID: `subscriptions` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Current preview surfaces; Phase 3 purchase/subscription implementation has not started and remains required release scope. Product direction is an invited AI social presence with personal continuity; the retained agreed one-liner is **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

Freemium plus subscription is agreed. Existing surfaces are previews; StoreKit purchases, verified entitlements and restore are not implemented.

## Gaps and non-goals

Commercial prices, allowances and billing periods are undecided. A free pilot before billing is an option, not an approved waiver. No paid launch before purchase lifecycle acceptance.

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

Release feature remains incomplete. [Verifier](../verification/subscriptions.json): `python3 scripts/verify_feature.py subscriptions`. Its updated gates require final-configuration lifecycle evidence; existing local checks or preview navigation alone do not satisfy them. See the [handoff delivery ledger](../../execution/testflight-release-handoff.md) for merged, installed and deployed boundaries. No new account, billing or release behavior was tested in this documentation pass.

## Next bounded work

Only after Phase 1 accounts and Phase 2 plans are accepted, implement the first sandbox purchase-to-entitlement slice with failure and restore evidence.

## Supporting context and evidence

- [native-experience-ui.md](../../native-experience-ui.md)
- [execution/demo-testflight-phases.md](../../execution/demo-testflight-phases.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
