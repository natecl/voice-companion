# Native experience UI checkpoint — September 27, 2026

The approved Home mockup is the visual baseline: white canvas, neutral surfaces, native sans typography, separate Home/Agent navigation, plain document icons, and a shared bottom composer beside deliberate capture. The founder authorized layout refinements according to the current user's goal, spatial hierarchy, touch, feedback, and control. The exact product one-liner and existing companion scope remain unchanged.

## Delivered behavior

- Home groups saved recordings by day, shows available generated titles and transcript previews, and searches local transcript text without a model call. Search does not yet index generated titles.
- Home and Agent share the same draft, attachment, dictation controls, and persistent conversation. Sending from Home opens Agent. Mic dictates a private editable message; the paperclip opens attachment options and a recording picker, while the separate black plus starts meeting capture.
- The capture bar shows elapsed time and state, opens a live transcript sheet, and has Stop without Pause. Closing the sheet keeps capture running. Capture completion opens saved notes automatically.
- Saved notes retain the Notes/Transcript switch, original supporting passages, and Ask Agent attachment behavior. Deletion is in the recording menu, with confirmation.
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

Initial fidelity simulator run: iPhone 17 Pro simulator, iOS 26.5, September 27. All four scenarios passed (21.978s, 18.359s, 20.564s, 20.978s). The final Mac build passed. Result bundles are preserved by the QA script; this run is under `/tmp/VoiceCompanion-ExperienceResults/20260927-160211/`.

Rendered screenshots were inspected: [Home](qa/native-experience/home.png), [Agent](qa/native-experience/agent.png), [Notes](qa/native-experience/notes.png), [Attachments](qa/native-experience/attachments.png), [Account](qa/native-experience/account.png), [Sign-up preview](qa/native-experience/signup.png), and [Pricing preview](qa/native-experience/pricing.png). These contain only synthetic fixture content.

The fidelity revision removes the separate material footer, puts the composer and capture control on the continuous white canvas, matches the mockup's outlined icon silhouettes, and refines list spacing, duration metadata, neutral contrast, composer proportions and shadows. Shared styling extends to account and preview screens. A DEBUG-only isolated gallery seeds four recordings for reproducible visual comparison; it cannot seed the production store.

Acceptance scenarios:

1. Capture while asking, inspect source/transcript, return, stop into saved notes, attach/remove the recording, relaunch the persistent conversation.
2. Preserve a draft across Home/Agent, start capture, inspect/dismiss the live sheet without stopping, stop into notes, search matching/empty results, and dictate an editable message.
3. Generate/read saved notes, reopen a supporting passage, relaunch, and delete through confirmation.
4. Render four dated recordings, inspect generated notes and the shared screen gallery, attach a recording through the composer attachment control, and remove it.

During iteration, UI execution caught duplicate accessible Stop controls behind a sheet and an alert attached to the wrong presentation layer. Those were fixed. The QA runner now isolates owners to avoid selecting an older offscreen citation from a previous run.

## Composer optical refinement

Follow-up reference comparison corrected oversized mic/send glyphs, the send control's excessive right inset, and the capture plus's glyph size and vertical alignment. The inner attachment control retains a 44-point target. The actual Home render was compared with the supplied reference; Home and Agent screenshots above are updated. This adjusts visual geometry only, preserving capture, dictation and attachment behavior.

Both affected simulator scenarios passed on September 27: gallery/attachment picker and shared draft/search/live-sheet/dictation. Results: `/tmp/VoiceCompanion-ExperienceResults/20260927-161534/`. Mac compilation also passed. Earlier four-scenario evidence remains for the preceding revision; this focused follow-up does not claim renewed physical-device QA.

## Remaining delivery gates

Physical-iPhone recording, interruptions, touch comfort, accessibility text sizes, and battery/performance have not been validated by this UI checkpoint. Mac compiles, but the Mac XCTest runner timed out while enabling automation, before tests began; no Mac behavioral pass is claimed. Existing microphone/provider verification is not new evidence for this layout.

Before founder-assisted device QA, explain the exact steps and wait for explicit readiness. Do not merge this as completed iPhone delivery or present the preview account screens as working services.

## Shared composer controls

Home and Agent render the same composer: paperclip opens attachments, empty/whitespace-only drafts show mic, and text replaces mic with send. Active dictation shows Stop until the editable text is ready; busy responses retain Cancel. Clearing a draft restores mic. The external plus still starts capture.

Three affected simulator scenarios passed on September 27 (gallery/attachments, shared draft/search/dictation, capture/chat/navigation); Mac build passed. Result bundles: `/tmp/VoiceCompanion-ExperienceResults/20260927-162356/`. Native Home and typed Agent screenshots were inspected, including keyboard placement. [Typed composer](qa/native-experience/composer-send.png). No paid calls or physical-device validation were performed.

Upright paperclip follow-up: rotated the shared attachment glyph vertically at founder request. Gallery/attachment simulator check passed; native Home render inspected. Updated Home and Agent screenshots show the vertical glyph; the earlier typed-composer screenshot predates this orientation-only change. Results: `/tmp/VoiceCompanion-ExperienceResults/20260927-163546/`.


## Eight-screen reference pass — September 27

The founder supplied eight final references for Home, Agent during capture, saved notes, live transcript, sign-up, pricing, account and search. The native implementation now shares the reference's white surfaces, pale borders, soft control shadows and typography hierarchy. Agent has a contextual pill header, neutral user bubble and serif author heading; saved notes and account use full pages, while live transcript remains a sheet. Search has a dedicated search capsule, result count and matching-text highlights. Sign-up keeps Google above Apple; pricing and account use grouped cards. The upright paperclip and mic-to-send composer behavior supersede the older controls pictured in the references. Live capture retains Stop only and opens from the recording bar.

Screenshot iteration also caught and fixed a generated-note title that could remain stale after the body was ready, oversized back/close icons, short conversations anchored too low, and a pricing footer that did not fit the screen.

Final verification: all four isolated simulator scenarios passed on iPhone 17 Pro / iOS 26.5. Result bundles: `/tmp/VoiceCompanion-ExperienceResults/20260927-170751/`. Final Mac compilation and `git diff --check` passed. No paid provider runs or physical-device validation were performed. The delivery gates above remain open.

[Open the screenshot gallery](qa/native-experience/index.html). All images are actual native simulator captures from the final run, including the typed composer with its upright paperclip:

- [Home](qa/native-experience/home.png), [Agent empty](qa/native-experience/agent.png), [Agent during capture](qa/native-experience/agent-capture.png), [typed composer](qa/native-experience/composer-send.png)
- [Saved notes](qa/native-experience/notes.png), [live transcript](qa/native-experience/live-transcript.png), [search](qa/native-experience/search.png), [attachments](qa/native-experience/attachments.png)
- [Account](qa/native-experience/account.png), [sign-up preview](qa/native-experience/signup.png), [pricing preview](qa/native-experience/pricing.png)

These are close native adaptations, not pixel-identical reproductions. The simulator's status bar and iOS sheet chrome differ; content length and source links affect note height. The Agent capture test intentionally includes source-debug output and a partial-context retrieval notice; the live transcript uses synthetic stress text. Account, authentication and billing have explicit unconnected-service states instead of simulated signed-in or paid behavior. No physical-phone acceptance or Mac UI behavioral pass is implied.


## Agent-first navigation and inline composer — September 27

Agent is now the first/default root tab, with Notes second for the recording library. Both tabs remain visible on both root screens. Latest-answer sharing and refresh are available by long-pressing Agent. The recording bar now says View beside the separate Stop button. The shared composer starts on one row: upright paperclip, inline text, mic/send. Longer drafts wrap up to five visible lines and then scroll; clearing restores the compact mic state. The external capture plus remains separate.

All four isolated simulator flows passed again (21.821s, 19.965s, 28.162s, 20.105s), including an explicit automatic-wrapping height check, screenshot, clearing and shared-draft check. Results: `/tmp/VoiceCompanion-ExperienceResults/20260927-200059/`. Mac compilation passed. Screenshots in the gallery are refreshed; `home.png` is retained as the filename for the renamed Notes screen. [Multiline composer](qa/native-experience/composer-multiline.png). This supersedes the prior two-tier composer and contextual Agent-only header. No paid calls, device installation or new physical-device acceptance.


Capture plus refinement: increased the symbol frame from 30 to 36 points while preserving the 58-point capture target. Gallery/attachment simulator flow passed on September 27; actual Notes and Agent renders inspected and updated. Results: `/tmp/VoiceCompanion-ExperienceResults/20260927-204416/`. Founder authorized UI deployment; device discovery reports the physical iPhone unavailable, so installation is pending device connection. No deployment or new physical acceptance is claimed.


## Authorized internal iPhone installation — September 28

After the founder connected/unlocked the phone and confirmed readiness for installation, the signed Phone build of `44bb9aa` succeeded with the existing development identity. `devicectl` installed the app as an in-place update on the paired physical iPhone 16 Pro and successfully launched `ai.voicecompanion.phone --enable-companion-ui`, persisting activation of the new interface. No uninstall, backend deployment, microphone capture or paid provider check was performed. Build/install/launch receipts: `/tmp/ui-device-build.log`, `/tmp/ui-device-install.json`, `/tmp/ui-device-launch.json`.

This supersedes the prior unavailable-device installation blocker. It establishes installation and launch, not physical behavioral acceptance. Full device flow/interruption/touch checks and Mac UI acceptance remain pending; PR 104 remains draft.
