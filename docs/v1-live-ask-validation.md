# Ask while listening — physical-device acceptance pending

Checkpoint 5 starts from verified main `5d7437c`; Jev deferral is merged in PR #21. Direct Luna provider/settings and hosted runtime remain unchanged. Native changes allow one Ask while recording, snapshot transcript passages before sending, persist its cutoff and interim-text caveat, and keep capture/answer controls and error states independent. Source snapshots stay fixed across later speech and transcript revisions. Backgrounding cancels Ask while supported background recording continues. Ask remains disabled during connection/finalization/replay and before text arrives.

UI places Ask before the growing transcript, with recording controls kept in the existing fixed bottom bar. Each answer shows the received-transcript cutoff, excludes later speech explicitly, and marks provisional source text. Question/answer history still belongs to the selected session; old saved answers decode without the new optional metadata. No change to backend request shape, prompt, provider, model, budgets, or recording duration.

Verification:
- 19 focused native tests passed: six existing saved-Ask cases, seven recording lifecycle cases, six new live-Ask cases. New cases exercise real controller/store behavior with controlled streams: immutable snapshot despite correction/later speech, Stop without cancelling Ask, cancellation without stopping capture, duplicate Ask rejection, independent failures, background cancellation with ongoing recording, and saved reopening.
- Both simulator UI tests passed: existing saved Ask/relaunch and new Ask during fixture recording, cutoff rendering, independent Stop, and source inspection. Exported screenshot visually inspected. These are synthetic UI fixtures, not microphone/provider proof.
- Signed physical-iPhone build passed; no provider call needed for build/UI checks.
- Actual local WebSocket integration passed: simultaneous audio and Ask, cancel Ask, then deliver more audio and finalize STT. Exactly one synthetic STT stream remained alive; no external provider calls.
- Diff whitespace check passed.

Ignored evidence: `work/live-ask-core-tests.log`, `work/live-ask-ui-tests.log`, `work/live-ask-ui-attachments/`, `work/live-ask-device-build.log`, `work/live-ask-relay-test.log`.

Pending founder-ready physical-iPhone QA: start a short recording, speak a specific fact and wait for transcript, ask about that fact while recording remains active, speak additional words after the Ask, verify capture continues, stop and reopen the session/Q&A, and inspect the fixed source. Use one short session and one answer; no new comparative model testing. Confirm available daily allowance before starting. Do not merge until the actual simultaneous phone/provider path is verified.
