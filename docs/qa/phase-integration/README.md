# Phased-work integration review — September 29, 2026

The founder requested merging the UI and integrating/reviewing the background changes without changing its presentation. PR154 merged as `dd907d4`; the reviewed UI implementation is `4bb2bdb`, followed by documentation-only `8d00c39`. This is the internal UI baseline, not TestFlight acceptance.

Candidate `ebda961` combines the existing phase-wave branch, final cache source `0ef90b4`, and merged main. PR155 remains draft. The Xcode project was regenerated after resolving references. The SwiftUI notes conflict retains main's visual markup, padding and card geometry rather than reintroducing the worker's older presentation.

## Presentation preservation

`git diff --quiet origin/main -- App/RoomUI App/RoomWebView.swift App/RoomWebModel.swift App/ExperienceStyle.swift App/CompanionRootView.swift` passes. Shared HTML/CSS/JS, typography, colors, icons, transitions and shell wiring are unchanged. `scripts/check-room-bundle.py` also confirms packaged shared resources match. Identical assets alone do not prove correct runtime behavior.

## Review dispositions

| Source PR | Disposition and scope |
| --- | --- |
| 149 capture preparation | Code and disk/controller regression accepted for candidate integration. Integrated lifecycle tests pass. No new physical permission/background claim. |
| 150 baseline repairs | Narrow mechanical/historical replay repair accepted. Current prompts cannot silently consume historical outputs; no current model-quality claim. |
| 151 proactive controls | Lease-expiry scheduling fix accepted for candidate integration. Authenticated loopback socket/storage, cancellation and budget cases pass. No production rollout, distribution activation or live-model claim. |
| 152 distribution audit | Read-only audit accepted. Release enrollment, account clearing, signing/archive and independent install/update are still outstanding. |
| 153 note cache | Foundation accepted for candidate integration; complete feature changes required. Final revision/tombstone and cleanup-failure fixes are present. The shared iPhone RoomWebModel still reads RecordingNotesConnection directly, bypassing this cache. Worker UI evidence targets the previous SwiftUI notes view and cannot establish new-shell offline behavior. Logout, owner-transition and reset integration remain open. |

## Integrated evidence

- 85 backend tests passed: `/tmp/phase-integration-backend.log`. Modules: memory_atomic, memory_identity, memory_retention, memory_transitions, proactive_policy, proactive_service, proactive_socket, proactive_stream, proactive_phone_qa and proactive_conversation. Actual local sockets and SQLite fixtures; no paid calls.
- 19 native tests passed (8 lifecycle, 11 cache): `/tmp/phase-integration-native.log`; `/tmp/VoiceCompanion-phase-wave-review/Logs/Test/Test-Mac-2026.09.29_17-07-41--0400.xcresult`.
- Initial integrated simulator pipeline failed to expose End recording after tapping Close panel in a growing live transcript: `/tmp/PhaseIntegrationUI/20260929-170740/SharedRoomPhoneUITests-testSharedRoomNativePipeline.xcresult`. Preserved recording, AX tree and event coordinates: `/tmp/phase-ui-failure/`. The tap was at the visible close-button center (363,203), yet the dialog remained visible. Do not classify this as a resolved timing flake without further evidence.
- The unchanged UI branch passed the same pipeline in `/tmp/PhaseUIBaseline/`; this bounds the comparison but does not alone prove integration innocence. One diagnostic integrated repeat is recorded separately.

## Next bounded acceptance

Resolve the transcript-close failure without changing visual design or weakening interaction assertions. Wire the existing cache behind RoomWebModel with owner/revision checks, immediate reads, coalesced refresh, authoritative invalidation and safe error preservation. Verify actual shared-shell offline relaunch/update/deletion using the existing fictional fixture. Preserve all UI assets. Account lifecycle and Release enrollment remain separate follow-on work; no upload, invitations, provider spending or deployment occurred in this review.

Diagnostic repeat: the unchanged integrated source passed the complete shared-room native pipeline at `/tmp/PhaseIntegrationRepeat/20260929-171156/SharedRoomPhoneUITests-testSharedRoomNativePipeline.xcresult`. Exported note/action screenshot inspected at `/tmp/phase-integration-shots/AEAB8D11-2FBB-42B2-8564-57EBC402CEB6.png`; presentation matches the merged system-font UI baseline. The earlier missed close tap remains an intermittent interaction issue, not erased by the passing repeat. No acceptance assertion or runtime code was changed to obtain this pass. Keep integration draft while that reliability concern and shared-shell cache wiring remain open.
