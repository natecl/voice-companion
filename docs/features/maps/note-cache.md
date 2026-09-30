# On-device note caching

> September 30 delivery context: [release handoff](../../execution/testflight-release-handoff.md). This map distinguishes source implementation from recorded deployment, installation and bounded verification; historical receipts do not attest current runtime state.

Feature ID: `note-cache` · Context reviewed September 29, 2026 against integration `b9bfb68` and UI main `dd907d4`.

## Purpose and user outcome

Instant persistent/offline summaries with owner/revision-safe refresh. Product direction is an invited AI social presence with personal continuity; the retained agreed one-liner is **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

The merged CACHE-1 integration implements persistent ready-summary storage, immediate local note/title reads, coalesced open/reactivation refresh, and source deletion invalidation. Typed `source_unavailable`/`stale_notes` service errors clear cached content/title; transport failures preserve valid content. Revision markers survive invalidation and deletion tombstones prevent later resurrection. Both deletion methods finish selection/library/outbox updates even if cache removal fails, with an explicit cleanup warning. Server-returned generation version is stored with owner/session/revision identity; local schema version remains separate. The backend remains canonical. See [bounded QA and screenshots](../../qa/note-cache/README.md). Shared iPhone integration and its fresh evidence are in the [primary review](../../qa/phase-integration/README.md). Deployment and physical installation are separate.

## Gaps and non-goals

Sign-out and account-transition entry points now clear owner-scoped state. Populated Google/Apple simulator switching and deletion verify cache separation and clearing in the account candidate; see [lifecycle evidence](../../qa/account-lifecycle/README.md). Token renewal is not an owner change. This bounded evidence does not complete physical deletion or independent-person acceptance. No physical locked-storage or live generation claim.

## Flow and implementation entry points

Candidate: authenticated note read → account/source/revision keyed disk cache → immediate local render → coalesced refresh → atomic cache update.

- [Shared iPhone model](../../../App/RoomWebModel.swift)
- [App/RecordingNotesView.swift](../../../App/RecordingNotesView.swift)
- [App/Sessions/RecordingNotes.swift](../../../App/Sessions/RecordingNotes.swift)
- [Cache module](../../../App/Sessions/RecordingNotesCache.swift)
- [Dedicated tests](../../../UnitTests/RecordingNotesCacheTests.swift)
- [Current shared-iPhone staged tests](../../../UITests/SharedRoomCacheUITests.swift) and [runner](../../../scripts/check-shared-note-cache.py)
- [Earlier SwiftUI simulator tests](../../../UITests/RecordingNotesCacheUITests.swift)

## Contracts and dependencies

Never blank valid cached content on refresh failure. Never show another account’s note. Reads/refresh must not pay to regenerate notes. Source deletion and known revision changes invalidate the corresponding entry.

**Uses:** [Meeting note summaries](meeting-notes.md), [Tester access and account controls](access.md), [Note deletion and retained answers](deletion.md)

**Consumers / coordinated work:** [TestFlight install and update](distribution.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: CACHE-1 candidate; eleven dedicated CoreTests and bounded simulator scenarios. Full feature remains incomplete pending account lifecycle integration.
- [Feature verifier contract](../verification/note-cache.json): `python3 scripts/verify_feature.py note-cache`.
- [Mechanical baseline and unresolved checks](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Implement and exercise disk persistence, invalidation, owner separation and refresh coalescing; Cold launch/offline read, refresh success/failure, deletion and sign-out.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

Cache/shared-UI integration is merged in PR155; account-transition wiring is implemented in the unmerged account stack. Complete remaining Phase 1 acceptance while preserving cancellation and clearing before exposing the next owner; token renewal is not an owner change. Existing `deleteFromLibrary(_:)` and `deleteCurrent()` invoke source-scoped invalidation after successful local deletion. Keep visuals independent.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [execution/demo-testflight-phases.md](../../execution/demo-testflight-phases.md)
- [recording-notes-rollout.md](../../recording-notes-rollout.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
