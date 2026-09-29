# On-device note caching

Feature ID: `note-cache` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Instant persistent/offline summaries with owner/revision-safe refresh. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

Server-side notes persist, but the current native view fetches on open/reactivation. This map describes an approved next implementation, not a delivered local cache.

## Gaps and non-goals

Disk persistence, stale-content display, owner isolation, refresh coalescing, and deletion/sign-out/reset invalidation need implementation and dedicated automated tests.

## Flow and implementation entry points

Planned: authenticated note read → account/source/revision keyed disk cache → immediate local render → coalesced refresh → atomic cache update.

- [App/RecordingNotesView.swift](../../../App/RecordingNotesView.swift)
- [App/Sessions/RecordingNotes.swift](../../../App/Sessions/RecordingNotes.swift)

## Contracts and dependencies

Never blank valid cached content on refresh failure. Never show another account’s note. Reads/refresh must not pay to regenerate notes. Source deletion and known revision changes invalidate the corresponding entry.

**Uses:** [Meeting note summaries](meeting-notes.md), [Tester access and account controls](access.md), [Note deletion and retained answers](deletion.md)

**Consumers / coordinated work:** [TestFlight install and update](distribution.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: planned; persistent cache not implemented.
- [Feature verifier contract](../verification/note-cache.json): `python3 scripts/verify_feature.py note-cache`.
- [Mechanical baseline and unresolved checks](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Implement and exercise disk persistence, invalidation, owner separation and refresh coalescing; Cold launch/offline read, refresh success/failure, deletion and sign-out.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

Deliver one bounded persistence/read/refresh slice with disk/relaunch/offline tests and actual app inspection; agree cache ownership and invalidation interfaces before parallel edits.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [execution/demo-testflight-phases.md](../../execution/demo-testflight-phases.md)
- [recording-notes-rollout.md](../../recording-notes-rollout.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
