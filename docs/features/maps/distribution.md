# TestFlight install and update

Feature ID: `distribution` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Correct signed release configuration and independently usable beta. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

Native build/check tooling and historical internal phone installs exist. These are prerequisites, not evidence that an independent TestFlight tester can use the product.

## Gaps and non-goals

Current signing/access, release flags, independent enrollment and full install/update acceptance remain unverified. Five-minute capture cap must be accurately disclosed.

## Flow and implementation entry points

Reviewed feature evidence + version pairing → signed archive/configuration → authorized TestFlight upload → independent install/update.

- [project.yml](../../../project.yml)
- [scripts/check.sh](../../../scripts/check.sh)
- [App/Transcription/RelayConfiguration.swift](../../../App/Transcription/RelayConfiguration.swift)

## Contracts and dependencies

One release operator; serialize signing, deployment and shared device use. Debug-only activation cannot count as release readiness. No upload/invitation follows automatically from passing a verifier.

**Uses:** [Tester access and account controls](access.md), [Capture and live transcript](capture.md), [Meeting note summaries](meeting-notes.md), [Companion chat and follow-ups](chat.md), [Proactive contributions](proactive.md), [On-device note caching](note-cache.md)

**Consumers / coordinated work:** None required in this map.

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: internal foundation; independent beta readiness unverified.
- [Feature verifier contract](../verification/distribution.json): `python3 scripts/verify_feature.py distribution`.
- [Mechanical baseline and unresolved checks](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Signed release install/update and independent tester access; intended native/backend version pairing.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

Perform a read-only readiness audit and prepare exact native/backend version evidence; release only after demo and access gates are accepted.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [development.md](../../development.md)
- [demo-to-testflight-plan.md](../../demo-to-testflight-plan.md)
- [execution/demo-testflight-phases.md](../../execution/demo-testflight-phases.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
