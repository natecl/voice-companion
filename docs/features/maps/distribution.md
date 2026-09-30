# TestFlight install and update

> Release planning reference: [September 29 handoff](../../execution/testflight-release-handoff.md). This link does not expand the feature’s existing verification claims.

Feature ID: `distribution` · Context reviewed September 30, 2026; see the handoff for exact source/configuration pairing.

## Purpose and user outcome

Correct signed release configuration and independently usable beta. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

UI PR154 and integration PR155 are merged. The dependent account candidate `208ca34` is deployed with schema21 and deletion enabled; its development-signed Release phone build passed Google migration and persistent sign-in/content checks. This is not an App Store distribution export. No TestFlight upload is established.

## Gaps and non-goals

The founder accepted the Developer Program agreement September 29 and the warning cleared. The founder created **Ellis: AI Notetaker**, Apple app ID `6817680460`, after Apple rejected `Ellis` as already used. On September 30, direct App Information inspection verified bundle ID `ai.voicecompanion.phone`, SKU `ellis-iphone-001` and English (U.S.). The record is in Prepare for Submission with no build selected; creating it is not a review submission or TestFlight upload. Distribution signing, icon, permitted artwork, privacy/legal/support metadata and fresh-tester access remain open. The EU trader-status notice is visible; no compliance declaration was submitted.

## Flow and implementation entry points

September 30 setup verification: the iOS 1.0 version is saved with **Manually
release this version**, confirmed again after reload. TestFlight shows **No
Builds**. Beta description, feedback email, privacy URL and review contact fields
remain empty. No review submission, tester group/invitation or legal/compliance
declaration was made. Before filling review metadata or uploading a build,
resolve the documented temporary companion-artwork distribution rights and
missing app icon; the existing UI design remains the source of truth.

Founder clarified that the final mascot will be supplied later. Do not block
unrelated account, pricing or billing engineering on that asset; keep it as a
pre-distribution gate. The current placeholder is not cleared for distribution.

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

Release feature remains incomplete. [Verifier](../verification/distribution.json): `python3 scripts/verify_feature.py distribution`. Its updated gates require final-configuration lifecycle evidence; existing local checks or preview navigation alone do not satisfy them. See the [handoff delivery ledger](../../execution/testflight-release-handoff.md) for merged, installed and deployed boundaries. No new account, billing or release behavior was tested in this documentation pass.

## Next bounded work

Resolve Release enrollment, activation and assets; review backend backup/deploy/rollback and version pairing; then archive/upload and test independent install/update.

## Supporting context and evidence

- [development.md](../../development.md)
- [demo-to-testflight-plan.md](../../demo-to-testflight-plan.md)
- [execution/demo-testflight-phases.md](../../execution/demo-testflight-phases.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
