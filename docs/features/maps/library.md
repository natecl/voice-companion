# Recording library and sync

Feature ID: `library` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Save, reopen, attach, and sync recordings without loss. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

Recordings reopen locally; attaching one supplies context to the persistent main chat. Evidence upload and deletion have durable sync paths.

## Gaps and non-goals

Backend evidence sync is not a complete cross-device recording library. Persistent generated-summary caching is a separate planned feature.

## Flow and implementation entry points

Transcript reducer → local session JSON → durable evidence outbox → authenticated backend source/revision.

- [App/Sessions/SessionStore.swift](../../../App/Sessions/SessionStore.swift)
- [App/Sessions/MemorySync.swift](../../../App/Sessions/MemorySync.swift)
- [UITests/SavedRecordingUITests.swift](../../../UITests/SavedRecordingUITests.swift)

## Contracts and dependencies

Local save precedes upload. Failed sync preserves local content; revision checks and tombstones prevent stale uploads from resurrecting deleted recordings.

**Uses:** [Capture and live transcript](capture.md), [Tester access and account controls](access.md)

**Consumers / coordinated work:** [Meeting note summaries](meeting-notes.md), [Notes search](notes-search.md), [Past-context retrieval](recall.md), [Note deletion and retained answers](deletion.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: implemented foundations; fresh feature verification required.
- [Feature verifier contract](../verification/library.json): `python3 scripts/verify_feature.py library`.
- [Mechanical baseline and unresolved checks](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Offline save/relaunch, sync recovery and attaching a recording.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

Verify offline save/relaunch and outbox recovery; coordinate source IDs/revisions with notes and deletion before modifying shared storage.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [memory-foundation.md](../../memory-foundation.md)
- [companion-source-navigation.md](../../companion-source-navigation.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
