# Phased-work integration review — September 29, 2026

The founder requested merging the UI and integrating/reviewing the background changes without changing its presentation. PR154 merged as `dd907d4`; the reviewed UI implementation is `4bb2bdb`, followed by documentation-only `8d00c39`. This is the internal UI baseline, not TestFlight acceptance.

Initial candidate `ebda961` combined the existing phase-wave branch, final cache source `0ef90b4`, and merged main. Follow-up implementation `b9bfb68` wires the shared cache and fixes the reproduced touch loss; final verification is recorded below. The Xcode project was regenerated after resolving references. The SwiftUI notes conflict retains main's visual markup, padding and card geometry rather than reintroducing the worker's older presentation.

## Presentation preservation

Shared HTML, CSS, typography, colors, icons, assets and animation durations match the merged UI baseline. `RoomWebModel` now uses the cache. The only shared JavaScript changes preserve a pressed control through incoming state updates and refresh an open note’s title/metadata with its body. These are functional integration repairs, not design changes. `RoomWebView` is unchanged. `scripts/check-room-bundle.py` also confirms packaged shared resources match. Identical assets alone do not prove correct runtime behavior.

## Review dispositions

| Source PR | Disposition and scope |
| --- | --- |
| 149 capture preparation | Code and disk/controller regression accepted for candidate integration. Integrated lifecycle tests pass. No new physical permission/background claim. |
| 150 baseline repairs | Narrow mechanical/historical replay repair accepted. Current prompts cannot silently consume historical outputs; no current model-quality claim. |
| 151 proactive controls | Lease-expiry scheduling fix accepted for candidate integration. Authenticated loopback socket/storage, cancellation and budget cases pass. No production rollout, distribution activation or live-model claim. |
| 152 distribution audit | Read-only audit accepted. Release enrollment, account clearing, signing/archive and independent install/update are still outstanding. |
| 153 note cache | Cache foundation and shared iPhone integration accepted for this bounded checkpoint. Fresh shared-shell staged tests cover offline relaunch, delayed title/body replacement, revision invalidation, remote deletion and local deletion. Logout, owner-transition clearing and reset integration remain open; this is not full account-lifecycle acceptance. |

## Integrated evidence

- 85 backend tests passed: `/tmp/phase-integration-backend.log`. Modules: memory_atomic, memory_identity, memory_retention, memory_transitions, proactive_policy, proactive_service, proactive_socket, proactive_stream, proactive_phone_qa and proactive_conversation. Actual local sockets and SQLite fixtures; no paid calls.
- 19 native tests passed (8 lifecycle, 11 cache): `/tmp/phase-integration-native.log`; `/tmp/VoiceCompanion-phase-wave-review/Logs/Test/Test-Mac-2026.09.29_17-07-41--0400.xcresult`.
- Initial integrated simulator pipeline failed to expose End recording after tapping Close panel in a growing live transcript: `/tmp/PhaseIntegrationUI/20260929-170740/SharedRoomPhoneUITests-testSharedRoomNativePipeline.xcresult`. Preserved recording, AX tree and event coordinates: `/tmp/phase-ui-failure/`. The tap was at the visible close-button center (363,203), yet the dialog remained visible. Do not classify this as a resolved timing flake without further evidence.
- The unchanged UI branch passed the same pipeline in `/tmp/PhaseUIBaseline/`; this bounds the comparison but does not alone prove integration innocence. One diagnostic integrated repeat is recorded separately.

## Initial review findings (resolved below)

Resolve the transcript-close failure without changing visual design or weakening interaction assertions. Wire the existing cache behind RoomWebModel with owner/revision checks, immediate reads, coalesced refresh, authoritative invalidation and safe error preservation. Verify actual shared-shell offline relaunch/update/deletion using the existing fictional fixture. Preserve visual assets. Account lifecycle and Release enrollment remain separate follow-on work; no upload, invitations, provider spending or deployment occurred in this review.

Diagnostic repeat: the unchanged integrated source passed the complete shared-room native pipeline at `/tmp/PhaseIntegrationRepeat/20260929-171156/SharedRoomPhoneUITests-testSharedRoomNativePipeline.xcresult`. Exported note/action screenshot inspected at `/tmp/phase-integration-shots/AEAB8D11-2FBB-42B2-8564-57EBC402CEB6.png`; presentation matches the merged system-font UI baseline. The earlier missed close tap remains an intermittent interaction issue, not erased by the passing repeat. No acceptance assertion or runtime code was changed to obtain this pass. That repeat did not close either finding; the subsequent work below does.


## Shared-cache and touch repair — `b9bfb68`

RoomWebModel hydrates ready summaries synchronously from owner/session/revision-scoped storage, then revalidates through the same cache and authenticated connection. Opening the library revalidates entries sequentially; foregrounding refreshes the selected note without fetching the entire library. Duplicate reads coalesce. Pending/failed regeneration retains the last ready summary; authoritative revision/deletion errors remove it. Local deletion cancels and clears matching presentation tasks/content. Late task cleanup is identity-guarded so an old cancelled task cannot erase a replacement task.

The close failure was reproduced in `SharedRoomPhoneUITests/testLiveTranscriptCloseDuringUpdates`: a 400ms press across the synthetic source’s 250ms updates failed on the first close. Temporary content-free tracing saw `pointerdown` and `pointerup` on `close`, but no compatibility click. No close handler or animation ran. Keeping incoming state queued while a touch presses a button restored down/up/mousedown/mouseup/click and five successful closes. Queued state flushes after the click, cancellation/blur, or a 100ms no-click fallback after release. Mouse/keyboard behavior and animation durations are unchanged. The diagnostic trace code was removed; the regression stays.

- Failed focused reproduction: `/tmp/TranscriptCloseProbe/`; diagnostic failure `/tmp/TranscriptTouchProbe/`. The original integration failure above remains retained.
- Instrumented repaired run: `/tmp/TranscriptTouchStable/20260929-172430/SharedRoomPhoneUITests-testLiveTranscriptCloseDuringUpdates.xcresult` — five closes passed with continuous updates.
- Eight staged shared-iPhone cache tests passed in `/tmp/SharedCacheFinal/`: three independent population stages, offline relaunch/server-stopped preservation, gated title/body update, actual source revision invalidation, actual remote source deletion, and local swipe/delete. Saved screenshots: [updated note](shared-cache-after-update.png), [stale source](shared-cache-stale-removed.png), [remote deletion](shared-cache-remote-delete.png), [local deletion](shared-cache-local-delete.png), [offline](shared-cache-offline-preserved.png). The offline screenshot includes the existing connection-error toast; assertions separately confirm saved content remains present.
- Actual app-container inspection after local deletion found zero cached summary JSON files and one content-free deletion marker for that fictional owner: [disk receipt](shared-cache-disk.json).
- Nineteen lifecycle/cache CoreTests also passed at `/tmp/VoiceCompanion-phase-wave-review/Logs/Test/Test-Mac-2026.09.29_17-24-56--0400.xcresult`. The 85 backend results above remain applicable; backend code did not change in this follow-up.

Reproduce cache scenarios with `python3 scripts/check-shared-note-cache.py --simulator YOUR_ID --results /tmp/NEW_RESULT_DIRECTORY`. It preserves earlier fixture directories, uses fresh fictional owners, and stops its local servers. Use only one simulator QA run at a time. The original run used the equivalent staged commands before packaging this runner.

Reproduce touch and complete app-pipeline checks with `python3 scripts/check-experience-ui.py --simulator YOUR_ID --test SharedRoomPhoneUITests/testLiveTranscriptCloseDuringUpdates --test SharedRoomPhoneUITests/testSharedRoomNativePipeline --results /tmp/NEW_RESULT_DIRECTORY`.

This checkpoint does not activate release proactive behavior, deliver account enrollment/sign-out/reset, establish physical capture or locked-device storage behavior, perform paid inference, upload TestFlight, or install on the founder’s phone. Those remain separately gated work. Prior provider-quality and physical-device receipts are historical, not refreshed by loopback QA.


Final uninstrumented checks passed at `/tmp/PhaseIntegrationFinal/20260929-172859/`: five consecutive close interactions during live updates, then the complete native chat → capture → transcript → note swipe/hold/search → fixed-footer note/transcript → attach/detach → dictation-send → profile flow. The complete flow built `b9bfb68`; the close regression uses the same JavaScript bytes. [Final note screenshot](shared-note-final.png) was inspected against the merged design. Bundle hashes match repository assets; HTML/CSS/icons/images and animation timing are unchanged from `dd907d4`. The transient tracing code is absent from the final source.

Review decision: accept PR155 as the bounded internal integration checkpoint. All two initial integration findings are addressed. Full CACHE-1 account lifecycle, Release access/proactive activation, signing/archive and real-device/TestFlight acceptance remain open; merging this integration is not distribution approval.
