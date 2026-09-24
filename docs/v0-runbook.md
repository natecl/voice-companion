# Internal V0 runbook

Status: internal V0 accepted September 24, 2026 under the revised best-effort diarization scope. Both closeout UI checks passed; known limitations remain explicit.

Scope: microphone → live text → Stop/finalize → local save/reopen, on Mac and physical iPhone. Speaker labels are best-effort by explicit founder decision. This is a bounded internal development build, not a public release or the always-on companion.

## Use the installed apps

The Mac development relay must be running for live transcription. The phone needs network access to the Mac; a USB connection alone does not supply the relay network path. Replay sample works without the relay, microphone, or provider.

1. Start the relay and launch the app with fresh configuration using the platform instructions below.
2. Click Start recording. Wait for Recording before speaking; Connecting is not active capture.
3. Text appears as results arrive. Speaker pending means a label is unavailable; existing words need not wait for it. Numeric labels may arrive later, change, or be inaccurate. They do not identify which person is you.
4. Click Stop recording. Capture stops, then Finishing waits for final results. Saved means completed. Incomplete means available text was preserved but the recording did not finish normally.
5. Back to sessions opens saved recordings. Delete session requires confirmation and permanently removes that local transcript.

Sessions currently stop at approximately five minutes. Keep the iPhone app foregrounded and the phone awake; backgrounding/interruption safely ends capture rather than continuing recording. Headphones change which microphone is used. A microphone does not directly capture computer audio playing through headphones.

## Prerequisites and build

Run commands from the repository root. Validated tools: Xcode 27.0, XcodeGen 2.46.0, Swift 6.4, Python 3.13 with `Backend/requirements.txt` installed. Have an authorized Apple development signing team and paired iPhone. Set `DEVELOPMENT_TEAM` to your team and `DEVICE_ID` to the paired device identifier from `xcrun devicectl list devices`.

Store the provider key as `XAI_API_KEY` in the ignored root `.env`, save it, and restrict the file to owner access (`chmod 600 .env`). Do not put that key in the app, client configuration, screenshots, or Git. Existing credentials should not be printed or replaced during routine setup.

```sh
scripts/check.sh mac build
scripts/check.sh device build
```

Export `DEVELOPMENT_TEAM` for both commands and `DEVICE_ID` for the device build. Stable development signing preserves the app's microphone permission identity. Both commands regenerate the Xcode project; do not run these wrappers concurrently. Products are under `~/Library/Developer/Xcode/DerivedData/VoiceCompanion-mac/Build/Products/Debug/` and `VoiceCompanion-device/Build/Products/Debug-iphoneos/`.

## Mac live transcription

Quit existing VoiceCompanion instances before relaunching with configuration; an old instance can have no relay settings. In a terminal, start exactly one relay:

```sh
python3 Backend/relay.py
```

Leave that terminal running. In another terminal, from the repository root:

```sh
open /Users/n.chinlue/Library/Developer/Xcode/DerivedData/VoiceCompanion-mac/Build/Products/Debug/VoiceCompanion.app --args --relay-config "$PWD/work/relay-client.json"
```

The app path above is for this development Mac; use the equivalent DerivedData path on another machine. Approve microphone access if requested. No capture begins until Start recording.

## iPhone live transcription

Stop the existing relay with Ctrl-C first. Prepare the local TLS certificate when first setting up, when its seven-day validity expires, or when the Mac's local address changes:

```sh
python3 Backend/prepare_lan.py
python3 Backend/relay.py --lan
```

This binds to the Mac's specific local address and loopback, not a public service. It does not change system trust. Keep the relay terminal running. In another terminal, install the build if needed and copy the fresh configuration:

```sh
xcrun devicectl device install app --device "$DEVICE_ID" "$HOME/Library/Developer/Xcode/DerivedData/VoiceCompanion-device/Build/Products/Debug-iphoneos/VoiceCompanion.app"
xcrun devicectl device copy to --device "$DEVICE_ID" --source work/relay-phone.json --destination Documents/relay-client.json --domain-type appDataContainer --domain-identifier ai.voicecompanion.phone
xcrun devicectl device process launch --terminate-existing --device "$DEVICE_ID" ai.voicecompanion.phone --relay-check
```

The reachability check makes no provider call. Approve Local Network access if requested. After it succeeds, relaunch without the diagnostic flag:

```sh
xcrun devicectl device process launch --terminate-existing --device "$DEVICE_ID" ai.voicecompanion.phone
```

Then Start recording. Keep the Mac/relay awake and on the reachable network. Restarting the relay rotates its client token: recopy configuration each time. LAN mode also permits the Mac launch instructions above; the two apps share the same relay budget.

## Development budget and recovery

The relay allows **one upstream attempt per process**, not unlimited everyday sessions. It also caps submitted audio at 310 seconds and server wall time at 330 seconds; the app's normal capture limit is 300 seconds. After an attempt, intentionally stop/restart the relay for a fresh budget. Never retry automatically. At the previously recorded streaming rate, 60 seconds costs about $0.0033; estimates are not verified invoices.

| Symptom | Recovery |
| --- | --- |
| Microphone access is off | Enable VoiceCompanion in platform microphone privacy settings, then retry |
| Missing relay configuration | Quit the old app instance; launch the Mac with its config or recopy iPhone configuration |
| Relay limit reached / rejected connection | Inspect the prior run first; restart the relay only when intentionally authorizing another attempt |
| Phone cannot reach relay | Confirm LAN reachability, Local Network permission, current certificate/address, running relay, and freshly copied configuration |
| Headset disconnect / app interruption | Available text remains saved as incomplete; start a new session when ready |
| Network/provider error | Read incomplete status; check relay logs and configuration before a deliberate retry |
| Device authentication blocks testing | Unlock the phone and complete the requested authentication; do not bypass or repeatedly retry |

Raw audio is not retained by the app. Transcripts are stored locally in Application Support/VoiceCompanion/sessions (inside the app container on iPhone), with no sync. Test replays use separate VoiceCompanion-QA storage. Provider processing still sends audio externally; server-side retention is not established by the local no-audio-retention policy.

## Evidence and acceptance limits

- Real microphone transcription, Stop/finalization, save/reopen: independently exercised on Mac and physical iPhone; see [development evidence](development.md).
- Five-minute sessions and resource observations on both devices: [five-minute checkpoint](five-minute-checkpoint.md).
- Permission denial/restoration, empty transcripts, physical USB/AirPods input loss, and local socket failure preservation: [reliability checkpoint](reliability-edge-cases.md).
- Speaker labels: [known human-speech attribution errors](human-speaker-evaluation.md) remain unresolved. The founder accepts them for this trial; the failed strict evaluation has not been turned into a passing benchmark.
- Text-before-label UI behavior: targeted cached-provider replay check on both platforms, with text visible while Speaker pending, then later labels, no duplicated final segment, and persistence after relaunch. Both checks passed; result references are recorded below.

Cached replay validates the app's handling of available events, not today's provider/network latency or a live speaker-label timing guarantee. No fresh paid run is required to establish that the UI does not wait for labels. Broader noisy/overlapping speech, lecture-length sessions, battery endurance, and older supported OS versions remain unverified. Provisioned deployment targets are not tested compatibility claims.

Grok is the working internal provider, not a broad quality benchmark winner. Production authentication, retention review, distribution, billing, cross-device sync, background/always-on recording, computer audio, notes, Q&A, and attribution-dependent memory remain outside this release boundary.

## Targeted verification

The closeout extends `FoundationUITests/testReplayPersistsAcrossRelaunch`, using the checked-in synthetic-speech provider response fixture. It checks actual rendered text before speaker labels, later Speaker 1/2 labels, final segment replacement, saved reopening, and deletion confirmation. It makes no microphone or provider calls. Run just that method with `xcodebuild -only-testing:MacUITests/FoundationUITests/testReplayPersistsAcrossRelaunch` (Mac) or `PhoneUITests/FoundationUITests/testReplayPersistsAcrossRelaunch` (physical Phone), using the normal project, scheme, signing, destination, and DerivedData options from `scripts/check.sh`.

For broader changes use the default check script as appropriate; paid microphone checks remain opt-in and require founder readiness. Reuse evidence when the relevant implementation is unchanged.

Closeout evidence (September 24, 2026): Mac `Test-Mac-2026.09.24_16-56-03--0400.xcresult` and physical iPhone `Test-Phone-2026.09.24_16-57-30--0400.xcresult`, one targeted UI test passed on each. Logs: `work/v0-closeout-mac.log`, `work/v0-closeout-phone.log`. The retained iPhone early-text screenshot was visually inspected: text is present beneath Speaker pending during replay. The first iPhone attempt was blocked by canceled device authentication before test execution; work paused until the founder unlocked/confirmed readiness, then the same test passed. No paid calls or production app-code changes occurred in closeout; prior hardware and transport evidence remains applicable.
