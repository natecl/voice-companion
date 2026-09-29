# P0-C / ACCESS readiness audit — September 29, 2026

**Audit complete; independent TestFlight readiness remains unverified.** This is an offline repository/local-tool audit of `47eadb4c8be3a46593bb6f17250f4c24335ea02c`, the clean assigned `origin/main` baseline. Documentation-only delivery does not change runtime configuration. No deployment, archive, signing mutation, simulator/device use, account mutation, upload, invitation or paid provider call occurred. The default project checkout and its unrelated untracked project were untouched.

## Evidence and boundary

Environment: macOS 26.6.2 arm64, Python 3.13, Xcode 27.0 (27A266a). `xcodebuild`, `xcodegen`, `xcrun`, and `gh` are available. Local `security find-identity -v -p codesigning` returned two valid identities; Apple Development was present and Apple Distribution was absent. Only aggregate/class information was retained. Standard profile directories contained zero and one `.mobileprovision` files respectively; profile contents and identities were not inspected. These facts do not establish team membership, certificate entitlement, profile suitability or App Store Connect access. No login or remote account check was attempted.

| Layer | Configured/observed | Tested at this baseline | Still needed |
| --- | --- | --- | --- |
| Native target | iPhone only family 1, iOS 18 minimum, bundle `ai.voicecompanion.phone`, automatic signing | Read-only Release build settings resolve without error | Signed archive, artifact inspection and intended-device install/update |
| Version | Phone Info.plist fixes version `1.0`, build `1`; no selected team in resolved settings | Source/config inspection | Deliberate candidate version/build and native/backend identity pairing |
| Signing | Resolved Release identity is `iPhone Developer`; no selected team/profile specifier | Local identity availability only | Operator-selected team/distribution setup; do not infer absence in account from absence locally |
| Assets/disclosures | AppIcon setting exists, but no tracked asset catalog/icon set or privacy manifest found; legal links are previews | Repository inventory only | Release operator and UI owner prepare/verify necessary release assets and disclosures; no claim about current Apple submission policy |
| Enrollment | Admin exports private per-credential config; optional stable memory owner for renewal | Local private-file export, refusal to overwrite, renewal/revocation tests | A selected fresh-tester Release enrollment path without developer cable/file injection |
| Native auth | Release loads existing Keychain only; Debug imports `hosted-relay.json` | Source inspection; no fresh native execution | Fresh Release enrollment, expired/revoked recovery and account switch/sign-out |
| Isolation/revocation | Owner-scoped stores, hashed/expiring credentials and revocation | Actual loopback WebSocket handlers and temporary SQLite/files with synthetic upstreams | Integrated fresh two-tester acceptance, all relevant endpoints, device data invalidation |
| Participation | Native coordinator creation is inside `#if DEBUG`; backend phone QA registry gates its pilot path | Source inspection | Reviewed distribution-configured controls and accepted real model/native integration |
| Installed/deployed/uploaded | Historical runbooks describe internal development installations | No current phone/hosted/App Store inspection | Exact candidate backend/native pairing, signed install/update, separately authorized upload/invitations |

The repository's current one-liner and product behavior were preserved. Historical runbooks remain evidence for their recorded versions, not claims about this baseline or today's hosted state. The five-minute capture cap must remain explicit.

## Reproduced checks

Run from this checkout/base:

```sh
python3 scripts/verify_feature.py distribution
python3 scripts/verify_feature.py access
PYTHONPATH=Backend python3 -m unittest -v Backend.test_admission Backend.test_admin Backend.test_hosted_startup Backend.test_hosted_relay Backend.test_memory.MemorySocketTests Backend.test_companion_service.CompanionServiceTests.test_empty_chat_invalid_input_and_owner_isolation Backend.test_companion_service.CompanionServiceTests.test_deletion_and_revocation_interrupt_stalled_answer
xcodebuild -project VoiceCompanion.xcodeproj -scheme Phone -configuration Release -sdk iphoneos -showBuildSettings -disableAutomaticPackageResolution -skipPackageUpdates -derivedDataPath work/readiness-derived
```

- [Distribution receipt](distribution-verifier.json): exit 1, incomplete; required signed-device behavior and inspection receipts absent. No dedicated mechanical distribution suite exists in its manifest.
- [Access receipt](access-verifier.json): exit 1, incomplete; mechanical checks pass, required service/native behavior and inspection receipts absent. The verifier correctly does not convert mechanical success into acceptance.
- [Targeted execution log](tests-passed.txt): **22 tests passed**. Actual local sockets exercised unauthorized rejection before upstream, repeated sessions/budget denial, active and finalization revocation, disconnect cleanup, memory owner mismatch and deletion/reopen, isolated companion history for a second credential, and revocation of a stalled answer. Disk tests exercised private exports, renewal retaining owner, accounting reopen, and startup lock/crash recovery. Inspect the named test bodies for each contract; the two-user history case is not exhaustive endpoint isolation.
- [Initial failed invocation](tests-initial-failed.txt): omitted `PYTHONPATH=Backend`, causing seven import errors before any test body ran. The feature runner supplies that path itself. Correcting the direct invocation produced the passing run; no application fix or paid retry was involved.
- [Resolved settings](release-settings.txt): zero build-settings errors. This command did not compile, archive or validate distribution signing. No simulator claim follows from it.

All test data was synthetic in temporary local directories, providers were local fixtures, and paid usage was zero. These results establish bounded access mechanics, not live model quality, microphone behavior, hosted account state or device appearance. Raw feature receipts intentionally remain incomplete; this audit does not fabricate replacement full-feature receipts.

## Prioritized next acceptance slices

1. **ACCESS-1: fresh private-pilot enrollment and invalidation.** Primary selects a minimal enrollment contract for Release; existing admin provisioning can remain the operator foundation, but Debug file transfer cannot be the tester path. Keep credentials individual and owners stable through renewal. Implement explicit credential removal and coordinated cancellation/clearing of owner-scoped chat, recordings and note caches at sign-out/switch. `RelayCredentialStore` currently has save/load only, and `ExperienceAccountView` says sign-in, sign-out and deletion are not connected. Agree the invalidation interface with CACHE-1 before shared native edits. Acceptance: fresh empty Keychain, two isolated testers, rejected/expired/revoked access, renewal, switch/sign-out/relaunch and no stale owner data; inspect actual Release app/service behavior.
2. **Distribution configuration slice after integrated feature acceptance.** Wire approved participation without Debug launch arguments, retain Quiet/End/cancellation and bounded budgets. Pin intended backend commit/flags/model configuration and native version/build; inspect the produced app's Info.plist, entitlements, icons and configuration. `scripts/check.sh` only supports build/test, defaults development signing and uses shared DerivedData; it is not an archive/export preflight and was not run here. Use an isolated release output directory with one operator.
3. **Candidate signing/archive slice.** With operator-selected authorized team/signing access, create and inspect the signed Release archive and export configuration. Local lack of a distribution identity is a readiness gap, not proof an account cannot sign. No automatic provisioning updates or credential creation was attempted. Record archive hash, signing result, exact app/backend versions and rollback/update expectations. A fresh install and upgrade must retain intended local data/Keychain access; uninstall is not evidence of clean enrollment.
4. **Independent pilot acceptance and only then authorized distribution.** Exercise approved short-session behavior on a fresh tester device, revocation/sign-out, offline/recovery, update continuity and feedback path. Preserve preview labeling until actual account/legal flows exist. Resolve privacy/retention/deletion disclosures with the founder before invitations; existing historical runbook explicitly defers full erasure/retention operations. Confirm selected runtime quota behavior: admission counts category/day usage across credentials, so per-tester enrollment alone does not establish per-tester allowances. Do not raise limits implicitly. Upload/tester invitations remain separate authorized actions.

## Access handoff and stop boundary

No new founder access was needed to complete this bounded audit. Account membership, App Store app record, signing/provisioning changes, candidate archive/install and uploads were outside it and remain unchecked. Before that next gate, primary must obtain the authorized release operator/team and permitted account/signing scope; before device QA it must coordinate a lease and founder readiness if participation is needed. No account access was bypassed or replaced with simulated success.

Primary owns integration/acceptance and all shared plan/catalog/verifier changes. This packet changes only this report/evidence directory and the distribution context map. ACCESS map delta for primary: existing local access foundations now have fresh 22-test evidence with explicit scope; independent enrollment/sign-out and complete two-tester/device acceptance remain missing. Rollback is a documentation-only revert; no runtime state changed.
