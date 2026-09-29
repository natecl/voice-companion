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
