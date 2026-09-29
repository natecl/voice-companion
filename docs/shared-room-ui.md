# Shared prototype interface — internal candidate

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
- Physical mirroring displayed the prior updated build, but automated taps failed with `noWindowsAvailable`; founder confirmed the first swipe revision felt better, then requested this slower revision. Final feel, haptic strength and recording-with-haptics acceptance remain pending. Keep PR 154 draft.

Calmer-motion build installed in place and launched successfully on the enrolled iPhone (`/tmp/room-calm-install.json`, `/tmp/room-calm-launch.json`). No uninstall, reset or account mutation. Installation is not physical haptic acceptance.

## Accessory, search and note-tab parity follow-up

See [component audit](shared-room-component-audit.md) for the original-versus-added feature boundary and surface inventory. Fixed search focus theft; retained the Notes/Transcript segment during updates; eased accessory/note entry to 780 ms; exposed the purple Talk about this action even when a note is not yet attachable. Native pipeline and failure/recovery passed at `/tmp/CompanionRoomParityQA/20260929-150335/`. Simulator bundle bytes match preview resources and approved-source CSS. This follow-up is simulator-verified; it has not yet been installed on the physical phone.
