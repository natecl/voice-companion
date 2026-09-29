# Composer dictation

Feature ID: `dictation` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

On-device speech draft, discard, append and explicit Send. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

On-device recognition and bounded native acceptance are documented. Dictation is distinct from saved meeting capture; current composer interaction supersedes earlier Stop/Clear-draft UI history.

## Gaps and non-goals

Supported on-device locale is required; no silent cloud fallback. Backend budget tests do not establish native recognition, permissions or interruption correctness.

## Flow and implementation entry points

Composer mic → Apple on-device Speech → temporary speech draft/waveform → discard or arrow-send/append → ordinary chat submission.

- [App/Sessions/ComposerDictation.swift](../../../App/Sessions/ComposerDictation.swift)
- [UnitTests/ComposerDictationTests.swift](../../../UnitTests/ComposerDictationTests.swift)
- [UnitTests/DictationCallbackTests.swift](../../../UnitTests/DictationCallbackTests.swift)

## Contracts and dependencies

Discard removes the new dictated segment without destroying pre-existing text. Preserve explicit send and existing text. Coordinate microphone ownership with capture; never silently lose draft text on callback/background transitions.

**Uses:** [Companion chat and follow-ups](chat.md), [Capture and live transcript](capture.md)

**Consumers / coordinated work:** None required in this map.

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: implemented foundations; fresh feature verification required.
- [Feature verifier contract](../verification/dictation.json): `python3 scripts/verify_feature.py dictation`.
- [Mechanical baseline and unresolved checks](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Actual dictation recognition, discard/send, permission and interruption; backend budget test alone is insufficient.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

Use callback and state tests, then exercise recognition, existing-text append, discard/send and permission/interruption on the actual device when changed.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [companion-feel-and-dictation.md](../../companion-feel-and-dictation.md)
- [native-experience-ui.md](../../native-experience-ui.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
