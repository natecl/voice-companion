# Capture and live transcript

Feature ID: `capture` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Microphone → transcript → stop → saved text. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

User-started Mac/iPhone microphone capture and saved text exist. Historical physical evidence covers locked-screen capture and interruption preservation. Speaker labels are best-effort and never verified identity.

## Gaps and non-goals

Internal capture remains capped at five minutes. Full-lecture reliability, Mac computer audio, imports, and silently always-on capture are not delivered.

## Flow and implementation entry points

Microphone permission → native audio lifecycle → hosted transcription → partial/final events → local save.

- [Backend/relay.py](../../../Backend/relay.py)
- [UnitTests/RecordingLifecycleTests.swift](../../../UnitTests/RecordingLifecycleTests.swift)
- [UITests/MicrophoneUITests.swift](../../../UITests/MicrophoneUITests.swift)

## Contracts and dependencies

Preserve received text on interruption; stop/finalization must not create another chat or silently retry a paid request. Text display cannot wait for speaker attribution.

**Uses:** [Recording library and sync](library.md), [Tester access and account controls](access.md)

**Consumers / coordinated work:** [Companion chat and follow-ups](chat.md), [Meeting note summaries](meeting-notes.md), [Automatic memory learning](memory-learning.md), [Proactive contributions](proactive.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: implemented foundations; fresh feature verification required.
- [Feature verifier contract](../verification/capture.json): `python3 scripts/verify_feature.py capture`.
- [Mechanical baseline and unresolved checks](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Actual microphone/provider capture, interruption and save/reopen.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

Invitation is proposed experience language for deliberately starting capture/participation. It must not obscure microphone state or change permission, Quiet versus End, or private dictation pause/resume semantics.

Exercise permission, interruption and stop/save recovery with saved events first; use real microphone/provider evidence only for the changed capture boundary.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [v1-acceptance.md](../../v1-acceptance.md)
- [reliability-edge-cases.md](../../reliability-edge-cases.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
