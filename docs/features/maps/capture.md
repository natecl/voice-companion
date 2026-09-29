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

## CAPTURE-1 local recovery checkpoint — September 29, 2026

Candidate source `75f32b88a71495373bda868840852baa91c1c937`, based on `47eadb4c8be3a46593bb6f17250f4c24335ea02c`. Only `SessionController.interrupt(reason:)` changes product behavior: cancel preparation without mutating the previously opened recording when no capture connection exists. Active capture interruption still persists received text before cancellation. No retry, chat, audio routing, provider or storage-format change.

Reproduction uses the actual controller, transcript reducer and atomic JSON store: reduce checked-in synthetic provider events, save a completed recording, reopen it, start a new capture with pending preparation, then deliver the background lifecycle event. Before the fix, the saved file changed from 2,136 to 2,301 bytes, `completed` became false and an interruption reason was added (four assertions failed in the new test). After the fix, bytes remain identical immediately and after cancellation; a fresh controller reopens the completed transcript, exactly one session remains and no connection starts.

Verification: `RecordingLifecycleTests` passed all eight tests on macOS 26.6.2 / Xcode 27.0 (27A266a), including foreground interruption, active background capture, network failure, explicit stop, denied permission and preparation cancellation. This executes production lifecycle/reducer/disk code with injected preparation/connection boundaries; it is not microphone, provider, UI or physical-iPhone evidence. Fixture: `Fixtures/transcript-events.json`, SHA-256 `e0cd5886da647402ea73898f1c6b704ff2ce92a3113d3cf3e246dfbb4ca56ae3`.

Reproduce in an isolated checkout:

```sh
xcodegen generate
xcodebuild -project VoiceCompanion.xcodeproj -scheme Mac -destination 'platform=macOS' -derivedDataPath /tmp/VoiceCompanion-capture-recovery CODE_SIGN_IDENTITY=- -only-testing:CoreTests/RecordingLifecycleTests test
python3 scripts/verify_feature.py capture
python3 scripts/verify_feature.py library
```

The full capture/library verifiers each pass their mechanical contracts but correctly return `incomplete` for missing fresh behavior/inspection receipts; this narrow checkpoint does not mark either whole feature verified. Local raw logs: `work/capture-recovery/capture-recovery-before.log` and `capture-recovery-after.log`; result bundles: `Test-Mac-2026.09.29_04-28-34--0400.xcresult` (reproduction) and `Test-Mac-2026.09.29_04-29-17--0400.xcresult` (fixed), under the dedicated `VoiceCompanion-capture-recovery` DerivedData `Logs/Test` directory.

Zero paid calls. Candidate is not merged, deployed or installed on phone; orchestrator review is pending. Separate device follow-up, with readiness and device lease: open an existing completed recording, start capture while microphone permission is pending, background the app, return and confirm the original recording remains completed and unchanged with no automatic capture restart. Actual microphone/provider capture interruption remains the broader feature gate and requires its own authorized run.

## Next bounded work

Invitation is proposed experience language for deliberately starting capture/participation. It must not obscure microphone state or change permission, Quiet versus End, or private dictation pause/resume semantics.

Exercise permission, interruption and stop/save recovery with saved events first; use real microphone/provider evidence only for the changed capture boundary.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [v1-acceptance.md](../../v1-acceptance.md)
- [reliability-edge-cases.md](../../reliability-edge-cases.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
