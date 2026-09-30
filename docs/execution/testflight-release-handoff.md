# TestFlight and paid-launch handoff

Updated September 30, 2026. **Start here when continuing in a new agent.** This is the current remaining-work overview; it supersedes the pending-work sequence in demo-testflight-phases.md, whose earlier execution and evidence remain historical. Read README.md, product-source-of-truth.md, v0-scope.md and engineering-principles.md first. Preserve the exact agreed one-liner and the approved shared UI.

## Verified baseline and delivery ledger

- UI PR154 merged as `dd907d4`. Integration PR155 merged as `5a04ea30d05dcf78537340e66da9e695465249ee`; it includes background PR149–153. These are accepted bounded checkpoints, not full TestFlight acceptance.
- [Integration review](../qa/phase-integration/README.md): 85 local backend tests, 19 native lifecycle/cache tests, eight staged shared-shell cache runs, five live-transcript-close repetitions, and the full synthetic native UI pipeline passed. No new live provider calls or physical capture acceptance was established by those checks.
- Shared note cache is wired into the iPhone shell. Offline relaunch, refresh, revision invalidation and deletion were exercised. Real-provider Release simulator owner switching and cache clearing are now verified; see the lifecycle evidence below.
- A real close-button tap loss during transcript updates was reproduced and repaired. Approved shared CSS, HTML, iconography, typography and motion were preserved.
- Merged phone build was signed, installed in place and launched on the existing iPhone; no reset. Receipts: `/tmp/integration-device-install-retry.json`, `/tmp/integration-device-launch.json`, `/tmp/integration-device-bundle.json`. Temporary local receipts may disappear; preserve sanitized durable evidence before release.
- Latest phone inspection used the same baseline with temporary DEBUG-only font diagnostics. User/agent computed font family, size (16px) and weight (430) matched; Bold Text was enabled. Founder confirmed they look the same. Diagnostics were reverted from source; no UI fix or data change. Receipt `/tmp/message-font-phone-final.json`; do not mistake this diagnostic binary for an archived release.
- Hosted candidate: `208ca34bbc5fa81278c5ea5720230d1f36caec4b`, normal Render deploy `dep-daubmspsrm7s73bke6n0`, service `srv-daqtfs7lot8c73dleuug`. Auto-deploy remains off. Live schema is 21 and account deletion is enabled. Founder Google server mapping is applied, with complete row/file preservation checks and fresh off-host backups. The matching physical Release candidate passed founder Google sign-in, exact-byte native storage migration and signed-in relaunch; the founder confirmed existing notes/chat and opening an existing note. See [live cutover evidence](../qa/founder-migration/live-cutover.json). The dependent PR stack remains unmerged pending its acceptance gates.
- Draft PR159 implements native accounts. Both providers passed basic sign-in/sign-out/relaunch on the signed Release simulator (native source `07f9977`); Apple reauthentication reused its original owner. This is not populated two-user isolation, actual refresh/revocation or physical-device acceptance.
- The dependent account-erasure storage branch starts from PR159 `8568a20`, not an independently merged baseline. Its schema-21 operation removes one enrolled owner’s complete memory/chat/source content and rejects stale writes; see [local QA and remaining gates](../qa/account-erasure-storage/README.md). A further dependent [backend workflow candidate](../qa/account-deletion-workflow/README.md) adds a default-off deletion endpoint and local retry/isolation evidence. Fresh-provider-proof backend recovery is also locally verified. The further dependent [native deletion candidate](../qa/native-account-deletion/README.md) has locally tested owner cleanup/retry and inspected simulator presentation, with default-off UI. A further [Google revocation candidate](../qa/google-account-revocation/README.md) adds original-grant revocation and isolated Keychain/relaunch checks. The latest [server finalization candidate](../qa/deletion-finalization/README.md) keeps Google identities reserved until server-observed revocation and passes a real native/TLS/Keychain flow with synthetic provider responses. The subsequent [real-provider simulator run](../qa/account-lifecycle/README.md) passed Google and Apple enrollment, relaunch, deletion, successful provider revocation responses and signed-out relaunch against isolated local data. Later updates below supersede this initial status; physical acceptance and backup retention policy remain unfinished.
- App Store Connect login worked. No app record existed. The founder accepted the updated Developer Program License Agreement on September 29; a fresh App Store Connect reload verified that its warning cleared. Xcode team `7HF6VDCZF7` was available for development signing; archive/distribution signing remains unverified.
- No TestFlight build uploaded and no testers invited. Accounts, prices, paywall and real subscriptions remain unfinished.

## Product decisions versus proposals

Founder asks to include accounts, paywall and price plans in this release plan. Freemium plus subscription is already agreed. Founder selected both Google and Apple sign-in on September 29, with Google above Apple in the UI. The earlier Apple-first/Google-later proposal is superseded. Founder confirmed separate Google and Apple accounts with persistent sign-in on September 30, and selected Google for the existing founder development data. See the [migration preparation](founder-account-migration.md); server and physical Google migration acceptance are complete. Exact prices, allowances, billing periods and paid-pilot timing are **not selected**. Free and Pro, and a free student pilot before charging while purchases are tested in sandbox, remain proposals, not implementation facts or permission to charge.

Keep the five-minute internal capture cap until separately changed and validated. Do not promise full lectures. Calendar/email/messages, outside-knowledge expansion, TTS and silent always-on capture remain outside this release slice. Preserve the single persistent chat, ordinary multi-message interjections, Quiet/End bounds, upright paperclip, purple actions and approved shared interface. New account/paywall surfaces should follow that design, not redesign the app.

## Phases, packets and gates

| Phase | Bounded packets | Dependency and completion gate |
| --- | --- | --- |
| 0: establish release baseline | REBASE-0 verify main/runtime/build identities; DECIDE-0 prepare concrete account/provider and plan choices; APPLE-0 resolve agreement/app record | No assumption that a Debug install or old receipts prove Release readiness. Founder handles legal acceptance; no automatic paid calls. |
| 1: accounts and data lifecycle | ACCOUNT-1 authenticated enrollment/session refresh; ACCOUNT-2 sign-out, revocation and owner cache clearing; ACCOUNT-3 account deletion and existing-owner migration | Select auth contract first. Fresh Release install works without bundled developer credentials. Two actual users cannot read each other's notes/chat/memory or cached data. Preserve founder data during migration; prove deletion scope and retention policy. |
| 2: plans and limits | PLAN-1 measured cost/allowance proposal; PLAN-2 server-enforced allowance reservations and remaining-usage API; PLAN-3 limit/error UX | Founder selects numbers. Stable account identity first for enforcement. Cover capture, chat, notes, learning and proactive spending, including concurrent requests and retries. Existing notes remain readable at limit. No client-only enforcement. |
| 3: subscriptions and paywall | BILLING-1 StoreKit product/paywall UI; BILLING-2 verified transaction-to-account entitlement; BILLING-3 restore/manage lifecycle | Account and entitlement contracts accepted first. Sandbox purchase/cancel/pending/renew/refund/revoke/restore and expired/grace states; idempotent updates, account binding and offline reconciliation. Never ship a preview purchase button as working billing. |
| 4: deploy and validate Release | RELEASE-1 reviewed backend deploy/backup/rollback; RELEASE-2 bounded proactive Release wiring; RELEASE-3 assets/disclosures/archive; RELEASE-4 fresh install/update validation | Final native/backend version pairing; all critical failure paths pass. Release enrollment cannot depend on Debug import. Quiet/End/cancellation/budgets survive Release. Signing, app icon, permitted companion artwork, privacy/legal/support configuration and distribution metadata completed. |
| 5: TestFlight student pilot | PILOT-1 upload and independent installation; PILOT-2 short guided conversation and feedback | Explicit selected cohort/release route. A free pilot may precede commercial billing only by founder decision; exclude misleading purchase flows, keep real quotas. Paid launch requires phases 2–3 fully accepted. Capture real consented feedback without default transcript collection. |

## Safe parallelization

After contracts are fixed, account implementation, pricing/cost analysis and read-only release-assets audit can run independently. Serialize owner migration/cache invalidation, entitlements/usage reservations, schema migrations, deployment, signing and physical-device access. No concurrent writers in RoomWebModel/shared UI without explicit file ownership. Preserve the accepted baseline and use separate worktrees/DerivedData for authorized workers.

If the founder authorizes workers for execution, use bounded Astra/low packets with exact base SHA, files, feature map, verifier, failure cases and budget. This documentation request launches no workers. Workers submit reproducible evidence to the lead; the lead reviews actual outputs and explicitly accepts dependent work. No worker self-approval or broad “own billing” assignment.

## Verifiers and evidence

Use `python3 scripts/verify_feature.py --list` and [feature index](../features/context-map.md). Primary release gates: `access`, `pricing`, `subscriptions`, `distribution`, with impacted `note-cache`, `deletion`, `capture`, `chat`, `proactive` and `social-presence` contracts. Every feature keeps its own context and verifier. Planned feature evidence gates are runnable but intentionally incomplete until real receipts exist; this update does not implement missing auth/StoreKit tests.

Use `--checks-only` for existing local contracts, never as feature acceptance. Add purpose-built automated suites when the implementation exists. Submit exact source/configuration, fixture provenance, expected/observed behavior, raw sanitized receipt and inspected UI evidence. Review the final commit, not an earlier candidate. Real LLM changes require bounded approved final-model calls through the claimed pipeline; UI/cache mechanics should use fixtures. Simulator/StoreKit-local checks cannot establish App Store sandbox, physical haptics or actual microphone behavior.

Run manifest tooling checks after edits: `python3 -m unittest discover -s scripts/verification -p 'test_*.py'`. No requirement may be weakened to produce a green verifier. Account deletion differs from note deletion: deleting a note preserves past answers under existing policy; account erasure must address the account's full data lifecycle.

## Operational handoff and permissions

Continue from latest main in a suitable free worktree. Current accounts checkout: `/Users/n.chinlue/.codex/worktrees/account-sign-in/voice-companion`; original `/Users/n.chinlue/code/voice-companion` has unrelated local state and must be preserved. Never store keys/tokens in docs or evidence.

Founder authorized internal deployment and TestFlight setup/release validation. That does not authorize accepting legal agreements, choosing commercial prices, charging, arbitrary tester invitations, resetting production data, changing Render tier, or paid model runs without a bounded allowance. Founder subsequently authorized $5 total provider/API testing; [ledger](testflight-provider-budget.md) remains at $0 spent. Hosting upgrades, subscriptions and other purchases are excluded. Observe canonical stop-and-wait rules for required founder input. Ask for physical readiness before timed manual QA.

Render SSH works with the existing dedicated `voice_companion_render` identity; default SSH identity failure does not establish loss of access. Do not deploy until current config, active work, backup, migration and rollback checks are satisfied. Preserve runtime quotas and historical ledgers. App Store Connect agreement is a separate founder-dependent gate; do not silently accept it.

## First action for the next agent

Read this handoff and linked maps, verify current git/runtime state, and prepare the smallest accounts packet for the selected Google and Apple providers. Recheck whether Apple agreement acceptance is still pending before signing/upload work. Keep pricing/pilot decisions visibly open. Do not restart the completed UI redesign or rerun paid evaluations just because the agent changed. Basic provider enrollment is already evidenced; continue from the remaining lifecycle gates rather than repeating it.

## Handoff documentation validation

The 15 verifier self-tests pass, including catalog/manifest schema and context-map links. The stale cache-is-unimplemented self-test was updated to require pricing/subscriptions/distribution (which have no automated suites yet) to reject checks-only verification. Feature discovery lists the new pricing contract. This validates tooling and documentation structure, not account, billing or TestFlight behavior. App source and UI assets are unchanged by this checkpoint.

## Founder constraint: preserve the established design system

September 29 clarification supersedes the earlier blanket UI-code freeze: functional frontend wiring for Google/Apple sign-in and necessary account/privacy pages are authorized. The current UI design system is the source of truth. Reuse existing components, styling, typography, colors, spacing and motion; preserve established screens and interactions. Do not redesign, restyle or reinterpret the app's visual character while preparing TestFlight. Google remains above Apple. Verify functional additions in the actual app against the existing design system.


### September 30 lifecycle and migration evidence update

The [real-provider local QA](../qa/account-lifecycle/README.md) now covers populated
provider switching, backend refresh rotation/replay rejection, and populated Apple
deletion while preserving Google's notes/chat and all spending rows. Google then
reauthenticated to the same owner and stayed signed in after relaunch. Native
automatic timed refresh, real fresh-proof recovery,
independent-human isolation and physical acceptance remain open.

[Server migration](../qa/founder-migration/README.md) passed a coordinated private
hosted-copy rehearsal. [Native migration](../qa/founder-native-migration/README.md)
preserved four copied phone sessions and 20 outbox records, and passed an isolated
four-launch actual runtime/Keychain interruption sequence with synthetic sessions.
Draft PR166 and PR167 remain undeployed/unmerged; no live founder migration occurred.
Fresh Google proof, coordinated operator cutover and physical migration remain
required. These additions supersede older pending-status wording above only for
the specific tested scopes; Phase 1 and TestFlight readiness are still incomplete.

Populated Google deletion also passed in the same isolated environment: real
revocation success, server/native content erasure, preserved budget history,
signed-out relaunch, and re-enrollment into a new empty owner. The native Notes
empty state was inspected. This completes that bounded check, not Phase 1.

### Live founder cutover — September 30, 07:35 UTC

Server migration applied after exact maintenance deployment/process verification,
zero active reservations and 24 fresh coordinated backups verified locally.
Every row in 42 memory and 18 usage tables was compared: only the selected Google
identity binding and five old credential flags changed. Other 22 database files
were byte-identical. Normal schema21 service and all workers are healthy.
The physical candidate preserves all four original session files and 20 outbox
files. Founder Google sign-in, the native move and persistent-session/content
acceptance subsequently passed as described below.
Do not replay the server migration or restore old ledgers over resumed activity.
See the [receipt](../qa/founder-migration/live-cutover.json). No paid calls.

Physical Google sign-in subsequently succeeded. Readback shows the native plan
removed, legacy sessions directory moved into the preserved account owner, and
all four session files plus 20 outbox files byte-identical. Hosted verification
confirms the selected Google binding, one valid session and existing 23 source,
four note and eight chat-turn rows. Controlled terminate/relaunch succeeded.
The founder then confirmed all three explicit checks: signed-in relaunch without
a prompt, existing notes/chat visible, and an existing note opens correctly.
This closes founder migration acceptance; remaining access gates include native
automatic refresh, real fresh-proof recovery, physical Apple switching, independent
human isolation and an implemented backup retention/restore policy.
