# Agent bubble trailing margin

September 29, 2026. Increase agent trailing inset from 32 to 64 points inside the existing 24-point page padding. Applies to welcome, saved/proactive and streaming replies. User bubbles, fonts, colors, copy behavior and model output are unchanged.

Verified on iPhone 17 Pro simulator (iOS 26.5), Phone/ProactiveUITests, using the local companion_fixture.py --ui --proactive service with synthetic capture and model output. The actual reply leaves at least 80 points to the screen edge; draft preservation, Quiet without stopping capture, and persisted reply after relaunch pass. Inspected agent.png: readable wrapping, intact rounded bubble, visible trailing whitespace. No paid calls or physical-device installation.

Reproduce: start a fresh local fixture directory; pass its config.json through TEST_RUNNER_VOICE_MEMORY_UI_CONFIG to xcodebuild Phone test with -only-testing:PhoneUITests/ProactiveUITests. Evidence: work/bubble-margin-live/native.xcresult (local). Initial run failed before the composer appeared because its fixture process had exited with the parent shell; keeping the fixture in a foreground tool session resolved setup. This is simulator layout acceptance, not physical-device acceptance.
