# Accounts and personal data

> Release planning reference: [September 29 handoff](../../execution/testflight-release-handoff.md). This link does not expand the feature’s existing verification claims.

Feature ID: `access` · Context reviewed September 30, 2026; native accounts remain draft PR159, with the dependent account-erasure storage checkpoint separately reviewable.

## Purpose and user outcome

Independent per-tester enrollment, isolation and revocation. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

The schema-20 provider/session backend is enabled on Render at `c897dec`. Both Google and Apple basic sign-in, sign-out and relaunch passed on the signed Release simulator; Apple reauthentication reused its original owner. Native account wiring remains draft PR159. The dependent schema-21 storage checkpoint adds atomic enrolled-owner content erasure and stale-credential tombstones, with local populated-owner and late-write checks. It is not deployed. A further dependent [deletion workflow candidate](../../qa/account-deletion-workflow/README.md) adds a default-off authenticated endpoint, durable retry state, session/provider revocation orchestration and owner-scoped socket shutdown. Fresh-provider-proof backend recovery can finish pending deletion after losing the original receipt. A dependent [native deletion candidate](../../qa/native-account-deletion/README.md) adds durable pending state, owner-local cleanup and existing-component confirmation/recovery UI, with 34 native tests and two simulator presentation tests. Exact-owner fresh-proof recovery also handles a locally saved request that never reached the server. The dependent [Google revocation adapter](../../qa/google-account-revocation/README.md) now binds revocation to the original verified grant and has isolated simulator Keychain/relaunch evidence. The latest [server finalization candidate](../../qa/deletion-finalization/README.md) closes the identity-reservation interval and passes an actual native/TLS service/Keychain retry run with fictional provider responses. The subsequent [real-provider Release simulator run](../../qa/account-lifecycle/README.md) verifies enrollment, relaunch, successful revocation responses, deletion and fresh re-enrollment for both providers. Backend refresh/replay and populated TLS isolation also pass with real enrolled QA owners and separate synthetic request credentials. Native automatic refresh, populated switching/cache acceptance, recovery, backups and physical-device checks remain open.

## Gaps and non-goals

Session refresh/revocation, owner-scoped cache clearing, existing-account migration and complete account erasure are required release work. Founder selected both Google and Apple on September 29, with Google above Apple in the sign-in UI. Google OAuth clients and Apple identifiers/server grants are configured. Real provider enrollment has simulator evidence; full populated two-user native isolation, actual refresh/revocation, physical-device checks, deletion and migration remain release gates.

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

The [backend account protocol and QA](../../qa/account-backend/README.md) distinguish signed synthetic-token socket evidence from unverified live providers. Current deployment and basic real-provider evidence are recorded in the native account QA below.

Native transport, device-local account Keychain storage, refresh serialization and Google/Apple adapters are connected to the existing signup view in the draft candidate. [Native account QA](../../qa/native-accounts/README.md) records build and fixture limits. Both providers completed basic Release-simulator enrollment/sign-out/relaunch. This does not establish physical-device lifecycle or full populated two-user acceptance.

## Next bounded work

Complete the remaining provider/runtime acceptance on the matching [server finalization candidate](../../qa/deletion-finalization/README.md). The synthetic native/TLS flow passes; real successful revocation/recovery and physical lifecycle still need evidence.

Integrate authenticated, resumable deletion with provider revocation and local cleanup, then complete populated native isolation, actual refresh/revocation and physical-device checks. The [storage checkpoint](../../qa/account-erasure-storage/README.md) proves only local content erasure; backups and restore policy remain explicit work. Use a stable server-owned account identity independent of expiring session credentials. Never automatically merge accounts by matching email; preserve existing founder data through an explicitly verified migration. See the [first account packet](../../execution/account-enrollment-packet.md).

## Supporting context and evidence

- [v1-runbook.md](../../v1-runbook.md)
- [execution/demo-testflight-phases.md](../../execution/demo-testflight-phases.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
