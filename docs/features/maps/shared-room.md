# Shared companion-room interface

Status: internal candidate installed on the founder’s iPhone; physical acceptance remains in progress. Depends on PR 154's native baseline. Founder revision: approved prototype UI is the source of truth, now shared literally instead of translated into SwiftUI.

## Owned boundary

- `App/RoomUI/index.html`, `room.css`, `runtime.css`, `icons.js`, `room.js`: the same bundled interface in browser and iPhone. The approved prototype CSS is preserved verbatim. Runtime CSS supplies the previous host reset, platform viewport sizing and retained note gestures/dictation/error states absent from the prototype.
- `App/RoomWebView.swift`: local-only WebKit host, typed action dispatch, serialized state delivery, no remote navigation or provider credentials.
- `App/RoomWebModel.swift`: maps existing capture, chat, notes, dictation and proactive controllers into the presentation. Native storage/model/provider behavior remains authoritative.
- `App/VoiceCompanionApp.swift`: persisted `--shared-room-ui` rollout flag, reversed with `--disable-shared-room-ui`. Previous SwiftUI room remains available for rollback; Mac stays native.

Browser preview: `python3 -m http.server 61715 --bind 127.0.0.1 --directory App/RoomUI`. Preview-only fictional data runs only without the native message handler; it cannot invoke device/provider actions. Production markup contains no fictional notes.

## Verification

`python3 scripts/check-room-bundle.py --app <built-app-path> --prototype <approved-prototype-path>` verifies original CSS, JavaScript syntax, and byte-for-byte equality between preview and app resource files. It does not establish pixel fidelity, accessibility or native behavior by itself.

`python3 scripts/check-experience-ui.py --simulator <id> --derived-data /tmp/CompanionRoomSharedNative --results /tmp/CompanionRoomSharedQA --test SharedRoomPhoneUITests/testSharedRoomNativePipeline` exercises the real local native controllers with synthetic recording/dictation and local provider fixtures. No paid calls; not real microphone evidence.

Remaining gates: screenshot inspection, gesture and error/recovery checks, physical iPhone keyboard/viewport/motion and native capture/dictation acceptance. Do not merge or declare physical acceptance while these are unverified. The preceding native room remains available as a rollback. Temporary companion artwork and unavailable invitations remain internal-preview limitations. iOS/system share sheets and permission prompts remain system UI.

Evidence and installation status: [shared interface checkpoint](../../shared-room-ui.md).

Latest motion slice: `scripts/qa/room-motion.html` provides the isolated browser motion/gesture verifier. Shared calm motion tokens, finger-tracked note actions, and chat left-swipe navigation are implemented; native fixture pipeline passed. Haptic bridge now prepares a retained impact generator, and capture enables optional recording-time haptics. Physical feel and capture/haptic coexistence remain unverified; see checkpoint evidence above before advancing acceptance.
