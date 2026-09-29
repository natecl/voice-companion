# Proactive message readability — September 28, 2026

Verified local native rendering only; not deployed. The v3 candidate prompt is prepared but **not selected or live-model validated**. Runtime still uses v2.

Founder feedback: the Cedar reminder was useful and naturally timed, but should arrive as absorbable pieces without losing details such as “before adding features.” One idea per bubble, often a sentence or two and roughly 2–4 mobile lines, is a design hypothesis rather than a hard size limit. Keep regular body text, necessary qualifiers and all useful content. No new word or bubble-count cutoff.

Explicit blank-line paragraphs in a proactive answer render as closely spaced ordinary Agent bubbles. Normal replies remain unchanged. Storage, one turn ID, cooldown and new-message behavior remain unchanged. Each bubble supports native Copy. No punctuation guessing or artificial delivery delay.

## Verification

- `xcodegen generate` passed.
- `xcodebuild -project VoiceCompanion.xcodeproj -scheme Mac -destination platform=macOS -derivedDataPath /tmp/proactive-core-build CODE_SIGN_IDENTITY=- -only-testing:CoreTests/CompanionMessageTextTests test` passed, including paragraph order, qualifiers, abbreviation preservation, normal replies and four-bubble content retention.
- Start `python3 Backend/companion_fixture.py /tmp/proactive-short-ui --ui --proactive`; supply generated config as `TEST_RUNNER_VOICE_MEMORY_UI_CONFIG` to `xcodebuild -project VoiceCompanion.xcodeproj -scheme Phone -destination 'platform=iOS Simulator,id=C804A6C5-EC44-4271-8E83-A224EB2D9234' -derivedDataPath /tmp/proactive-phone-build CODE_SIGNING_ALLOWED=NO -only-testing:PhoneUITests/ProactiveUITests test`.
- Actual native simulator UI test passed: synthetic capture over local socket, two paragraphs delivered as two ordered bubbles, draft retained, Quiet does not stop capture, Stop and relaunch preserve both paragraphs. No paid provider call or physical microphone claim. An initial incorrect `PhoneTests` target was corrected to `PhoneUITests` before successful execution.
- Screenshot inspected: readable two-line bubbles, close six-point grouping, no overlap with composer/recording controls. The later removal of the provisional three-bubble cap was covered by the core test; the screenshot’s two-bubble path is unchanged.

![Native grouped proactive contribution](grouped-bubbles.png)

## Remaining gates

Candidate wording needs bounded real Luna QA for completeness, appropriate silence and natural boundaries, followed by separate deployment/native installation. Simulator output proves rendering, not generated wording quality, optimal engagement, physical feel or accessibility across every Dynamic Type setting. No new provider allowance has been consumed.
