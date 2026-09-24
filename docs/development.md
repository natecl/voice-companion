# Development and foundation QA

## Setup and commands

Validated September 24, 2026 with Xcode 27.0, Swift 6.4, and XcodeGen 2.46.0. Install Xcode and XcodeGen, select Xcode as the developer directory, and install an iPhone simulator runtime. The project specification is the source for generated Xcode configuration; regenerate after changing it. XcodeGen keeps the two targets and shared UI-test source easy to review; there are no third-party app runtime dependencies.

```sh
scripts/check.sh mac
SIMULATOR_ID=<simulator-identifier> scripts/check.sh simulator
DEVICE_ID=<paired-device-identifier> DEVELOPMENT_TEAM=<your-team> scripts/check.sh device
```

Commands default to `test`; append `build` for build-only. Use `xcrun simctl list devices` and `xcrun devicectl list devices` to discover destinations. Signing requires an authorized development identity and provisioning access. Never commit credentials. No microphone permission is needed by this foundation.

Generated products live in Xcode's standard DerivedData location. Building products under the Documents workspace produced resource-fork metadata that codesign rejected; moving generated products resolved the packaging error without weakening signing.

Minimum deployment settings are provisionally iOS 18 and macOS 15; QA below covers only the actual listed systems. Older-version support is not yet demonstrated.

## Foundation acceptance and observed results

The bounded checkpoint is a shared SwiftUI app shell with native Mac and iPhone builds, accessible controls, real UI navigation, screenshots, and structured navigation logs. It does not record, transcribe, or save sessions.

UI test `FoundationUITests/testSessionNavigation` launches the real app, presses New session, checks the transcript placeholder, captures a screenshot, then returns to sessions and verifies the control is present. No provider or microphone input is used or claimed.

| Environment | Observed result |
| --- | --- |
| Mac, macOS 26.6.2 | Build and UI test passed: 1 test, 0 failures; screenshot visually inspected |
| Physical iPhone 16 Pro, iOS 26.5.2 | Signed build, install, launch, and UI test passed: 1 test, 0 failures; screenshot visually inspected |
| iPhone 17 Pro Simulator, iOS 26.5 | Build and UI test passed: 1 test, 0 failures |

Mac logs retrieved with `log show --info` contained `foundation_ready`, `session_opened`, and `session_closed` under subsystem `ai.voicecompanion.app`. No conversation data is logged.

Local evidence (ignored, not committed): `work/phone-foundation.xcresult`, `work/phone-test.log`, `work/mac-test.log`, `work/simulator-test.log`, and exported screenshots in `work/phone-screenshots` and `work/mac-screenshots`. Mac and simulator result bundles reside in their DerivedData `Logs/Test` directories. Screenshots can contain desktop surroundings and remain local. Reproduce evidence using the commands above; Xcode prints the result-bundle path.

The physical-device run used the same xcodebuild options directly before the wrapper was added. Mac and simulator runs used the wrapper. The source snapshot is identified in the checkpoint PR. Review covered shared source, generated targets, scripts, ignored artifacts, and the scope of QA claims.

## Inspect results

Apple documents command-line testing and result bundles in [Running tests and interpreting results](https://developer.apple.com/documentation/xcode/running-tests-and-interpreting-results). Use `xcrun xcresulttool export attachments --path <result-bundle> --output-path <local-directory>` to extract retained screenshots.

## Remaining work

Provider validation, simulated transcription, microphone capture, transcript persistence, interruptions, and quality evaluation remain unimplemented. This checkpoint is evidence of the native engineering workflow, not completion of V0 or validation of transcription accuracy.

## Replay checkpoint — September 24, 2026

The app now replays the captured synthetic provider events with no API calls. Shared transcript reduction replaces overlapping interim/chunk text, and the stitched final result contains one segment with 30 words. Speaker labels preserve the provider's one known boundary attribution error. Sessions are saved atomically after updates; stopping preserves an incomplete session; completed and incomplete sessions can be reopened and deleted. Replay is clearly labeled and does not activate the microphone.

Verification: four core checks pass (overlapping revisions, recorded response reduction, persistence/delete, corrupt-file error). Mac UI checks pass for complete replay/relaunch/delete and early stop/reopen; physical iPhone 16 Pro checks pass for both flows. Screenshots from both platforms were inspected. The Mac replay check was rerun in isolation after correcting an accessibility element-type assumption; unchanged core/stop evidence was retained. No paid provider calls were made for this checkpoint.

Local evidence: work/replay-core.log, work/replay-focused.log, work/replay-test.log, work/replay-phone.log, and exported screenshots in work/replay-mac-screenshots and work/replay-phone-screenshots. The earlier full Mac log contains the diagnosed UI-test failure; the focused log records its passing correction. Result bundles are in the respective DerivedData Logs/Test directories.

UI tests use a separate VoiceCompanion-QA storage directory via --ui-testing; normal sessions use VoiceCompanion in Application Support. Minimum-OS coverage, microphone capture, provider relay, realistic quality evaluation, and cross-device sync remain outside this checkpoint.

## Mac live development checkpoint — September 24, 2026

Implemented microphone permission, AVAudioEngine capture, PCM16/16 kHz conversion, bounded streaming through an authenticated loopback relay, live transcript updates, stop/finalization, and saved-session reopening. Raw audio is not retained. See Backend/README.md for configuration and limits. iPhone live capture is not enabled yet.

Real behavioral QA: started recording in the signed Mac app, played the synthetic single-voice fixture through the computer's audio output, observed its complete expected text through the microphone/provider path with Speaker 1, stopped to Saved, quit/relaunched, and reopened the same text. The successful session sent 24.09775 seconds of audio with estimated audio cost $0.00133876. A preceding attempt crashed before sending audio; provider connection overhead, if billed, is not included in the estimate. Prior probes plus this successful run total about $0.00243 estimated audio cost, not a verified bill.

The crash was a MainActor assertion in the audio tap callback. Constructing the callback outside MainActor fixed it. A five-second local capture then returned 159,986 PCM bytes and stopped without uploading. An opt-in hardware UI regression check now exercises that actual callback and requires nonzero PCM output, clean completion, and no upload. It passed.

Default Mac regression: four core tests and two replay UI tests passed with the live changes. Relay authentication/forwarding/quota test passed entirely locally. Evidence: work/live-regression.log, work/microphone-regression.log, work/relay-usage.jsonl, local Xcode result bundles, and UI inspection in the working task. The provider key and client token are excluded from commits.

Hardware regression command (permission must already be granted): run xcodebuild with scheme Mac, your development signing team/identity, and `-only-testing:MacUITests/MicrophoneUITests test`. The default check script excludes this opt-in microphone test. Launching with `--microphone-check` also runs a five-second local-only diagnostic.

Known limits: this is a bounded Mac development integration; natural multi-speaker quality, hardware route changes, full interruption behavior, longer sessions, iPhone transport, and production relay deployment are not yet verified. It does not complete V0.


## iPhone live development checkpoint — September 24, 2026

Bounded acceptance: physical iPhone microphone -> encrypted development relay -> real provider -> speaker-labeled transcript -> Stop/Saved -> reopen, including after app relaunch. This checkpoint establishes the successful short-recording path; it does not complete phase 5 interruption/failure acceptance or all of V0.

The iPhone reuses the shared capture, transcription, and persistence flow. Development configuration is copied over the paired-device connection. The relay adds optional LAN TLS with a seven-day certificate, random client authorization, and the existing shared usage limits. Native trust checks preserve expiry and hostname validation. No provider credential enters the app; release builds cannot load this development configuration. See Backend/README.md for reproduction.

Behavioral evidence on iPhone 16 Pro / iOS 26.5.2:

- Five-second local microphone hardware test passed with nonzero PCM and no upload: work/phone-microphone-check.log.
- Signed TLS-enabled build passed: work/phone-lan-build.log. The phone's `/health` diagnostic displayed connection verified with no provider call. Local TLS validation accepted the development anchor and rejected a wrong hostname.
- Founder tapped Start recording, spoke the supplied synthetic appointment sentence, and stopped. The completed relay ledger reports 10.79875 audio seconds, 13.713 seconds connection duration, estimated audio cost $0.00059993 (not verified billing). The UI showed the complete expected 18-word text with Speaker 1 across two segments; the agent visually inspected it via iPhone Mirroring.
- Agent independently ran SavedRecordingUITests on the physical device: open the existing recording, verify Saved and expected text, return to sessions/reopen, terminate/relaunch/reopen, and verify the same text again. One test passed, zero failures. Three retained screenshots show the expected transcript; the final screenshot was visually inspected. No recording, provider calls, or data deletion occurred in this test.
- Local relay real-socket authentication/forwarding/cleanup/quota regression passed using a fake upstream; no external requests. The signed Mac build also passed after extracting the shared relay configuration (work/iphone-checkpoint-mac-build.log).

Saved-recording evidence: work/phone-saved-recording.log and work/phone-saved-screenshots; device result bundle Test-Phone-2026.09.24_04-01-45--0400.xcresult in DerivedData Logs/Test. Screenshots stay local. The opt-in `-only-testing:PhoneUITests/SavedRecordingUITests` test requires this consented fixture in normal app storage and is excluded from default checks. Default replay tests still use isolated QA storage. Microphone hardware checks are also opt-in on both platforms.

Computer-use observation worked through iPhone Mirroring, but coordinate clicks repeatedly failed with `noWindowsAvailable`. A native Xcode UI test supplied independent interaction/relaunch evidence instead; manual user reports were not substituted for that verification. The check script also fixes Bash 3.2 empty-array expansion for build-only runs.

Remaining acceptance: interruption/background behavior, permission denial and other failure paths, natural multi-speaker accuracy, longer recordings/resource usage, supported minimum OS coverage, production authentication/retention review. The development app still auto-stops at 55 seconds. No claim of full V0 completion or production readiness.

## Recording lifecycle checkpoint — September 24, 2026

Recording now persists an optional end reason, preserves received text on failure, and identifies interrupted sessions after reopen. Backgrounding saves the incomplete session before cancelling capture/network work, without waiting for final provider output while suspended. Explicit Stop still finalizes normally; auto-stop reports Finishing. Startup can be cancelled before a microphone connection is created. The adapter rejects premature provider completion and preserves audio-stream errors while cleaning up the microphone and socket.

Audio capture observes engine configuration changes, iOS audio interruption beginnings, route changes (excluding its own category changes), and lost media services. Callbacks hand off to MainActor before stopping capture; notification observers are removed during cleanup. Startup failures deactivate the session too. This follows Apple's [engine-change notification guidance](https://developer.apple.com/documentation/foundation/nsnotification/name-swift.struct/avaudioengineconfigurationchange) and [audio interruption guidance](https://developer.apple.com/documentation/avfaudio/handling-audio-interruptions).

Verification and provenance:

- Five controlled-connection tests use the real session controller, reducer, and temporary disk store: background preservation before cancellation/reload, network-error preservation, explicit Stop completion, cancellation during permission preparation, and denied permission without connecting. Together with the existing four core tests, nine pass. These are local injected failure tests, not claims of physical permission denial or network outage QA.
- Physical iPhone 16 Pro: local replay verified that bringing SpringBoard forward actually backgrounds the app and stops replay. A real microphone/provider run then verified background cancellation, incomplete saved status, the stored reason, and relaunch/reopen. The run sent 1.1903125 audio seconds ($0.00006613 estimated). The relay closed after 4.084 seconds with ConnectionError, expected for an intentionally cancelled session. This short run had no transcript content; preservation of received text is covered separately by the controlled-connection/disk checks and prior successful microphone persistence QA.
- Physical iPhone audio interruption: a local-only microphone diagnostic was running when the founder held the side button to invoke Siri and returned to the app. The agent captured and inspected work/manual-interruption-result.png: the stream ended with the audio-interruption error. The diagnostic calls the same MicrophoneCapture as real recording and sends no audio to a provider. Reproduce with `--microphone-interruption-check` (120-second local cap), invoke Siri physically, and return to inspect. The generic “check failed” prefix reflects the stream throwing the expected interruption; it is not a failed acceptance result.
- Xcode's simulated Home-button command left the app foregrounded. A screenshot and application-state check established this; switching to SpringBoard activation reproduced the real transition. The earlier paid attempt sent 11.1900625 seconds and was closed when the test terminated the app ($0.00062167 estimated). Subsequent diagnosis used free replay. Automated Siri text activation also did not interrupt capture, so its nonworking test was replaced by the documented manual physical trigger, not marked passed. No repeated paid Siri test occurred.
- Local evidence: work/lifecycle-core-fixed.log, work/lifecycle-background-springboard.log, work/lifecycle-background-live.log, work/background-live-shots, work/manual-interruption-result.png. The earlier failed logs are retained locally with the diagnosed causes. The device background result bundle is Test-Phone-2026.09.24_04-13-55--0400.xcresult. Paid audio for this checkpoint totals 12.380375 seconds, approximately $0.00068780, not verified billing.

A RecordingConnection boundary and injected preparation/store make these failures testable without paid inference. Physical recording interruption tests are opt-in (`PhoneUITests/RecordingInterruptionUITests`); default tests do not make paid calls. The local replay method in that class is individually selectable. Tests leave their incomplete sessions in isolated QA storage, not the founder's normal sessions.

Remaining V0 acceptance includes actual network outage/provider failure and timeout coverage at the transport boundary, physical permission denial, input-route changes, longer sessions, and representative multi-speaker quality/latency. A manual Siri event verifies one interruption type, not every phone call or accessory behavior. No automatic resume is implemented.

Final regressions: nine core tests plus two replay UI tests passed on Mac (work/lifecycle-mac-regression.log), and both replay UI tests passed on the physical iPhone (work/lifecycle-phone-regression.log). Review moved adapter cleanup to cover configuration/startup throws as well as active connections; final signed Mac and iPhone builds verified that cleanup adjustment. Existing active-connection evidence remains applicable because its cleanup path is unchanged.

## Transport failure checkpoint — September 24, 2026

The production WebSocket adapter now has explicit readiness/finalization timeout errors. A small AudioCapture boundary, configurable connection factory, and timeout values let the actual adapter run over local sockets without microphone access or a paid provider. Defaults remain unchanged: 10 seconds to readiness, 55-second recording cap, 12 seconds to finalization. Tests shorten these to 1 second / 2 seconds / 300 milliseconds. The existing controller still saves received text and failure reasons; this checkpoint exercises the transport underneath it rather than replacing it with a fake connection.

Eleven local scenarios: abrupt network socket loss, provider error event, rejected HTTP authorization, readiness timeout, Stop before readiness, finalization timeout, unexpected premature completion, audio-stream failure, active cancellation, normal Stop, and auto-stop. Each runs real URLSession WebSocket traffic against a loopback-only Python server, through the actual session controller and atomic disk store. Assertions verify capture cleanup, incomplete/completed state, text preservation where text was sent, specific timeout/audio error reasons, server-observed socket closure, audio.done for graceful Stop, and zero audio before readiness or after rejected authorization. The synthetic audio source substitutes only for hardware capture; prior physical-device capture evidence remains separate.

The first run exposed a test setup issue: Xcode selected a Python missing websockets. The check script now explicitly forwards the chosen Python path into the test runner; direct-command instructions are in Backend/README.md. It is a required local dependency, not a skipped test. The corrected initial nine scenarios passed in 4.8 seconds; the final eleven are included in the complete Mac regression run.

Evidence: work/transport-failure-configured.log, work/transport-final-regression.log, work/transport-phone-build.log, and corresponding Xcode result bundles. The shared iPhone target builds with the injected boundaries and timeout errors. No new physical microphone/paid runs were needed: audio hardware behavior and UI rendering are unchanged. These tests prove controlled transport-failure behavior; they do not establish every real carrier/Wi-Fi, accessory, or provider-service condition.

No provider calls or transcription charges occurred in this checkpoint. Manual QA readiness is now explicit in both AGENTS.md and the canonical engineering principles: explain the steps and wait for the founder to say they are ready before starting any test that needs them.

Final result: all 20 core tests (11 transport, five controller lifecycle, four transcript/store) and both Mac replay UI tests passed in work/transport-final-regression.log; signed iPhone build passed in work/transport-phone-build.log. Review confirmed unchanged production timeout limits, loopback-only fixture networking, cleanup assertions, no fixture credentials or external provider access, and explicit rather than silently skipped dependency failures.

## Recording feedback and deletion protection (September 24, 2026)

The development build shows the 55-second microphone recording limit before starting and during capture. Elapsed time begins when capture becomes ready, excludes connection setup, and freezes when capture stops or fails. New saved recordings retain that duration; older sessions without duration metadata do not display an invented value. Automatic limit stops retain an explanation when reopened. A normal limit stop still finalizes the transcript; a finalization failure remains visibly incomplete with its error.

Deleting a saved session now requires confirmation. Cancel leaves it available across app relaunch; confirming deletes it through the existing store.

Targeted QA uses no microphone or paid provider requests:

- `CoreTests/TransportFailureTests` exercises actual local WebSockets, including automatic stop, `audio.done`, successful finalization, and persisted stop reason with a shortened two-second limit.
- `CoreTests/RecordingLifecycleTests` checks explicit stop, frozen elapsed time, errors, and interruptions. `TranscriptTests` checks older saved JSON without the new optional fields.
- `FoundationUITests` runs the actual Mac and physical-iPhone UI: ticking elapsed time, automatic-stop explanation after relaunch, cancellation preserving a transcript across relaunch, confirmed deletion, and incomplete replay persistence.
- The timer UI test uses `--ui-testing --recording-ui-fixture` in Debug builds only, a six-second simulated connection, and separate QA storage. It neither captures audio nor opens a network connection. Its transcript explicitly identifies simulated input. The normal development limit remains 55 seconds.

Local evidence is under ignored `work/recording-feedback-*.log` and the Xcode test result attachments (recording timer, reopened automatic-stop explanation, and deletion confirmation). This verifies presentation and stop metadata; earlier real microphone/provider evidence remains the integration evidence. This checkpoint does not increase recording limits or establish long-session quality.


## Five-minute checkpoint (September 24, 2026)

The current development limit is 300 seconds, superseding the 55-second cap described in earlier checkpoint records above. Stop remains visible below the scrolling transcript. Separate Mac and physical-iPhone five-minute microphone playback captures, automatic finalization, persistence, and independent relaunch verification passed. See [five-minute checkpoint evidence](five-minute-checkpoint.md) for exact durations, local/real QA, resource observations, cost controls, and provider timestamp limitations. This does not complete all V0 quality acceptance.
