# Prototype / iPhone component audit — September 29, 2026

The founder's scope is the approved prototype as the baseline, retaining later functionality such as note swipe actions, real capture/dictation, memory controls and recovery. This is a component audit, not a claim that different content or iOS system surfaces produce identical pixels.

## Shared source and fixed discrepancies

The preview at port 61715 and the simulator load the same `App/RoomUI` HTML, CSS, icons, artwork and interaction code. `scripts/check-room-bundle.py` passed byte equality against the built simulator app and original approved CSS. Native controllers supply actual data; browser fixtures do not run on iPhone.

- Search previously focused the field, then the navigation callback stole focus. Search now retains focus and filters the native library; zero-results and clearing were exercised.
- Attachment and note sheets enter over 780 ms with gentler easing. Their baseline heights are 42% and 72% respectively.
- Notes/Transcript keeps the segment mounted, moves its indicator over 520 ms, and reveals content over 560 ms. Data updates do not replay the explicit tab-switch animation.
- Every saved note exposes the purple Talk about this action. Pending/unavailable notes show a disabled action with an explanation, rather than silently omitting it. Ready notes still attach to the persistent main chat.

## Surface inventory

| Surface | Verification / preserved boundary |
| --- | --- |
| Companion header, artwork, Notes menu, Invite | Same source, inspected browser and simulator welcome/profile screenshots. Invite remains an explicitly unavailable internal-preview feature. |
| Welcome, message bubbles, typography, outline | Same source; simulator welcome, sent/reply and failure screenshots inspected. System Bold Text remains a physical-device variable, not overridden. |
| Composer, upright paperclip, mic/arrow, plus | Native keyboard entry and send; square bounds asserted for arrow button. Native dictation is retained later functionality. |
| Listening bar, red dot, View, Quiet, Stop | Shared markup; synthetic native capture/View/Stop exercised. Earlier proactive verifier covers Quiet. No new real-microphone claim. |
| Notes page, search, empty results, cards | Browser and native navigation/filtering exercised; content differs by fixture. |
| Note sheet, Notes/Transcript, Talk about this | Browser tabs inspected, native tabs/attachment exercised. Long transcripts scroll; the action follows content as in the prototype. |
| Attachment picker and attached-note chip | Browser picker inspected; native attach/remove tested. Availability reflects actual synchronized notes. |
| Profile, appearance, memory information | Browser profile and memory panels inspected; native profile/dark screenshots and memory-panel coverage. |
| Black error popup, dismiss, uncertain-reply recovery | Native failure test passed; screenshot inspected. Existing recovery action retained. |
| Long-press message copy | Native failure/safe-text test passed; uses the shared sheet. |
| Note swipe Delete/Share/Copy, hold menu, deletion confirmation | Later functionality intentionally retained, not replaced by prototype simulation. Native swipe-versus-tap/hold exercised. No personal note deleted or shared in this audit. |
| Conversation refresh, native share/permission dialogs | Later functionality / OS surfaces, not required to reproduce the prototype's mock interactions. |

## Evidence and limits

Native controller pipeline and failure/recovery passed in `/tmp/CompanionRoomParityQA/20260929-150335/`. Exported images are `/tmp/room-parity-final-shots/` and `/tmp/room-parity-error-shots/`. Browser compared at 402×778, the simulator's web-content area; iOS safe areas/status bar are outside that area.

Initial screenshot capture could occur during sheet entry. The screenshot helper now waits for the close control to settle. A follow-up exposed the live synthetic transcript's growing height; that surface has a longer bounded settling window. This is not a relaxation of functional assertions. The separate accessory-panel check passed in 23.447 seconds at `/tmp/CompanionRoomPanelQA/20260929-153704/`, including invitation, profile, memory controls and an empty attachment picker. Both built and installed simulator resource bytes were checked.

Simulator checks use local provider responses and synthetic recording/dictation, with no paid calls. Physical haptic feel, real microphone behavior and complete physical acceptance are not established by these checks. PR 154 stays draft until those acceptance gates are complete.

Final expanded native pipeline passed in 76.127 seconds: `/tmp/CompanionRoomFinalQA/20260929-153823/SharedRoomPhoneUITests-testSharedRoomNativePipeline.xcresult`. It includes settled note/attachment screenshots and memory controls; exports are `/tmp/room-final-evidence/`. [Selected simulator panels](qa/shared-room-parity/simulator-panels.jpg).
