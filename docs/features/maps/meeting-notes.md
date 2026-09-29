# Meeting note summaries

> Release planning reference: [September 29 handoff](../../execution/testflight-release-handoff.md). This link does not expand the feature’s existing verification claims.

Feature ID: `meeting-notes` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Generate grounded summaries once; read/retry safely. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

Generated titles, overviews and sections are stored server-side. Reads do not regenerate notes; explicit retry is separate. Historical physical capture/notes/passage/reopen evidence exists.

## Gaps and non-goals

Reopening currently needs a server read/connectivity. No persistent phone summary cache or manual note editing. Fresh feature acceptance still requires actual generated output and rendered inspection.

## Flow and implementation entry points

Terminal source upload → revision-bound generation job → transcript-only model request → validation/storage → Notes view and supporting passages.

- [Backend/recording_notes.py](../../../Backend/recording_notes.py)
- [Backend/notes_generation.py](../../../Backend/notes_generation.py)
- [App/RecordingNotesView.swift](../../../App/RecordingNotesView.swift)
- [UITests/RecordingNotesUITests.swift](../../../UITests/RecordingNotesUITests.swift)

## Contracts and dependencies

Notes are derived summaries, not independently verified memory. Source changes invalidate notes; deletion removes them. Preserve full-width wrapping with no inline source-icon row.

**Uses:** [Recording library and sync](library.md), [Tester access and account controls](access.md)

**Consumers / coordinated work:** [On-device note caching](note-cache.md), [Notes search](notes-search.md), [Past-context retrieval](recall.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: implemented foundations; fresh feature verification required.
- [Feature verifier contract](../verification/meeting-notes.json): `python3 scripts/verify_feature.py meeting-notes`.
- [Mechanical baseline and unresolved checks](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Final note-generation configuration produces a faithful summary through service/storage; Render the actual summary and supporting passage; inspect failures/retry.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

Preserve generation/read separation; test failure/retry and readable native rendering. Supply revision/status contracts to the cache worker.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [recording-notes-plan.md](../../recording-notes-plan.md)
- [recording-notes-rollout.md](../../recording-notes-rollout.md)
- [qa/note-layout/README.md](../../qa/note-layout/README.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
