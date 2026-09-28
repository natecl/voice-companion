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


## Interaction polish and secondary Notes — September 28

Founder revision: Agent remains the main destination; Notes now opens with a back circle, Notes title capsule, and search/options capsule, retaining the recording library. This supersedes the earlier both-tabs-on-both-pages layout. Responses no longer repeat Ellis. Connection, partial-context and dictation notices use readable rounded cards; uncertain saved state remains explicit. The capture button uses a charcoal circle, rounded bold plus and soft shadow based on the supplied Wispr Flow reference.

Shared controls have light iPhone tap haptics and a distinct notification when recording state changes. Typing, streaming tokens and passive updates do not trigger tap haptics. Native press feedback (180 ms), mic/send replacement (200 ms), and navigation (180–240 ms) are implementation hypotheses, not research-validated optimum values. Reduce Motion disables travel/scale animation. Existing Libraries.dev ThinkingOrbsKit remains limited to longer waits; no web effects or new dependency were added. System haptic settings and recording-session suppression remain respected. Simulator QA cannot verify tactile feel.

Verification: all four isolated native UI scenarios passed at `/tmp/VoiceCompanion-ExperienceResults/20260928-001133/`. After the notice-copy and screenshot-settling refinements, the three affected gallery, capture/chat and shared-draft/search/dictation scenarios passed again at `/tmp/VoiceCompanion-ExperienceResults/20260928-001408/` (27.014 s, 20.869 s, 29.516 s). Assertions cover absent Ellis labels, notice presentation and multiline composer behavior. Final Mac and signed iPhone builds passed; `git diff --check` passed. The refreshed gallery contains settled actual simulator screenshots. No paid provider calls or new physical recording QA.

The requested Luna Max last30days research covered August 29–September 28 using free/public sources; recent community evidence was sparse and Reddit ended in HTTP 429. Apple supports visible custom-button press states, at least 44-point hit targets, short causally clear haptics and reduced-motion handling. These support the implementation direction but do not establish specific timing or haptic-strength values. Sources: [Buttons](https://developer.apple.com/design/human-interface-guidelines/buttons/), [Haptics](https://developer.apple.com/design/human-interface-guidelines/playing-haptics), [Reduce Motion](https://developer.apple.com/documentation/swiftui/environmentvalues/accessibilityreducemotion). Physical touch comfort, repeated-tap fatigue and accessibility acceptance remain open.

Installation receipt: the signed UI source checkpoint `7a98981` was installed in place and launched successfully on the paired iPhone 16 Pro with companion UI activation. Receipts: `/tmp/polish-device-build.log`, `/tmp/polish-device-install.json`, `/tmp/polish-device-launch.json`. This preserves app data and does not claim microphone, provider or tactile acceptance.


## Dictation composer and dismissible notices — September 28

Active dictation replaces the shared composer with trash, an elapsed timer, PCM-driven waveform and Send. It finalizes before sending the combined typed/dictated draft. Trash cancels only the new dictated segment. The attachment menu offers Dictate message when a typed draft already occupies the trailing send slot. Natural recognition completion, timeout and interruption retain the established review-before-send behavior. The waveform reads the same PCM frames as recognition, at a bounded UI sampling rate, without another microphone consumer; timer and meter stop on completion/cancellation. No generated decorative voice activity or new dependency. Libraries.dev Voice guidance was consulted; its React glow was not imported into this native monochrome interface.

Notice cards now have a top-right accessible dismiss button; dismissing presentation does not clear drafts or change capture. Profile/search circles have a 1.5-point pale-gray outline.

Verification: 15 focused ComposerDictation/SharedMicrophone unit tests passed, covering RMS silence/amplitude, meter cleanup, finalization/send-once, trash, permission/failure recovery and private-dictation audio isolation. Mac build passed with the tests. Two simulator flows passed at `/tmp/VoiceCompanion-ExperienceResults/20260928-004253/`, including trash-preserves-draft and send-appends-final-words. A follow-up capture flow with explicit notice-dismissal assertion passed at `/tmp/VoiceCompanion-ExperienceResults/20260928-004419/`. Signed iPhone build and diff checks passed. [Actual simulator capture](qa/native-experience/dictation.png) uses a fixed synthetic audio level, so its bars are uniformly tall; production bars follow PCM amplitude. No paid calls or physical microphone/haptic acceptance in this checkpoint.

Signed source checkpoint `0d53122` was installed in place and launched on the paired iPhone. Receipts: `/tmp/dictation-wave-device.log`, `/tmp/dictation-wave-install.json`, `/tmp/dictation-wave-launch.json`. No recording was initiated; device behavior acceptance remains pending.

Dictation arrow correction: replaced the visible Send text with the exact shared filled up-arrow control used for typed messages. Finalization behavior is unchanged. The affected simulator flow passed (38.385 s), screenshot inspected/refreshed, signed build passed. Evidence: `/tmp/VoiceCompanion-ExperienceResults/20260928-004753/` and `/tmp/dictation-arrow-device.log`.


## Paperclip menu and refresh follow-up

The menu now offers Attach note, Use past memory and Refresh conversation. Dictate message and Clear draft are removed at founder request. The attachment sheet explains the context being attached, uses consistent note naming, and shows an add/selected indicator. Dictation remains on the empty composer's microphone.

Refresh previously erased the visible history before waiting for the network. It now retains the page while loading, preserves the draft, and reports Refreshing conversation / Conversation is up to date. A failed revalidation still clears unvalidated history and presents the existing error card. The busy control correctly identifies Cancel refresh. Dismissed notice cards use a short fade/scale transition and animated layout collapse; Reduce Motion removes the transition.

Focused refresh-controller tests cover visible-history preservation, replacement/success feedback, and failure clearing while retaining the draft. Simulator QA initially exposed test assumptions tied to the removed Clear draft action and debug-only source controls; those test steps were corrected to use actual composer editing and completion state. These failures were not application refresh failures.

Final verification: two controller regressions passed; menu/refresh and gallery/attachment flows passed at `/tmp/VoiceCompanion-ExperienceResults/20260928-005534/`. The shorter Refresh chat label and dismissal update passed at `20260928-005732`; the subsequent incoming-bubble revision passed capture/chat/source/reopen plus dismissal at `20260928-005903`. Actual menu, attachment sheet and Agent bubble screenshots inspected. Final signed iPhone and Mac builds passed. No paid calls or physical behavioral acceptance.

Agent saved and streaming replies now use the latest supplied reference: content-sized left-aligned light-gray rounded bubbles, subtle border, 16-point horizontal padding and semibold body type. This supersedes the earlier unboxed replies. The Agent capture screenshot contains debug-only source markers from the synthetic fixture.

Source checkpoint `6ba4966` installed in place and launched successfully on the paired iPhone. Receipts: `/tmp/menu-bubbles-install.json`, `/tmp/menu-bubbles-launch.json`. No microphone or paid-provider run was initiated.

Agent typography/copy correction: regular body text replaces semibold in incoming bubbles. The persistent copy icon is removed; saved and streaming replies expose Copy through the bubble context menu. Targeted simulator capture/chat test passed at `/tmp/VoiceCompanion-ExperienceResults/20260928-010213/`, including long-press and Copy selection. Screenshot inspected/refreshed; signed iPhone build passed. No paid calls or new physical behavior claims.

Copy-preview fix: the context menu was attached after the full-width alignment frame, so iOS lifted the row including transparent padding. Context-menu attachment and the rounded preview shape now apply to the content-sized bubble before outer spacing/alignment, for saved and streaming replies. The actual long-press preview was captured and inspected without the extra rectangle; Copy and capture navigation passed at `/tmp/VoiceCompanion-ExperienceResults/20260928-010508/`. Signed iPhone build and diff checks passed. Screenshot: [Copy preview](qa/native-experience/copy-preview.png). No paid calls or new microphone validation.


### Note actions and preserved chat — September 28

Native Notes now uses a plain List with the existing row artwork, native swipe Delete (confirmation required), and long-press Share/Delete. Active capture cannot be deleted. Share uses the same transcript export as the detail screen. Both delete entry points use the existing local/outbox deletion path; the selected attachment is cleared without clearing chat. Backend ordinary source deletion keeps saved answers and follow-ups while removing unavailable citations, retiring their evidence context and preserving existing learned-memory rules. Source rewrite validation is unchanged. Already scrubbed historic answers cannot be reconstructed.

Simulator gallery/attachment flow passed at `/tmp/VoiceCompanion-ExperienceResults/20260928-011307/`: long-press menu, cancel preserves four notes, swipe/confirm removes the intended note, surviving attachment and navigation remain functional. Actual context menu and swipe screenshots inspected and saved. Initial run exposed inherited custom button style hiding native swipe action; `.automatic` resolves it. Second run exposed duplicate UIKit accessibility matches for the confirmation; `.firstMatch` resolves the test selection.

32 companion backend tests pass, including websocket history, deletion/reopen preservation and unavailable source rejection. Eleven retained-memory tests pass; the older exact-provider replay fails with `answer_unavailable` identically on unchanged HEAD and this branch (`/tmp/retention-baseline.log`), so is not claimed as passing. Signed Phone build passes (`/tmp/note-actions-device-final.log`); diff check passes. No paid calls. This combined client/backend revision is not deployed yet; the hosted service must receive the preservation change before the client deletion copy is shipped. Copy-preview source867bc17 was installed earlier, without a subsequent launch receipt.
