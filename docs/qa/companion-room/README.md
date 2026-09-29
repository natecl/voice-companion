# Companion room native candidate

September 29, 2026. Based on verified main `47eadb4`; independent of the pending background phase PRs. This is a native presentation checkpoint, not a backend/model or capture-provider change. The native build was subsequently installed internally on the founder’s phone; see the installation receipt below.

## Founder-approved direction

The reviewed prototype becomes the visual source of truth: lavender canvas, plum controls, companion at the top, two-line Notes entry on the left, Invite on the right. No root tab selector or home search control. Only the capture bar reports listening; preserve the current circular recording indicator, red beside “Listening”. The new design may replace navigation behavior, while note swipe/long-press Delete, Share and Copy remain.

Native implementation uses existing shared controllers and one persistent chat. Notes enters from the left and returns to the left; draft and capture state survive navigation. Existing card gestures and deletion confirmation are retained. Typography, continuous corners, shadows and press feedback follow the new surfaces. Reduce Motion suppresses page and press movement. Invite opens an honest unavailable-state sheet; no invites are sent, no contacts are accessed and no URL is invented.

The temporary companion image is extracted from the founder-reviewed prototype. Its debug rendering is for internal design evaluation only. Release displays a monogram. The reference image is still a bundled resource, so it must be replaced/removed before distribution; no final identity or licensing clearance is claimed. Existing missing distribution app-icon work remains open.

## Verification scope

Use the existing isolated native fixture runner (synthetic transcript and local socket/notes service, no paid provider or real microphone):

```
python3 scripts/check-experience-ui.py --simulator C804A6C5-EC44-4271-8E83-A224EB2D9234 --derived-data /tmp/CompanionRoomNative --results /tmp/CompanionRoomQA --test CompanionPhoneUITests/testExperienceGalleryAndAttachmentPicker --test CompanionPhoneUITests/testHomeSearchSharedDraftAndTranscriptSheet
```

The gallery exercises note generation/rendering, context menu, swipe arbitration, copy/delete, attachment, account and search. The second check exercises composer wrapping, mic/send substitution, draft continuity, capture start, transcript sheet, stop, search and dictation. Evidence results and screenshot review are recorded below after execution. Physical touch/haptics and real-audio behavior are not established by simulator QA.

## Observed results

Native iPhone 17 Pro simulator, iOS 26.5, September 29:

- `testHomeSearchSharedDraftAndTranscriptSheet`: passed, 37.914 s. Wrapping, mic/send swap, draft survival across Notes, synthetic capture/transcript/stop, search, dictation discard/send and refresh all executed.
- `testCompanionRoomHeaderAndInvite`: passed, 12.936 s. Home entry, Invite boundary, Notes/back, immediate capture and stop executed.
- `testExperienceGalleryAndAttachmentPicker`: passed, 44.358 s. Note rendering, hold menu, swipe actions, deletion, attachment, account and search executed.
- Mac build passed; Mac interaction and physical iPhone touch/haptics remain unverified.

Result bundles: `/tmp/CompanionRoomQA/20260929-063139/` (composer and header), `/tmp/CompanionRoomQA/20260929-063301/` (gallery). Reproduce using the command above plus `--test CompanionPhoneUITests/testCompanionRoomHeaderAndInvite`.

An earlier run exposed stale offscreen Notes accessibility controls and failed the capture-to-Notes/search check. The inactive page is now removed from the rendered hierarchy instead of hidden with opacity; the controller retains the draft. The stronger check waits for the actual Notes search control, and the complete affected flow passed after correction. Final post-run copy-only change clarifies how to start capture from empty Notes (return to Ellis); it does not alter behavior.

Screenshots inspected: [home](home.png), [capture](capture.png), [notes](notes.png), [native hold preview](note-context.png). The context highlight follows the card's continuous corner shape. Capture has only one status bar; Notes has no composer. These are synthetic local fixtures, not production conversations. No paid provider calls or user-data changes.

## Remaining delivery boundary

Light and dark appearances are implemented and visually inspected in the fidelity correction below. Physical motion/haptic judgment, final companion artwork, invitation delivery and release app icon are not complete. The temporary artwork and Invite state must not be mistaken for finished distribution features. No production backend deployment, merge or completed physical behavioral acceptance is claimed.

Follow-up: red Listening indicator and left-entry Notes navigation verified through `testCompanionRoomHeaderAndInvite` (13.016 s, passed), result bundle `/tmp/CompanionRoomQA/20260929-063859/`. Updated capture screenshot. Prototype capture and Notes/back interactions also exercised. Pause/connection/finishing labels remain unchanged.

## Authorized internal phone installation

September 29: founder explicitly requested phone deployment after reviewing the prototype. Signed Debug build of `0272c5f` succeeded with the existing development team. `devicectl` installed `ai.voicecompanion.phone` as an in-place update on the paired physical iPhone 16 Pro and successfully launched it with `--enable-companion-ui`. No uninstall, data reset, credential replacement, backend deployment or paid call was performed. Existing app container was retained.

Receipts: `/tmp/companion-room-device-build.log`, `/tmp/companion-room-device-install.json`, `/tmp/companion-room-device-launch.json`. This verifies signed build, installation and process launch, not physical touch/haptics, capture or production response acceptance. The draft PR remains open.

## Prototype fidelity correction

Founder rejected the first phone candidate as insufficiently faithful. The approved `arrival-prototype/companion-room.html` remains unchanged. This correction maps its components into SwiftUI rather than proposing another design.

| Prototype element | Native mapping |
| --- | --- |
| Light/dark palette | Exact background, card, ink, muted, wash, line, plum and capture-button hex pairs |
| Header | 126-point content header, 46-point edge controls, centered 76 × 72 companion and 14-point name |
| Chat | 16-point regular text, 14 × 16 padding, 23-point corners with 10-point grouped leading corner, 8-point gaps |
| Composer | 29-point corner, 5-point inset, upright clip, expanding text, mic/send and separate 58-point capture control |
| Capture | 58-point bar, red circle and Listening, time, View, bell and stop |
| Notes | Left-entry whole page, centered title, underlined search, serif heading, stacked 27-point cards |
| Note detail | Rounded sheet, Your note header, serif title, segmented content, 24-point paper card, plum Talk about this |
| Icon paths | Ten prototype Lucide paths exported as template vector PDFs; regeneration script and license retained |

Final targeted execution: gallery, shared draft/composer/transcript and header flows all passed in `/tmp/CompanionRoomQA/20260929-065014/`. Final minor styling refinements passed header/capture again in light (12.942 s, `20260929-065520`) and dark (13.213 s, `20260929-065229`). Mac and signed physical-device builds passed. Screenshots inspected: [home](home.png), [capture](capture.png), [dark capture](capture-dark.png), [Notes](notes.png), [note detail](note-detail.png), [hold actions](note-context.png).

These are actual native screens driven by synthetic local fixtures. No paid calls. The operating system still supplies safe areas, keyboard and native sheet margins/dismissal; real note/chat contents vary. This is not a claim of pixel identity between a fixed-height browser frame and every physical screen. The bell is visible but disabled when contributions are unavailable. Physical haptic and motion feel still require device judgment.

The corrected signed Debug build was installed in place and launched successfully on the paired physical iPhone 16 Pro at the end of this pass. Installation and launch receipts are `/tmp/companion-room-device-install.json` and `/tmp/companion-room-device-launch.json`; build receipt `/tmp/companion-room-device-build.log`. No reset, uninstall or backend change occurred. Device rendering and interaction acceptance remain distinct from these successful receipts.


## Accessory fidelity correction — September 29, 2026

The previous installation matched the main surface but retained old system sheets, an intermediary paperclip menu, inline error cards, and unrelated account previews. The approved prototype now governs these secondary surfaces too. The founder additionally requested a circular send button after noticing the prototype's vertically stretched control; both the reference HTML and native composer now use a 36 × 36 filled control centered within the composer slot.

| Surface | Native mapping and verification |
| --- | --- |
| Paperclip | One tap opens the note picker; real notes appear as white cards. Selecting one attaches its actual title. No intermediary action menu or note icons. |
| Accessory panels | Shared `RoomPanel`: canvas background, 32-point top corners, 20-point horizontal padding, 38-point close control, content-sized height capped at 88%, dimmed/scaled underlying page. |
| Notes / transcript | Same shared panel, serif note title, pill segment selector, white reading paper, real transcript/speaker content and Talk about this action. |
| Invite / profile / memory | Same panel hierarchy and typography. Appearance switches actual app light/dark mode. Memory preference remains connected to the existing controller. Invite stays explicitly unavailable. |
| Errors | Compact ink toast overlays the screen and has an x. No composer displacement or empty failed-answer bubble; uncertain replies retain their existing idempotent recovery path. |
| Composer | Upright paperclip, matching body text, circular send control, mic/send substitution, expanding draft, actual dictation controls retained. |
| Typography / icons | Prototype-rendered system body weight 430 approximated using the native font weight interval; Georgia headings, explicit line heights, existing Lucide vector assets plus matching chevron. |
| Existing note gestures | Swipe and hold Delete / Share / Copy preserved; swipe does not enter note detail. |

The screenshot loop exposed fixed-height panels, partly untappable settings rows, and a disappearing capture bar behind a modal. Panels now measure their content, complete rows have hit areas, and the capture bar retains layout space. Covered controls remain disabled through panel dismissal; tests wait for enabled controls rather than sending taps through a departing modal. An explicit regression checks that the stop button returns to the same vertical position.

Reviewed native screenshots: [composer](composer-send.png), [attachments](attachment-panel.png), [note](note-panel.png), [profile](profile-panel.png), [memory](memory-panel.png), [dark Invite](invite-dark.png). All contain synthetic local fixture content.

Behavioral differences from the prototype are deliberate: real capture/dictation replace simulations; actual note contents determine panel height; unavailable invitations are not implemented; memory copy describes real capabilities; iOS keyboard, share and hold menus remain native. This is not a claim that every OS-owned pixel or unimplemented backend feature matches a browser simulation.

Final accessory verification:

- `testExperienceGalleryAndAttachmentPicker`: passed 43.122 s (notes, swipe/hold actions, picker, search, profile/memory).
- `testCompanionRoomHeaderAndInvite`: passed 16.450 s (home, Invite, Notes, capture).
- `testPrototypePanelsToastAndAppearance`: passed 21.993 s (empty picker, appearance, dark panel, service failure, toast dismissal, no empty bubble, original-request recovery without duplication).
- `testHomeSearchSharedDraftAndTranscriptSheet`: passed 42.987 s (wrapping, mic/send, preserved draft, transcript panel, stable stop-button position, stop/save, dictation and refresh).
- Signed iPhone and Mac builds succeeded. No paid calls; no production backend changes.

Results: `/tmp/CompanionRoomQA/20260929-072907/` (gallery/header) and `/tmp/CompanionRoomQA/20260929-073249/` (final toast/composer). The last visual review corrected an empty failed-answer bubble and clarified the existing recovery action as “Check reply”; affected error and composer flows were rerun after that correction. [Final toast](error-toast.png), [live transcript](transcript-panel.png), [review sheet](accessory-review.png).

Installed in place on the paired iPhone 16 Pro September 29 after these checks; install receipt `/tmp/room-accessories-install.json`. No app uninstall, data reset, paid provider run or backend deployment. Physical haptics and real-audio capture were not re-tested for this presentation change. This candidate remains draft for founder visual review.
