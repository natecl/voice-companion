# TestFlight and paid-launch handoff

Updated September 30, 2026 after account integration to main `31b284340fda`.
**Start here when continuing. Phase 1 is incomplete.** This supersedes the
pending-work sequence in demo-testflight-phases.md. Read README.md,
product-source-of-truth.md, v0-scope.md and engineering-principles.md first.
Preserve the agreed one-liner and approved shared UI. The account merge did not deploy later backend fixes or upload a build.
See the merge review for physical and simulator evidence recorded before integration.

## Recorded delivery baseline

- Main: `31b284340fda`, account/lifecycle PR159–180 merged, including PR178 knowledge reconciliation. [Merge review](../qa/account-merge-review/README.md) records independent review, automated checks and actual behavior. Full Phase 1 remains incomplete.
- Hosted backend: `482394e23dd081cc4a9a1e67ef79f7f4aa3b676e`, Render deploy `dep-daukpurtqb8s73boufmg`, service `srv-daqtfs7lot8c73dleuug`, schema21, auto-deploy off. This is prior `208ca34` plus only bounded transcription-budget compatibility; later companion-session and backup fixes are not deployed.
- Founder Google migration is complete: coordinated server mapping, preserved unrelated rows/usage, exact native four-session/20-outbox file preservation, physical signed-in relaunch and content acceptance. [Cutover receipt](../qa/founder-migration/live-cutover.json). Never replay this migration or restore its old ledgers over current activity.
- Physical Google→Apple→Google switching passed on the recorded Release candidate: old owner access revoked, cache cleared, original content restored on returning to Google. [Receipt](../qa/founder-migration/physical-account-switch.json). One person's two provider identities are not independent-human isolation.
- Real isolated Release simulator checks cover Google/Apple enrollment, populated switching/deletion/re-enrollment, provider revocation, normal native automatic refresh and fresh-proof recovery. [Lifecycle evidence](../qa/account-lifecycle/README.md), [Google recovery](../qa/account-lifecycle/automated-google-recovery.json), [Apple refresh](../qa/account-lifecycle/native-apple-automatic-refresh.json), [Apple recovery](../qa/account-lifecycle/apple-fresh-proof-recovery.json). Apple completion transition was founder-reported; subsequent signed-in restart was executed and inspected by the agent.
- Merged PR171 prevents companion sends after revocation; PR174 rejects late capture events after account teardown. [Local review and regression evidence](../qa/account-isolation-review/README.md). Native `1da7e188` subsequently passed physical capture/sign-out, preserved Google data, Apple isolation and Google return/relaunch; [receipt](../qa/account-capture-signout/physical-receipt.json).
- Merged PR172/175 supplies managed snapshots and explicit automatic expiry; PR173 prepares/validates deletion-aware offline restore candidates. [Backup scope](../qa/managed-backups/README.md), [automatic expiry](../qa/managed-backups/automatic-expiry.md), [restore limits](../qa/backup-restore/README.md). No production retention duration, activation or comprehensive historical/off-host/provider-snapshot policy is accepted.
- PR170/176 provides native simulator QA automation; PR177 resumes interrupted local QA on its original endpoint/databases/keys, with nine focused offline regressions. [Runner and evidence](../qa/account-lifecycle/live-ui-automation.md). Password/security challenges remain founder handoffs.
- App Store Connect: `Ellis: AI Notetaker`, ID6817680460, bundle `ai.voicecompanion.phone`, SKU `ellis-iphone-001`, English(U.S.), version1.0 Prepare for Submission, manual release selected. Founder accepted the Developer agreement September29. Archive/distribution signing remains unverified. No build uploaded, review submitted or testers invited.

## Decisions and remaining Phase 1 gates

Google and Apple remain separate accounts with persistent sign-in; Google appears
first. Founder legacy data belongs to Google; no account linking or Apple-data
migration is authorized. Shared UI components, styling, motion and haptics are the
source of truth; only functional wiring using that system is authorized.

Native network-failure and staged actual Apple-provider rejection recovery passed
with preserved content and same-owner relaunch; [review](../qa/account-merge-review/README.md).
Remaining acceptance: Google-specific negative refresh coverage and final provider-revocation contract; independent-second-person isolation; physical deletion/failure/relaunch;
reviewed retention duration/production configuration and deletion-safe restore
handling for owned, historical, off-host and provider snapshots. The native
migration's real wrong-account selection negative remains separately unproven;
synthetic wrong-owner/provider rejection is not that evidence.

Freemium plus subscription is selected; exact prices, allowances, billing periods,
paid-pilot timing and cohort are not. Finish accounts before plans, then billing,
Release and pilot. Do not use a blocked account check to begin later phases.

The founder will supply the final mascot; current artwork is not cleared for
distribution. Defer that asset gate while continuing engineering, but do not ship
it or invent replacement design. Keep the five-minute internal capture cap.
Calendar/email/messages, fresh outside retrieval, TTS and silent always-on capture
remain outside this release slice. One persistent chat, ordinary message-style
interjections, Quiet/End and the existing interface remain required.

## Phases, packets and gates

Founder explicitly requests sequential execution: complete Phase 1 acceptance
before starting Phase 2, then follow phases 3–5. Existing Apple app-record setup
is retained; further pricing or distribution work waits for the account gates.

| Phase | Bounded packets | Dependency and completion gate |
| --- | --- | --- |
| 0: establish release baseline | REBASE-0 verify main/runtime/build identities; DECIDE-0 prepare concrete account/provider and plan choices; APPLE-0 resolve agreement/app record | No assumption that a Debug install or old receipts prove Release readiness. Founder handles legal acceptance; no automatic paid calls. |
| 1: accounts and data lifecycle | ACCOUNT-1 authenticated enrollment/session refresh; ACCOUNT-2 sign-out, revocation and owner cache clearing; ACCOUNT-3 account deletion and existing-owner migration | Select auth contract first. Fresh Release install works without bundled developer credentials. Two actual users cannot read each other's notes/chat/memory or cached data. Preserve founder data during migration; prove deletion scope and retention policy. |
| 2: plans and limits | PLAN-1 measured cost/allowance proposal; PLAN-2 server-enforced allowance reservations and remaining-usage API; PLAN-3 limit/error UX | Founder selects numbers. Stable account identity first for enforcement. Cover capture, chat, notes, learning and proactive spending, including concurrent requests and retries. Existing notes remain readable at limit. No client-only enforcement. |
| 3: subscriptions and paywall | BILLING-1 StoreKit product/paywall UI; BILLING-2 verified transaction-to-account entitlement; BILLING-3 restore/manage lifecycle | Account and entitlement contracts accepted first. Sandbox purchase/cancel/pending/renew/refund/revoke/restore and expired/grace states; idempotent updates, account binding and offline reconciliation. Never ship a preview purchase button as working billing. |
| 4: deploy and validate Release | RELEASE-1 reviewed backend deploy/backup/rollback; RELEASE-2 bounded proactive Release wiring; RELEASE-3 assets/disclosures/archive; RELEASE-4 fresh install/update validation | Final native/backend version pairing; all critical failure paths pass. Release enrollment cannot depend on Debug import. Quiet/End/cancellation/budgets survive Release. Signing, app icon, permitted companion artwork, privacy/legal/support configuration and distribution metadata completed. |
| 5: TestFlight student pilot | PILOT-1 upload and independent installation; PILOT-2 short guided conversation and feedback | Explicit selected cohort/release route. A free pilot may precede commercial billing only by founder decision; exclude misleading purchase flows, keep real quotas. Paid launch requires phases 2–3 fully accepted. Capture real consented feedback without default transcript collection. |

## Safe parallelization

The founder now authorizes GPT-6 Astra/low workers under the primary orchestrator.
Parallelize independent work **within the current phase**, after shared contracts
and file ownership are fixed. In Phase 1 the lanes are account lifecycle QA,
managed backup/restore preparation, and independent isolation review. Pricing
and distribution execution wait for Phase 1 acceptance, as required above.
Serialize shared-file changes, migration, deployment and simulator/device use.

Workers receive bounded files, feature context, verifiers, failure cases and
budget. The primary reviews actual outputs and independently runs targeted
checks before accepting each checkpoint. Workers do not approve, deploy or merge
their own changes. Current workers share the account checkout with disjoint file
ownership; the primary alone commits and controls branches.

## Verifiers and evidence

Use `python3 scripts/verify_feature.py --list` and [feature index](../features/context-map.md). Primary release gates: `access`, `pricing`, `subscriptions`, `distribution`, with impacted `note-cache`, `deletion`, `capture`, `chat`, `proactive` and `social-presence` contracts. Every feature keeps its own context and verifier. Planned feature evidence gates are runnable but intentionally incomplete until real receipts exist; account suites now exist; StoreKit/product-price implementation and its real acceptance remain open.

Use `--checks-only` for existing local contracts, never as feature acceptance. Add purpose-built automated suites when the implementation exists. Submit exact source/configuration, fixture provenance, expected/observed behavior, raw sanitized receipt and inspected UI evidence. Review the final commit, not an earlier candidate. Real LLM changes require bounded approved final-model calls through the claimed pipeline; UI/cache mechanics should use fixtures. Simulator/StoreKit-local checks cannot establish App Store sandbox, physical haptics or actual microphone behavior.

Run manifest tooling checks after edits: `python3 -m unittest discover -s scripts/verification -p 'test_*.py'`. No requirement may be weakened to produce a green verifier. Account deletion differs from note deletion: deleting a note preserves past answers under existing policy; account erasure must address the account's full data lifecycle.

## Operational handoff and permissions

The account stack is merged; start subsequent bounded work from verified main. Current accounts checkout: `/Users/n.chinlue/.codex/worktrees/account-sign-in/voice-companion`; original `/Users/n.chinlue/code/voice-companion` has unrelated local state and must be preserved. Never store keys/tokens in docs or evidence.

Founder authorized internal deployment and TestFlight setup/release validation. That does not authorize accepting legal agreements, choosing commercial prices, charging, arbitrary tester invitations, resetting production data, changing Render tier, or paid model runs without a bounded allowance. Founder subsequently authorized $5 total provider/API testing; [ledger](testflight-provider-budget.md) records one $0.02 transcription reservation, with invoice cost unavailable. Hosting upgrades, subscriptions and other purchases are excluded. Observe canonical stop-and-wait rules for required founder input. Ask for physical readiness before timed manual QA.

Render SSH works with the existing dedicated `voice_companion_render` identity; default SSH identity failure does not establish loss of access. Do not deploy until current config, active work, backup, migration and rollback checks are satisfied. Preserve runtime quotas and historical ledgers. App Store Connect agreement is a separate founder-dependent gate; do not silently accept it.

## First action for the next agent

Read current-state.md and the affected feature maps, inspect the current branch
and receipts, then select the smallest remaining Phase 1 gate. Preserve the
original checkout and existing authenticated phone. Do not repeat accepted
migration/provider checks without a changed contract or unresolved question.
Verify current live state before any rollout; recorded identities above are not
fresh health evidence. Recheck Apple agreement state at distribution time rather
than assuming either acceptance or a new blocker indefinitely.

For agent-operated simulator work use [native QA automation](../qa/account-lifecycle/live-ui-automation.md).
Explain physical steps and wait for readiness when founder participation is
required. Review bounded checkpoints and their dependency chain before merging;
no release or full-feature claim follows from a documentation/tooling pass.

## Documentation and verifier acceptance

Feature discovery, catalog/manifest/path validation and focused verifier
self-tests check the knowledge tooling. They do not refresh historical provider,
UI or physical evidence. Full feature runs must retain required external evidence
and final-source review; `--checks-only` cannot release dependent phases. Paid or
physical evidence is never generated automatically by a documentation refresh.
