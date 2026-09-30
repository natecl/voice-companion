# Ask while listening — verified checkpoint 5

> Historical Ask-during-capture checkpoint. Its selected-session history and visible source/cutoff presentation predate the persistent main chat and current release presentation. The physical/provider evidence remains bounded to the recorded run. See [current state](current-state.md) for selected behavior and current evidence boundaries.

Checkpoint 5 starts from verified main `5d7437c`; Jev deferral is merged in PR #21. Direct Luna provider/settings remain unchanged; hosted changes add explicitly approved QA admission grants. Native changes allow one Ask while recording, snapshot transcript passages before sending, persist its cutoff and interim-text caveat, and keep capture/answer controls and error states independent. Source snapshots stay fixed across later speech and transcript revisions. Backgrounding cancels Ask while supported background recording continues. Ask remains disabled during connection/finalization/replay and before text arrives.

UI places Ask before the growing transcript, with recording controls kept in the existing fixed bottom bar. Each answer shows the received-transcript cutoff, excludes later speech explicitly, and marks provisional source text. Question/answer history still belongs to the selected session; old saved answers decode without the new optional metadata. No change to backend request shape, prompt, provider, model, monetary budgets, or recording duration.

Verification:
- 19 focused native tests passed: six existing saved-Ask cases, seven recording lifecycle cases, six new live-Ask cases. New cases exercise real controller/store behavior with controlled streams: immutable snapshot despite correction/later speech, Stop without cancelling Ask, cancellation without stopping capture, duplicate Ask rejection, independent failures, background cancellation with ongoing recording, and saved reopening.
- Both simulator UI tests passed: existing saved Ask/relaunch and new Ask during fixture recording, cutoff rendering, independent Stop, and source inspection. Exported screenshot visually inspected. These are synthetic UI fixtures, not microphone/provider proof.
- Signed physical-iPhone build passed; no provider call needed for build/UI checks.
- Actual local WebSocket integration passed: simultaneous audio and Ask, cancel Ask, then deliver more audio and finalize STT. Exactly one synthetic STT stream remained alive; no external provider calls.
- Diff whitespace check passed.

Ignored evidence: `work/live-ask-core-tests.log`, `work/live-ask-ui-tests.log`, `work/live-ask-ui-attachments/`, `work/live-ask-device-build.log`, `work/live-ask-relay-test.log`.

## Physical iPhone evidence — September 25, 2026

Native implementation `fc7bc1c` was built and installed on the iPhone 16 Pro (iOS 26.5.2); subsequent commits changed backend QA admission and documentation only. Final tested/deployed backend is `f5e022e`, deployment `dep-darbtrojo6nc73fc2l40`. Founder operated the actual microphone/Ask UI. Read-only device-container inspection independently verified the persisted session JSON and immutable sources; this is storage inspection, not an independent screen recording of the phone.

First live-Ask run: STT request `57c94eaa-d711-46fa-9d76-e44074813ebf` completed with 39.097375 seconds audio. Ask `8de4bbbe-6ade-4673-8f53-aedc4776357a` completed at 18:30:08 UTC, first text 6.207 seconds, completion 6.697 seconds, 804 input/36 output tokens. Founder confirmed a good answer but was unsure whether speech followed its completion. Saved-session inspection showed later transcript beyond the frozen answer cutoff, supporting capture during generation. It did not establish speech after completion; a focused second run resolved that uncertainty.

Second run: founder recorded the supplied appointment fact, asked when it was, waited for the completed answer, spoke the supplied distinct purple-umbrella phrase, then stopped. Session `6C88A39F-8924-4737-AD11-B0EB60B18ADA` was read back from the physical phone:
- Session created 18:37:43.836 UTC; microphone duration 30.716 seconds; completed true.
- Ask created 18:37:54.793 UTC; capturedWhileRecording true. Snapshot contains only the appointment statement, cutoff 4.118 seconds.
- Answer is completed, says Tuesday at ten, and references the existing saved source p1.
- Server Ask `10eb4364-b336-4b70-8570-ecfcb7832209` completed 18:37:57.840 UTC, first text 2.626 seconds, completion 2.847 seconds, 694 input/15 output tokens.
- The final saved transcript contains the purple-umbrella phrase, word timestamps 21.592–26.376 seconds into capture. Even using session creation as the earliest possible capture start, that speech begins after 18:38:05 UTC, over seven seconds after server answer completion. The phrase is absent from the answer's fixed source snapshot.
- STT `b35f5c6a-be8c-425c-b7ae-5eef5acfc5f4` completed at 18:38:17.599 UTC with 30.69625 seconds audio. No capture interruption or incomplete session.

This verifies real microphone capture, concurrent direct-Luna Ask, continued capture after completion, and persisted transcript/answer/source data. Existing simulator reopening/source UI checks cover rendering; no claim of measuring exact phone text-paint times. Read-only source inspection establishes source resolvability. Speaker labels remain best-effort. The first run's 6.207-second first-text latency remains an observed limitation; this checkpoint makes no consistent sub-three-second latency claim.

## Cost controls and QA grants

The base daily six-attempt STT allowance was exhausted before this checkpoint. Founder approved one extra attempt, accidentally consumed by a 10.18675-second recording (`545de383-afe2-4bcf-896d-1909728ade95`), then separately approved a replacement and the final focused run. All three attempts remain charged in the ledger. Estimated STT cost across them is $0.00444335, not verified billing; two real Ask calls were made. No automatic provider retries.

Administrative dated allowances and a unique-ID grant authorize only those extra attempts, expire at midnight UTC, and preserve lifetime/category spending caps, concurrency limits, credentials and prior request history. Grant IDs prevent duplicate grants on command retry. Hosted ledger tables were compared against pre-deployment backups and remained unchanged except the authorized grant records. HTTP health passed. Sixteen focused admission/admin/relay checks passed, covering persistence, expiry, duplicate refusal, base-policy preservation, separate Ask quota and monetary caps. No public grant endpoint exists.

Additional ignored evidence: `work/named-grant-tests.log`, `work/live-ask-phone-session.json`, `work/post-answer-phone-session.json`. Phone session exports remain local/ignored; private free-form speech is not copied into this document. Only the supplied synthetic test content is described here.
