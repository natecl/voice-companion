# Accounts and personal data

> Release planning reference: [September 29 handoff](../../execution/testflight-release-handoff.md). This link does not expand the feature’s existing verification claims.

Feature ID: `access` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Independent per-tester enrollment, isolation and revocation. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

Internal admission/credential foundations and schema-20 provider-to-owner storage exist; a disabled-by-default account endpoint now verifies ID tokens, binds owners, rotates app refresh tokens and revokes app sessions. Fresh Release enrollment, native sign-out/owner switching, provider-side revocation and full account deletion are not delivered.

## Gaps and non-goals

Session refresh/revocation, owner-scoped cache clearing, existing-account migration and complete account erasure are required release work. Founder selected both Google and Apple on September 29, with Google above Apple in the sign-in UI. Google OAuth clients and Apple Sign in with Apple identifiers are configured; real authentication remains unverified.

## Flow and implementation entry points

Native credential/enrollment → authenticated admission → owner-scoped service/ledger → revocation/sign-out.

- [Backend/admission.py](../../../Backend/admission.py)
- [Backend/admin.py](../../../Backend/admin.py)
- [Backend/memory_store.py](../../../Backend/memory_store.py): server-only verified-identity binding
- [App/ExperienceAccountView.swift](../../../App/ExperienceAccountView.swift)

## Contracts and dependencies

No provider secrets in source or app bundle; no shared production credentials among testers. Separate owner isolation, authorization, budget reservations and permission to deploy. Sign-out must invalidate owner-scoped local state.

**Uses:** None required in this map.

**Consumers / coordinated work:** [Capture and live transcript](capture.md), [Recording library and sync](library.md), [Companion chat and follow-ups](chat.md), [On-device note caching](note-cache.md), [TestFlight install and update](distribution.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

Release feature remains incomplete. [Verifier](../verification/access.json): `python3 scripts/verify_feature.py access`. Its updated gates require final-configuration lifecycle evidence; existing local checks or preview navigation alone do not satisfy them. See the [handoff delivery ledger](../../execution/testflight-release-handoff.md) for merged, installed and deployed boundaries. [Storage checkpoint QA](../../qa/account-identity/README.md) exercises stable ownership and actual local WebSocket isolation with synthetic identities. This does not establish provider authentication, native owner switching or Release acceptance.

The [backend account protocol and QA](../../qa/account-backend/README.md) distinguish signed synthetic-token socket evidence from unverified live providers. No deployment has enabled this endpoint.

Native transport, device-local account Keychain storage, refresh serialization and Google/Apple adapters are connected to the existing signup view in the draft candidate. [Native account QA](../../qa/native-accounts/README.md) records build and fixture limits. Fresh simulator entry has been inspected; real provider success, signed-device lifecycle and full two-user acceptance remain open.

## Next bounded work

Verify the candidate Apple code redemption, encrypted grant storage and provider revocation handling against Apple, verify deployed account endpoint configuration, and prove fresh Release enrollment plus two-user isolation through the connected native flow. Use a stable server-owned account identity independent of expiring session credentials. Never automatically merge accounts by matching email; preserve existing founder data through an explicitly verified migration. See the [first account packet](../../execution/account-enrollment-packet.md).

## Supporting context and evidence

- [v1-runbook.md](../../v1-runbook.md)
- [execution/demo-testflight-phases.md](../../execution/demo-testflight-phases.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
