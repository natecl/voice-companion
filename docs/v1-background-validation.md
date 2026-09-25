# V1 background capture — bounded verification

Checkpoint 2, September 24, 2026. Verified for the existing five-minute internal limit. Implementation tested: `37f0455`; subsequent changes only document evidence.

The iPhone declares audio background mode and keeps its already-active recording when the scene backgrounds. A session still preparing/connecting is cancelled. Mac and synthetic UI-fixture behavior retain foreground-only handling. Session JSON uses atomic writes with protection until first unlock, allowing incremental saves while the previously unlocked phone is locked. The existing Keychain item is likewise accessible after first unlock on this device only.

A short UIKit background task covers normal/automatic finalization after capture stops, with expiration cancelling and preserving incomplete text. It is ended after the controller saves the result, and does not keep an idle microphone alive. Existing call/route interruption handling remains safe-stop, without automatic reconnection. The existing five-minute app limit and server usage budgets remain unchanged. The UI explains locking and reopening to Stop; custom Live Activities and lock-screen Stop controls are not part of this first implementation.

Apple references: [record category and background mode](https://developer.apple.com/documentation/avfaudio/avaudiosession/category-swift.struct/record), [bounded background tasks](https://developer.apple.com/documentation/uikit/uiapplication/beginbackgroundtask(withname:expirationhandler:)), [file protection](https://developer.apple.com/documentation/foundation/nsdata/writingoptions/completefileprotectionuntilfirstuserauthentication).

Local checks: 22 selected lifecycle/transport tests ran, 21 passed and the existing opt-in 90-second test was skipped. Actual controller/store fixtures cover active background preservation followed by Stop/save, preparation cancellation, existing foreground-only interruption persistence, transport errors, and quota rejection before capture. Mac build/test target passed; signed physical-iPhone build passed. Logs: ignored work/v1-background-tests.log and work/v1-background-device-build.log. These checks do not prove iOS background scheduling, lock-screen persistence or real audio capture.

## Physical iPhone evidence

Physical iPhone 16 Pro, installed signed build from `37f0455`, hosted relay from `381d243`. The founder performed the following checks; saved session metadata copied from the device and content-free Render logs independently corroborate outcomes. Private transcript text is not committed. Evidence: ignored `work/background-phone-sessions/` and Render application logs.

| Started (UTC September 25) | Check | Outcome |
| --- | --- | --- |
| 02:39:21 | Short locked-screen capture, unlock and explicit Stop | Founder confirmed all speech including locked speech saved and reopened. Phone completed, 34.59 seconds; server completed with 34.5908 audio seconds. |
| 02:46:50 | Incoming phone call while recording | Recording stopped when the call arrived, before answer. Screenshot and founder confirmation show interruption reason and saved received text. Device incomplete with explicit interruption at 7.87 seconds; server closed at 7.6868 audio seconds. This is expected safe-stop, not a successful complete transcript. |
| 02:50:52 | Five-minute locked capture and automatic stop | Device completed at 300.35 seconds, no end error, explicit 300-second automatic-stop notice, 38 transcript segments through 300.092 seconds. Server completed at 300.2982 audio seconds and 303.148 seconds total connection duration. |

Request IDs respectively: `f03d82a4-3570-4f2c-8db5-a3072b54452d`, `1abb98c7-3038-4340-ba33-720d43d5b5be`, `b8e5e9e4-d6fc-4c1a-996f-866727c9fd84`.

The five-minute test was explicitly readied, then the founder reported completion. The native persisted auto-stop state and remote completion demonstrate finalization after the cap. Audio and transcript duration can exceed 300 seconds slightly due to buffer scheduling; the server's 310-second allowance remains intact. The server stopped receiving audio and ended the connection; no automatic retry/resume occurred.

Three checkpoint calls cost approximately $0.01903 in audio estimates, not verified billing; conservative reservations total $0.06. Combined with checkpoint 1, six attempts use the current UTC day's six-attempt allowance, approximately $0.02434 estimated audio cost and $0.12 conservative reservations. No more paid recordings are required for this checkpoint.

## Acceptance and limits

This completes the bounded five-minute background-capture checkpoint: live microphone speech while locked, explicit Stop/save/reopen, safe incoming-call interruption, and full-limit automatic stop/finalization have real-device evidence. Mac code still builds and retains its existing background policy. Local checks are not substituted for those real paths.

No 30-minute or all-day endurance, battery-drain benchmark, force-quit continuation, seamless call recovery, lock-screen Stop, or custom Live Activity is claimed. Keep the five-minute cap. Device resource/battery measurements and a longer-cap trial remain separate work before increasing it. The status surfaces remain the native microphone indicator and explicit in-app recording/finished/interrupted state. Next is checkpoint 3: Ask on a saved conversation, which can use existing transcripts without new STT calls.
