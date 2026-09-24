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
