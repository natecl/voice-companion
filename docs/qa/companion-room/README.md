# Companion room native candidate

September 29, 2026. Based on verified main `47eadb4`; independent of the pending background phase PRs. This is a native presentation checkpoint, not a backend/model or capture-provider change. It is not installed on the physical phone or deployed.

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

This is a light-appearance native candidate. Dark appearance, physical motion/haptic judgment, final companion artwork, invitation delivery and release app icon are not complete. The temporary artwork and Invite state must not be mistaken for finished distribution features. No phone install, deployment or merge is claimed.

Follow-up: red Listening indicator and left-entry Notes navigation verified through `testCompanionRoomHeaderAndInvite` (13.016 s, passed), result bundle `/tmp/CompanionRoomQA/20260929-063859/`. Updated capture screenshot. Prototype capture and Notes/back interactions also exercised. Pause/connection/finishing labels remain unchanged.
