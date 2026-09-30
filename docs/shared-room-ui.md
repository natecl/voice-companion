# Shared prototype interface — internal baseline and checkpoint history

> Recorded baseline update: PR154–155 merged the shared interface and functional integration; this is now the established design system. The earlier “keep draft,” “candidate” and simulator-only statements below describe their dated checkpoints and are superseded only by later recorded integration/install evidence. See [phase integration evidence](qa/phase-integration/README.md) and [release handoff](execution/testflight-release-handoff.md). Preserve assets, typography, motion and interactions while integrating account/lifecycle behavior. Temporary mascot distribution rights and physical/release checks remain explicit gates; installation is not proof of haptic or microphone acceptance. No fresh runtime inspection was performed for this update.

September 29, 2026. The founder selected literal shared presentation code after repeated typography and motion differences between the HTML prototype and SwiftUI recreation. The approved prototype remains the visual source of truth.

## Delivered boundary

`App/RoomUI` contains the approved CSS verbatim, local icons/artwork, the shared document, and interaction runtime. Browser preview and iPhone bundle use identical files. `RoomWebView` hosts only this local document; native `RoomWebModel` connects existing capture, dictation, chat, notes and proactive controllers. No credentials or raw audio enter JavaScript. Dynamic text is escaped or assigned as text content. Browser demonstration data is disabled in the native bridge.

The iPhone rollout preference persists after `--shared-room-ui`; `--disable-shared-room-ui` returns to the preceding native room. Test preferences are isolated by fixture owner. Mac retains its SwiftUI presentation. OS keyboard, permission dialogs and sharing remain native system surfaces.

## Reproducible evidence

- `scripts/check-room-bundle.py --app /tmp/CompanionRoomDevice/Build/Products/Debug-iphoneos/VoiceCompanion.app --prototype <approved companion-room.html>`: passed original CSS comparison, JavaScript syntax and byte-for-byte equality of every bundled interface asset.
- `SharedRoomPhoneUITests/testSharedRoomNativePipeline`: passed with local service and synthetic microphone/dictation. Covers real controller response, circular send bounds, live transcript, saved notes, swipe versus tap, hold actions, attachment/detachment, dictation submit, profile and dark appearance. Final result: `/tmp/CompanionRoomSharedQA/20260929-081015/SharedRoomPhoneUITests-testSharedRoomNativePipeline.xcresult` (36.238 seconds).
- `SharedRoomPhoneUITests/testSharedRoomProactiveAndRelaunch`: passed grouped proactive bubbles, draft preservation, Quiet without stopping capture and durable reopen, including reopening without the rollout launch argument. Result in the same directory (13.752 seconds).
- `SharedRoomPhoneUITests/testSharedRoomFailureAndSafeText`: passed dismissible error, explicit uncertain-reply recovery, no duplicated question, literal HTML-like text and long-press copy. Result: `/tmp/CompanionRoomSharedQA/20260929-080830/SharedRoomPhoneUITests-testSharedRoomFailureAndSafeText.xcresult` (18.795 seconds).
- Signed physical iPhone and unsigned Mac builds passed. No paid provider calls.
- Installed in place and launched on the founder's iPhone 16 Pro. Installation and launch receipts: `/tmp/room-shared-install.json`, `/tmp/room-shared-launch.json`. No uninstall or personal-data reset.

The checks caught and fixed leftover fictional note markup and an overbroad swipe guard that swallowed the next intentional tap. Proactive test initially queried a toggle as a plain button; it now uses the actual accessible control.

## Remaining acceptance

Physical visual/keyboard/motion comparison is in progress. Existing microphone and provider implementations are reused; synthetic tests do not establish real audio performance. Temporary character artwork and unavailable friend invitations remain internal-preview limitations. The checkpoint must not be treated as fully accepted or merged based only on compilation, asset equality or simulator tests.

## Founder follow-up: white background and outlined bubbles

Light-mode canvas is white in the approved source and shared bundle. Message bubbles have a one-pixel inset outline using the existing divider color; this preserves their dimensions and spacing. Updated signed iPhone build, byte equality check, in-place install and launch succeeded. Receipts: `/tmp/room-outlines-{build.log,packaged.json,install.json,launch.json}`. Browser preview was visually inspected. On the physical phone, Notes navigation and the detail panel were exercised; a heavier text appearance remains unresolved, and mirroring was interrupted by phone use before complete keyboard/motion acceptance. No device accessibility preference was changed.

## Founder motion and touch revision — September 29

Founder rejected the original pacing as too fast even after matching its declared timings. The approved source and bundled CSS now share calmer travel (620 ms), panel entry (600 ms), exit (400 ms), message arrival (480 ms), and control release (340 ms), with less front-loaded easing. White canvas and neutral gray surfaces replace lavender washes; the original purple accent remains. Reduce Motion continues to disable transitions/animations.

Note swipes now track horizontal pointer displacement, progressively reveal Delete/Share/Copy, and settle over 520 ms after release. Vertical scrolling locks out swiping; cancellation restores the previous state. Chat left-swipe opens Notes without opening a message menu or interfering with vertical scrolling. Menu navigation remains available. Repeated state delivery no longer moves the welcome bubbles. Panel/toast dismissal waits for compositor animation completion rather than a wall-clock cutoff.

Haptic feedback uses a retained light impact generator prepared at touch-down. Microphone capture opts into iOS haptics during recording; failure of this optional configuration is logged and does not block capture. No capture format, transmission, provider, or persistence behavior changed. This configuration also permits system sounds during recording as specified by Apple's API; audible-artifact impact remains part of physical capture acceptance.

Verification:
- `scripts/qa/room-motion.html`, served from the repository root: 13 passing checks for stable bubbles, 620 ms Notes transition completion, finger tracking, reveal/close/cancel/vertical gesture behavior, chat swipe navigation, panel completion and toast exit. Synthetic pointer dispatch is a focused handler check, not physical touch evidence.
- Native `SharedRoomPhoneUITests/testSharedRoomNativePipeline` passed in 36.545 s; exercises a real XCTest left swipe into Notes, note swipe/hold/tap, attachments, local chat, synthetic capture/dictation and appearance. Result: `/tmp/CompanionRoomCalmQA/20260929-145306/SharedRoomPhoneUITests-testSharedRoomNativePipeline.xcresult`.
- Signed physical build and exact package/source byte check passed (`/tmp/room-calm-phone-build.log`, `/tmp/room-calm-bundle.json`). No paid calls.
- Earlier physical diagnostics measured matching old CSS timings and median 17 ms animation frames with Low Power Mode off. Bold Text was enabled. Neither a device animation speed multiplier nor Low Power Mode was established as the cause. No system preference was changed.
- Physical mirroring displayed the prior updated build, but automated taps failed with `noWindowsAvailable`; founder confirmed the first swipe revision felt better, then requested this slower revision. Final feel, haptic strength and recording-with-haptics acceptance remain pending. At that checkpoint PR154 remained draft; its later merge is recorded above.

Calmer-motion build installed in place and launched successfully on the enrolled iPhone (`/tmp/room-calm-install.json`, `/tmp/room-calm-launch.json`). No uninstall, reset or account mutation. Installation is not physical haptic acceptance.

## Accessory, search and note-tab parity follow-up

See [component audit](shared-room-component-audit.md) for the original-versus-added feature boundary and surface inventory. Fixed search focus theft; retained the Notes/Transcript segment during updates; eased accessory/note entry to 780 ms; exposed the purple Talk about this action even when a note is not yet attachable. Native pipeline and failure/recovery passed at `/tmp/CompanionRoomParityQA/20260929-150335/`. Simulator bundle bytes match preview resources and approved-source CSS. This follow-up is simulator-verified; it has not yet been installed on the physical phone.

## Compact sheets with a fixed note action

Founder revision: note detail is a smaller sheet and Talk about this stays bottom-aligned while content scrolls; attachment scrolling must end at the last card. The shared note sheet is now 64% of the content viewport with a fixed footer (20-point bottom inset). Notes and transcript scroll independently above it; switching tabs resets that content's scroll position. The attachment picker fits short lists and caps at 64%, with no trailing card margin or artificial minimum height.

Native pipeline passed in 81.705 seconds at `/tmp/CompanionRoomPinnedQA/20260929-154608/`, asserting equal action position before/after switching to and scrolling a long transcript, bottom inset and hittability. Screenshot exports: `/tmp/room-pinned-shots/`. The first run caught the existing synthetic live transcript continuing to resize between the test's settling check and tap; its close interaction now waits for a two-second stable frame with a bounded 15-second timeout. `scripts/qa/room-note-layout.html` passed five browser checks, including a twenty-card attachment list ending within 0.09 pixels of the scroll boundary, fixed action and compact height. Bundle/prototype equality passed. No paid calls; this update remains simulator-only.

Founder-authorized physical install: bc8a58c signed iPhone build and package/source byte check passed, installed in place and launched on the paired iPhone 16 Pro. Receipts: `/tmp/room-pinned-device-build.log`, `/tmp/room-pinned-device-bundle.json`, `/tmp/room-pinned-install.json`, `/tmp/room-pinned-launch.json`. No uninstall or data reset. This supersedes the simulator-only delivery status above; physical feel remains a separate acceptance check.

## Dictation cancellation composer regression

Canceling dictation measured the hidden textarea before restoring its visibility. Its zero scrollHeight produced a 22-point padded box and clipped the Message Ellis placeholder. Visibility now updates before sizing; hidden fields are never measured, and visible height is bounded to 44–116 points. Empty input scroll position resets. No typography or composer styling changed.

Reproduced before the fix using `scripts/qa/room-dictation-layout.html`: empty, short and multiline drafts all collapsed to 22 points after cancellation. After the fix all three preserved their initial 44/44/116-point heights through three cycles, with draft content intact. Native `testSharedRoomDictationCancellationLayout` passed three start/discard cycles and typing afterward at `/tmp/CompanionRoomCancelQA/20260929-155729/`. Screenshot inspected: `/tmp/room-cancel-shots/DB1AE871-9349-494C-BB95-32A34F6ADAEA.png`. Signed physical build, asset-byte check and in-place installation passed (`/tmp/room-cancel-device-build.log`, `/tmp/room-cancel-bundle.json`, `/tmp/room-cancel-install.json`). No paid calls or data reset.

## Sheet grab-handle dismissal

All shared bottom sheets now track downward dragging from the top grip, with a larger invisible touch target around the original line. Pulling at least 22% of the sheet height (capped at 100 points) dismisses from the dragged position; shorter/canceled gestures return over 340 ms. Content scrolling remains independent. Keyboard/assistive activation and the close button remain available. Gesture-end clicks are suppressed so a short drag cannot become a backdrop dismissal. Reduced Motion skips the settling animation.

`testSharedRoomSheetDragDismissal` passed short-pull restoration, long-pull dismissal, underlying composer hittability and clean reopening in `/tmp/CompanionRoomDragQA/20260929-160749/`. Earlier runs identified the backdrop-click edge case before the fix. Screenshot export `/tmp/room-drag-shots/`. Signed device build and asset equality passed; installed in place on the paired phone (`/tmp/room-drag-device-build.log`, `/tmp/room-drag-bundle.json`, `/tmp/room-drag-install.json`). No data reset or paid provider calls. Physical feel remains founder acceptance.

## Content-sized notes and dictation send feedback

Saved note sheets start at 64% of the app viewport and grow with their content up to 94%; overflowing content scrolls independently above the bottom-pinned Talk about this action. Multiline detail titles use 1.2 line height (34.8 points at 29-point type), and library titles use 1.35. The dictation arrow acknowledges its tap immediately with Sending… and disables duplicate taps until the native session finishes. Speech finalization and its error handling remain unchanged; this fixes perceived button latency, not recognition latency.

Verification: `scripts/qa/room-note-layout.html` passed ten browser checks at 402×778, including short/long sheet sizing, multiline title leading, pinned footer, attachment end alignment, immediate send acknowledgement and a fresh dictation session. The fixture clones its state so preview transport cannot overwrite its short/long content. Native `testSharedRoomNativePipeline` passed in 80.629 seconds: `/tmp/CompanionRoomAdaptiveQA/20260929-161826/SharedRoomPhoneUITests-testSharedRoomNativePipeline.xcresult`. Native note screenshot inspected at `/tmp/room-adaptive-shots/0B6FFB93-1ED6-4AF6-9882-587A7719906F.png`. Signed device build and prototype/bundled byte equality passed. Synthetic/local fixtures only; no paid calls or personal-data changes. Physical speech recognition timing has not been measured by this check.

## Preview-card typeface as default

Founder requested the preview cards' typeface throughout the interface. Removed the separate Georgia heading family; headings now inherit the same system sans-serif stack as preview cards, note bodies, chat and composer. Heading weight matches card titles (500); body copy retains the preview excerpt weight (430), with contextual sizes unchanged. Browser inspection confirmed identical computed font families across all six surfaces and the note was visually reviewed. Signed iPhone build and packaged/prototype equality passed (`/tmp/room-font-build.log`). No controller or behavioral changes.
