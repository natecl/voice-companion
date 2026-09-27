# Native experience UI checkpoint — September 27, 2026

The approved Home mockup is the visual baseline: white canvas, neutral surfaces, native sans typography, separate Home/Agent navigation, plain document icons, and a shared bottom composer beside deliberate capture. The founder authorized layout refinements according to the current user's goal, spatial hierarchy, touch, feedback, and control. The exact product one-liner and existing companion scope remain unchanged.

## Delivered behavior

- Home groups saved recordings by day, shows available generated titles and transcript previews, and searches local transcript text without a model call. Search does not yet index generated titles.
- Home and Agent share the same draft, attachment, dictation controls, and persistent conversation. Sending from Home opens Agent. Mic dictates a private editable message; the separate plus starts meeting capture.
- The capture bar shows elapsed time and state, opens a live transcript sheet, and has Stop without Pause. Closing the sheet keeps capture running. Capture completion opens saved notes automatically.
- Saved notes retain the Notes/Transcript switch, original supporting passages, and Ask Agent attachment behavior. Deletion is in the recording menu, with confirmation on the sheet.
- Account exposes the existing memory preference and honest configuration/recording information. Sign-up (Google above Apple) and pricing layouts are explicitly design previews: OAuth, StoreKit, prices, legal URLs, and plan allowances are not implemented or invented.
- Libraries.dev ThinkingOrbsKit's native SwiftUI port is pinned and vendored with its MIT license. It appears after a two-second wait beside answer/notes status text, pauses when inactive, and respects Reduce Motion. No React runtime, paid Pro package, or external service was added.

The existing companion activation/rollout gate is preserved (`--enable-companion-ui`); this checkpoint does not silently switch legacy diagnostic builds or deploy a device update.

## Verification

Reproduce with a Python environment containing the repository backend dependencies:

```sh
python3 scripts/check-experience-ui.py --simulator <booted-iPhone-simulator-UUID>
xcodebuild -scheme Mac -destination 'platform=macOS' build CODE_SIGN_IDENTITY=-
```

The UI script creates a fresh local service and memory owner for each scenario. It exercises the real native screens, sockets, storage, and notes worker with synthetic capture/provider input. No microphone audio or paid provider calls are made.

Final simulator run: iPhone 17 Pro simulator, iOS 26.5, September 27. All three scenarios passed (20.242s, 18.484s, 20.979s). The final Mac build passed. Actual rendered screenshots were inspected: [Home](qa/native-experience/home.png), [Agent](qa/native-experience/agent.png), [Notes](qa/native-experience/notes.png). These contain only synthetic fixture content.

Acceptance scenarios:

1. Capture while asking, inspect source/transcript, return, stop into saved notes, attach/remove the recording, relaunch the persistent conversation.
2. Preserve a draft across Home/Agent, start capture, inspect/dismiss the live sheet without stopping, stop into notes, search matching/empty results, and dictate an editable message.
3. Generate/read saved notes, reopen a supporting passage, relaunch, and delete through the sheet confirmation.

During iteration, UI execution caught duplicate accessible Stop controls behind a sheet and an alert attached to the wrong presentation layer. Those were fixed. The QA runner now isolates owners to avoid selecting an older offscreen citation from a previous run.

## Remaining delivery gates

Physical-iPhone recording, interruptions, touch comfort, accessibility text sizes, and battery/performance have not been validated by this UI checkpoint. Mac compiles, but the Mac XCTest runner timed out while enabling automation, before tests began; no Mac behavioral pass is claimed. Existing microphone/provider verification is not new evidence for this layout.

Before founder-assisted device QA, explain the exact steps and wait for explicit readiness. Do not merge this as completed iPhone delivery or present the preview account screens as working services.
