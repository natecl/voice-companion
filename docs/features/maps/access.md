# Accounts and personal data

> Release planning reference: [September 29 handoff](../../execution/testflight-release-handoff.md). This link does not expand the feature’s existing verification claims.

Feature ID: `access` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Independent per-tester enrollment, isolation and revocation. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

Internal admission/credential foundations exist; fresh Release enrollment, sign-out, owner switching and full account deletion are not delivered.

## Gaps and non-goals

Session refresh/revocation, owner-scoped cache clearing, existing-account migration and complete account erasure are required release work. Sign in with Apple is proposed; Google is not yet selected.

## Flow and implementation entry points

Native credential/enrollment → authenticated admission → owner-scoped service/ledger → revocation/sign-out.

- [Backend/admission.py](../../../Backend/admission.py)
- [Backend/admin.py](../../../Backend/admin.py)
- [App/ExperienceAccountView.swift](../../../App/ExperienceAccountView.swift)

## Contracts and dependencies

No provider secrets in source or app bundle; no shared production credentials among testers. Separate owner isolation, authorization, budget reservations and permission to deploy. Sign-out must invalidate owner-scoped local state.

**Uses:** None required in this map.

**Consumers / coordinated work:** [Capture and live transcript](capture.md), [Recording library and sync](library.md), [Companion chat and follow-ups](chat.md), [On-device note caching](note-cache.md), [TestFlight install and update](distribution.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

Release feature remains incomplete. [Verifier](../verification/access.json): `python3 scripts/verify_feature.py access`. Its updated gates require final-configuration lifecycle evidence; existing local checks or preview navigation alone do not satisfy them. See the [handoff delivery ledger](../../execution/testflight-release-handoff.md) for merged, installed and deployed boundaries. No new account, billing or release behavior was tested in this documentation pass.

## Next bounded work

Select the account provider with the founder, then implement fresh Release enrollment and prove two-user isolation before lifecycle/migration work.

## Supporting context and evidence

- [v1-runbook.md](../../v1-runbook.md)
- [execution/demo-testflight-phases.md](../../execution/demo-testflight-phases.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
