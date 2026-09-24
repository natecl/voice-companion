# Reliability edge-case checkpoint

Status: verified September 24, 2026. Scope: permission recovery, empty transcripts, and safe stop when microphone input is lost.

## Mac microphone permission denied

On September 24, 2026, the founder disabled VoiceCompanion's microphone access in macOS settings. The opt-in `MicrophoneUITests/testDeniedPermissionShowsRecoveryWithoutCreatingSession` launched the actual Mac app and attempted Start twice. Both attempts displayed the microphone-access recovery instructions, left Start enabled, and showed no Stop control or additional saved session. The existing QA session file's SHA-256 remained unchanged across the successful run. Permission is checked before relay configuration or session creation.

Command: `xcodebuild -project VoiceCompanion.xcodeproj -scheme Mac -destination 'platform=macOS' -derivedDataPath /Users/n.chinlue/Library/Developer/Xcode/DerivedData/VoiceCompanion-mac DEVELOPMENT_TEAM=7HF6VDCZF7 'CODE_SIGN_IDENTITY=Apple Development' -allowProvisioningUpdates -only-testing:MacUITests/MicrophoneUITests/testDeniedPermissionShowsRecoveryWithoutCreatingSession test`.

Evidence: local `work/reliability-mac-permission.log` and `Test-Mac-2026.09.24_06-02-42--0400.xcresult`, including the retained UI screenshot. One initial test failed because its baseline count was queried before the window loaded; waiting for Start before taking the baseline corrected the test. No product change was needed for that failure. This check used no paid transcription calls. Restored permission was subsequently exercised by the USB input-disconnect check below.

## Physical iPhone microphone permission denied

The founder disabled microphone permission and confirmed readiness. On the physical iPhone 16 Pro, the same opt-in permission-denied test passed: two Start attempts showed recovery instructions, Start remained enabled, no Stop control appeared, and the saved-session count did not change. No audio capture or paid provider call was made. Evidence: `work/reliability-phone-permission.log` and `Test-Phone-2026.09.24_06-09-00--0400.xcresult`, including the retained screenshot. Run with scheme Phone, physical-device destination, device DerivedData, and `-only-testing:PhoneUITests/MicrophoneUITests/testDeniedPermissionShowsRecoveryWithoutCreatingSession`.

After the founder restored permission and confirmed readiness, `PhoneUITests/MicrophoneUITests/testAudioCallbackRunsAndStopsWithoutUpload` passed on the same physical iPhone. The actual audio callback produced nonzero PCM bytes and the five-second local diagnostic stopped automatically with its No upload status. Evidence: `work/reliability-phone-restored.log` and `Test-Phone-2026.09.24_06-10-17--0400.xcresult`. This establishes restored microphone access and bounded local capture, without another provider call.

## Mac physical USB input disconnect

The founder restored microphone permission and selected the USB EarPods microphone. Before launching the local diagnostic, `system_profiler SPAudioDataType` confirmed `EarPods Microphone` as the default input (USB, 44,100 Hz, one channel). Launched the signed Mac app with `--ui-testing --microphone-interruption-check`; accessibility inspection showed the local check running. After the founder spoke and unplugged the headset, inspection showed `Microphone check failed: Audio capture was interrupted or its input changed.` The app remained responsive. This demonstrates the real configuration-change path ending capture with the expected interruption error, rather than silently continuing on another input. The diagnostic does not retain byte counts on failure, so it does not independently prove the spoken audio's content or level.

During this check the founder also clicked the normal Start recording button; it displayed the missing-relay-configuration error. That separate action did not end the already-running local diagnostic or upload audio. The diagnostic UI left normal controls visible and did not make its automatic capture clear enough; the diagnostic UI was subsequently updated to hide those controls and explain automatic capture. The generic interruption error mentions saved text, but this local-only diagnostic created no transcript. No paid provider call was made for this hardware check. Actual transcript preservation is covered separately by the injected input-failure transport check, not claimed from this local capture.

## Physical iPhone AirPods input disconnect

The iPhone recording category now enables `.allowBluetoothHFP`, which makes paired Bluetooth headset microphones eligible inputs. This follows the installed Xcode 27 AVAudioSessionTypes.h contract and Apple's [allowBluetoothHFP documentation](https://developer.apple.com/documentation/avfaudio/avaudiosession/categoryoptions-swift.struct/allowbluetoothhfp). Eligibility alone does not prove the selected input: the local diagnostic now displays the actual iPhone input port name and type after capture starts. It also retains received byte count and peak on interruption, and hides normal recording controls throughout diagnostic mode. After the founder confirmed readiness, the actual app displayed an AirPods Pro input with port type `BluetoothHFP`. The founder spoke and placed both earbuds in the case, closing the lid. The diagnostic then displayed the expected interrupted/input-changed error with 678,378 PCM bytes received (about 21.2 seconds at mono 16 kHz, 16-bit) and stopped capture. The displayed peak was 32,768; this check proves audio flow and route-loss handling, not audio fidelity or transcription accuracy. No provider call or retained raw audio was involved. Screenshots: `work/airpods-input-check.png` and `work/airpods-disconnect-result.png` (local only; device name is personal). Normal recording controls were absent, and the diagnostic did not incorrectly claim that a transcript was saved.

## Empty transcript evidence

Mac checks passed (23 core/transport tests, one intentionally skipped 90-second check, and five UI tests) in `Test-Mac-2026.09.24_05-57-56--0400.xcresult`. Coverage includes an empty transcript's save/reopen behavior and local WebSocket handling of empty completion and injected input failure. Injected input failure is not proof of a physical headset disconnect.

The empty-session UI check also passed on the physical iPhone after the final app changes, including save, relaunch, reopen, and removal of the test session. Evidence: `work/reliability-phone-empty.log` and `Test-Phone-2026.09.24_06-14-10--0400.xcresult`. This used a simulated empty transcript with no microphone or provider call.

One eight-second digital-silence probe completed against the provider with no transcript words (11 empty partial events followed by completion). Local evidence: `work/silence-check/events.json` and `summary.json`. Estimated cost: $0.0004444, one call, no retries. Digital silence does not establish behavior for a quiet room with microphone noise.

## Review boundaries

The input-change transport test uses an injected capture error to verify saved text and connection cleanup. Physical device checks separately establish that actual input loss reaches this failure path. These checks do not establish AirPods transcription accuracy, seamless input switching, noisy-room hallucination rates, or general Bluetooth-device compatibility. Permission and transport evidence remains applicable after the diagnostic-only changes; the iPhone Bluetooth category change was exercised with the real AirPods. Both updated app builds passed. Paid usage for this checkpoint remains one eight-second digital-silence call, estimated $0.0004444.
