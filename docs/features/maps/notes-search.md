# Notes search

> Release planning reference: [September 29 handoff](../../execution/testflight-release-handoff.md). This link does not expand the feature’s existing verification claims.

Feature ID: `notes-search` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Relevant notes found with correct source and navigation. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

Notes search and note-to-original-passage discovery exist. Search is explicit navigation; proactive recall is a separate context-selection path.

## Gaps and non-goals

Search UI, empty/error handling and opening the correct note need current rendered acceptance. This is not web search or a connected-source search product.

## Flow and implementation entry points

Search query → owner/revision-bound notes index → results/snippets → selected note/transcript.

- [Backend/notes_search.py](../../../Backend/notes_search.py)
- [App/CompanionRootView.swift](../../../App/CompanionRootView.swift)

## Contracts and dependencies

Do not reveal another owner’s data, stale revisions or deleted sources. A generated summary snippet must not be promoted to independently verified knowledge.

**Uses:** [Meeting note summaries](meeting-notes.md), [Recording library and sync](library.md), [Tester access and account controls](access.md)

**Consumers / coordinated work:** [Past-context retrieval](recall.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: implemented foundations; fresh feature verification required.
- [Feature verifier contract](../verification/notes-search.json): `python3 scripts/verify_feature.py notes-search`.
- [Mechanical baseline and unresolved checks](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Search results, empty/error state and opening the correct note.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

Exercise relevant/empty/error results and correct-note navigation; keep index invalidation aligned with source updates and deletion.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [simple-memory-foundation.md](../../simple-memory-foundation.md)
- [recording-notes-plan.md](../../recording-notes-plan.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
