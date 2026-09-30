# Accounts and personal data

> September 30 delivery context: [release handoff](../../execution/testflight-release-handoff.md). This map distinguishes source implementation from recorded deployment, installation and bounded verification; historical receipts do not attest current runtime state.

Feature ID: `access` · Context reviewed September 30, 2026; source audit at `7079427`; dependent PR159–177 remain unmerged.

## Purpose and user outcome

Independent per-tester enrollment, isolation and revocation. Product direction is an invited AI social presence with personal continuity; the retained agreed one-liner is **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

The schema21 account/deletion candidate `208ca34` is deployed on Render with
accounts and deletion enabled; automatic deployment remains off. Native code
remains in the dependent draft PR159–177 stack. Both real providers passed
Release-simulator enrollment, sign-out, relaunch, populated source/note/chat
isolation and cache clearing. Both populated fictional accounts were deleted
through the native UI with successful real provider revocation and empty
re-enrollment; the other owner's rows and all spending history were preserved.
Backend refresh/replay passed for real enrolled owners using separate synthetic
app sessions; this is distinct from native automatic rotation.

The founder's selected Google identity is now bound to the preserved legacy
owner. The operator compared every row in 42 memory and 18 usage tables; only
the identity binding and five revoked flags changed. Twenty-two other database
files were unchanged. Fresh coordinated backups were downloaded and verified.
Physical iPhone Release Google sign-in moved all four original recordings with
exact bytes preserved, retaining 20 outbox files. Controlled relaunch and founder
confirmation verified no sign-in prompt, existing notes/chat and note opening.
See [cutover evidence](../../qa/founder-migration/live-cutover.json) and the
[real-provider lifecycle record](../../qa/account-lifecycle/README.md).

## September 30 reviewed local checkpoints

[PR171](https://github.com/natecl/voice-companion/pull/171) fixes a reproduced
stale-session disclosure on an already-open companion socket. Four regressions
fail against the prior source; the primary independently reran all 38 targeted
account/companion checks successfully. Actual loopback WebSockets and fictional
SQLite data establish this backend fix; it has not been deployed.

Managed snapshots, planned expiry and a disabled-by-default automatic expiry worker are implemented locally. [Managed backup evidence](../../qa/managed-backups/README.md) and [automatic expiry](../../qa/managed-backups/automatic-expiry.md) record disposable SQLite/CLI/hosted-process checks, including expiry while the service retains its database lease. Production duration, enablement and coverage of historical/off-host/provider copies remain open.

[Restore preparation](../../qa/backup-restore/README.md) creates and validates an offline quarantined candidate against independently established current memory/usage authority. It replays completed account erasures, preserves current spending/authentication state, and refuses other canonical content changes. It cannot activate a restore or recover arbitrary historical content. These changes and the [capture teardown fence](../../qa/account-isolation-review/capture-teardown.md) are implemented and locally tested, not deployed or installed. Phase 1 remains incomplete.

## Gaps and non-goals

Google native automatic expiry/Keychain rotation and signed-in restart now pass
in the isolated Release simulator; see [receipt](../../qa/account-lifecycle/native-automatic-refresh.json).
Real Google fresh-proof deletion recovery also passed through agent-operated
XCTest and the real provider, with no content session issued.
Apple native automatic rotation and persisted signed-in restart now also pass;
see [receipt](../../qa/account-lifecycle/native-apple-automatic-refresh.json).
Apple fresh-proof deletion recovery and re-enrollment also passed against an isolated local service using real Apple proof/revocation. The interrupted session was synthetic; the completion transition is founder-reported, and signed-in restart has separate XCTest/inspection evidence. See the [receipt](../../qa/account-lifecycle/apple-fresh-proof-recovery.json).
Remaining gates include physical deletion lifecycle, revoked-provider behavior, independent second-person isolation, production backup retention policy/coverage and restore acceptance. Local prepare/validate tooling is not operational restore completion.
Google and Apple remain separate accounts. Google stays above Apple; no account
linking or email-derived identity merge is included. The physical founder Google
migration is complete and must not be replayed.

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

Finish the remaining Phase 1 lifecycle and backup gates without repeating completed migration or isolated provider recovery. Physical Apple/Google switching, signed-in Apple relaunch and return to Google passed in the [receipt](../../qa/founder-migration/physical-account-switch.json); founder Google remains signed in in that record. Primary must review the local isolation/retention/restore checkpoints and establish their actual rollout pairing before claiming those fixes live. Keep founder-dependent physical checks behind explicit readiness. Pricing and paywall follow Phase 1 acceptance.

## Supporting context and evidence

- [v1-runbook.md](../../v1-runbook.md)
- [execution/demo-testflight-phases.md](../../execution/demo-testflight-phases.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
