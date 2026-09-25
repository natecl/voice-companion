# V1 background capture — verification in progress

Checkpoint 2, September 24, 2026. Not yet accepted or merged.

The iPhone declares audio background mode and keeps its already-active recording when the scene backgrounds. A session still preparing/connecting is cancelled. Mac and synthetic UI-fixture behavior retain foreground-only handling. Session JSON uses atomic writes with protection until first unlock, allowing incremental saves while the previously unlocked phone is locked. The existing Keychain item is likewise accessible after first unlock on this device only.

A short UIKit background task covers normal/automatic finalization after capture stops, with expiration cancelling and preserving incomplete text. It is ended after the controller saves the result, and does not keep an idle microphone alive. Existing call/route interruption handling remains safe-stop, without automatic reconnection. The existing five-minute app limit and server usage budgets remain unchanged. The UI explains locking and reopening to Stop; custom Live Activities and lock-screen Stop controls are not part of this first implementation.

Apple references: [record category and background mode](https://developer.apple.com/documentation/avfaudio/avaudiosession/category-swift.struct/record), [bounded background tasks](https://developer.apple.com/documentation/uikit/uiapplication/beginbackgroundtask(withname:expirationhandler:)), [file protection](https://developer.apple.com/documentation/foundation/nsdata/writingoptions/completefileprotectionuntilfirstuserauthentication).

Local checks: 22 selected lifecycle/transport tests ran, 21 passed and the existing opt-in 90-second test was skipped. Actual controller/store fixtures cover active background preservation followed by Stop/save, preparation cancellation, existing foreground-only interruption persistence, transport errors, and quota rejection before capture. Mac build/test target passed; signed physical-iPhone build passed. Logs: ignored work/v1-background-tests.log and work/v1-background-device-build.log. These checks do not prove iOS background scheduling, lock-screen persistence or real audio capture.

Pending physical QA after explicit founder readiness:
1. One approximately 45-second microphone session: speak a distinct phrase in-app, lock for about 20 seconds while speaking a second phrase, unlock/reopen and Stop. Verify the locked phrase in saved text and server completion. Expected STT cost about $0.0025; reservation $0.02, no automatic retry.
2. Separately verify a real audio interruption stops safely and preserves text.
3. A bounded longer session before making an endurance claim or increasing the limit. A 30-minute cap is not enabled.

No paid calls were made while implementing these changes. Do not merge on local tests alone.
