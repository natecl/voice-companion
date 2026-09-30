# Capture teardown regression — September 30, 2026

Bounded macOS native controller execution against base
`d9101a0ef10fa6a36c2de01c93ea94d704967850`. No UI test, simulator, physical device,
Keychain, real microphone, server or paid provider was used. Production code was
unchanged for this baseline reproduction.

Two tests added to `UnitTests/RecordingLifecycleTests.swift` exercise the actual
`SessionController`, transcript reducer, owner-scoped `SessionStore`,
`MemorySync` and `MemoryOutbox`, using disposable directories and a synthetic
`RecordingConnection`. Its delayed receive remains inside `run`'s callback
lifetime. Cancellation is recorded, then an explicitly released pending receive
invokes the real reducer; this models a callback already in flight at teardown.
It is not proof that a particular provider/socket reproduced this timing.

## Reproduced failure

`testSignOutDuringCaptureRejectsLateEventsAndPreservesOwnerStorage` starts owner
A capture, persists “Before sign-out”, invokes `endAccountSession`, and directly
inspects the interrupted source before releasing the late callback. It verifies
connection cancellation, owner-A interruption, owner-B isolation and stopped
synchronization. After the callback, three assertions fail:

- Saved source includes “Late private words”.
- The preserved owner-A outbox includes those late words.
- Reopening owner A's store retains those late words.

Owner B remains empty and no sync operations are sent. This is a late-write
teardown defect, not demonstrated cross-owner disclosure.

`SessionController.startRecording`'s `onEvent` callback applies/persists without
a cancellation fence (`App/Sessions/SessionController.swift:207–212` in baseline).
`endAccountSession` stops synchronization and cancels recording, but a pending
receive can still invoke that callback. Root owns the production fix. A minimal
fix should reject canceled/stale callbacks before changing transcript/storage;
review the adjacent ready/finishing callbacks and post-run completion boundary
for the same lifecycle problem.

`testSignOutDuringPreparationPreservesPreviouslyOpenedOwnerRecording` passes:
sign-out while permission/configuration preparation is suspended creates no
connection or new session, preserves the older completed recording's exact file
bytes and queued operation, and reopens the original words. Its sync instance is
already stopped to isolate preparation/storage from constructor recovery work;
active synchronization teardown is exercised by the first test.

## Exact execution

`project.yml` defines scheme **Mac**, not VoiceCompanion. The first ordinary
command stopped before tests because the application target lacked a Mac App
Development profile. No provisioning update was requested. Local unsigned
artifacts allowed the existing CoreTests bundle to execute:

```sh
xcodebuild test -project VoiceCompanion.xcodeproj -scheme Mac \
  -destination 'platform=macOS' \
  -derivedDataPath /tmp/ellis-capture-isolation-tests \
  -only-testing:CoreTests/RecordingLifecycleTests CODE_SIGNING_ALLOWED=NO
```

Observed: **10 tests executed; 1 test failed with 3 assertion failures; 9 passed**.
The [sanitized native output](capture-teardown-baseline.txt) preserves the failure.
Original local logs are `/tmp/ellis-capture-isolation-baseline.log` and
`/tmp/ellis-capture-isolation-baseline-unsigned.log`.

Baseline SHA-256:

```text
40e7a26daf13dedaa0699305a4ef86f2913203b75e34c8b612d5646641c7c7a6  App/Sessions/SessionController.swift
162ce4ab35e9dde961e282e2fff05f891c377e747590d5a5f8acf31cce31b8cb  UnitTests/RecordingLifecycleTests.swift
```

This evidence supports the controller portion of access behavior 2. It does not
establish the profile-action/notification bridge, real microphone teardown,
provider revocation, physical behavior, or overall Phase 1 completion. No new
release requirement is introduced; the regression tests the existing sign-out
teardown and owner-isolation contract.

## Root fix independently verified

Root added cancellation/session fences before capture callbacks mutate state,
and checks cancellation after `run` returns. Independent inspection confirms
that the `onEvent` fence precedes reducer/storage writes, and that late ready or
finishing callbacks cannot resume the canceled recording's presentation state.
The new active-teardown regression now passes: only pre-sign-out words persist,
the owner-A interrupted outbox remains queued without network activity, and
owner B remains empty. No production file was edited by the reviewing worker.

Final command:

```sh
TEST_RUNNER_VOICE_TEST_PYTHON=/tmp/ellis-auth-venv/bin/python \
xcodebuild test -project VoiceCompanion.xcodeproj -scheme Mac \
  -destination 'platform=macOS' \
  -derivedDataPath /tmp/ellis-capture-isolation-tests \
  -only-testing:CoreTests/RecordingLifecycleTests \
  -only-testing:CoreTests/MemoryTests \
  -only-testing:CoreTests/AccountSessionTests CODE_SIGNING_ALLOWED=NO
```

**27 tests passed, zero failures**: ten recording lifecycle, eight memory and
nine account-session tests. The existing memory test used its real local socket
fixture with the already-installed Python dependencies. The first broadened run
omitted `VOICE_TEST_PYTHON` and failed because the default Python lacked
`websockets`; this was an environment failure, not silently accepted or skipped.
Both [that output](capture-teardown-python-environment-failure.txt) and
[final passing output](capture-teardown-fixed.txt) are preserved.

Final tested SHA-256:

```text
14bc20690a4986dd380865196732cb40621c052733c51d202daf2688145ee682  App/Sessions/SessionController.swift
162ce4ab35e9dde961e282e2fff05f891c377e747590d5a5f8acf31cce31b8cb  UnitTests/RecordingLifecycleTests.swift
```

All earlier evidence limits still apply. This is verified native controller and
local socket behavior, not live microphone/provider or physical-device evidence.
