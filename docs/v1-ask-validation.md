# Saved-conversation Ask — verified internal checkpoint

> Historical saved-session Ask checkpoint. Independent questions and per-session Q&A below predate the persistent main companion chat; its paid allocation is a historical grant, not an available balance. See [current state](current-state.md) for selected behavior and current evidence boundaries.

Checkpoint 3. Luna access was verified with a read-only model lookup. No comparative model evaluation is planned. A versioned 12-case synthetic functional suite is frozen in `Fixtures/ask-cases.json` before paid calls, with case-specific review criteria. The $5 total approved envelope remains; answers have a $2.50 allocation and $0.003 conservative per-request reservation.

Implementation: authenticated Ask WebSocket, bounded same-session input, Luna Responses with reasoning off and Standard processing, partial streaming, explicit cancellation/errors, source ID validation, saved Q&A with immutable source snapshots, and deletion with the session. Each question is independent; prior Q&A is not supplied to the model. Background Ask cancels. Capture remains independent and is not used for these tests.

Local evidence:
- 22 Python tests pass, including actual local WebSocket admission, repeated answers, budget/invalid-input rejection before provider calls, cancellation, revocation, invalid references, and additive ledger migration preserving usage/credentials.
- Existing native core tests pass; six new focused Ask lifecycle tests pass for snapshot/history persistence, deletion, background cancellation, invalid sources, interrupted reload, empty/oversized input, and initial storage failure without a pending answer or provider call.
- Actual iPhone simulator UI test streams a fixture answer, opens its source, relaunches and verifies saved Q&A. Screenshot exported and visually inspected. This is fixture evidence, not a real model response.
- Signed iPhone build passes; physical-iPhone Ask, source inspection and full-relaunch persistence passed (founder observed).

Ignored evidence: work/ask-backend-tests.log, work/ask-native-tests.log, work/ask-lifecycle-tests.log, work/ask-ui-tests.log, work/ask-ui-attachments/, work/ask-device-build.log.

Hosted evidence: deployed backend `ad07941`, then prompt correction `6226944`, to the existing internal service. SQLite backup integrity passed; budget, all six STT requests and all existing credentials were byte-for-value equal after additive policy migration. STT reservations remain $0.12. Fifteen bounded Luna calls (12 frozen cases plus three targeted checks after one utility failure) used 9,822 input and 487 output tokens: estimated $0.0012257, not verified billing; ledger Ask reservations are $0.045. Temporary QA credential revoked and exports removed. See [reviewed synthetic outputs](v1-ask-synthetic-evidence.md). Eleven of the initial twelve cases met the 3-second first-text target and all completed within 15 seconds. The original mixed-answer failure is preserved and its correction verified.

Native `2743de1` includes the storage-failure correction; six focused lifecycle tests and the signed physical-iPhone build pass. The subsequent commit changes only the server prompt, so it does not invalidate that native build evidence.

## Physical iPhone acceptance — September 25, 2026

After an explicit ready signal, launched `ai.voicecompanion.phone` on the paired iPhone 16 Pro (iOS 26.5.2), using the installed native build from `2743de1` and hosted backend `6226944`. The founder selected an existing saved conversation, asked a question with an answer in that transcript, and confirmed the response was correct and its Source link showed the matching passage. Then the founder fully closed the app from the app switcher, reopened the same conversation, and confirmed the question, answer and source link remained. This is founder-observed physical-device evidence; the agent did not independently view the phone screen or record the private question/transcript.

Content-free service telemetry corroborates a completed Ask at `2026-09-25T10:31:59Z`, request `43862508-d4c3-4aec-9a28-f0edd2c31e14`: first text 1.270s and completion 1.689s measured server-side, 1,883 input and 51 output tokens. Estimated model cost $0.0002138, not verified billing. Across the 15 synthetic calls and this phone call: approximately $0.0014395 estimated model cost and $0.048 permanent Ask reservations. No new transcription call was needed.

## Review and limits

Reviewed authentication/admission, budget-preserving migration, provider cancellation/cleanup, input and reference validation, immutable source snapshots, persistence and error states, and UI gating. The initial-save failure found in review was fixed and regression-tested. Diff whitespace checks pass; GitHub has no configured CI checks, so recorded local/hosted/device evidence is the verification basis. No new code changed after the tested native build and server prompt correction.

Checkpoint 3 acceptance is satisfied for the internal iPhone trial. Each question remains independent and limited to one saved transcript; speaker identity and citation faithfulness are not guaranteed by source-ID validation. Ask while recording, Jev routing, voice replies and cross-session memory remain later checkpoints. No provider calls were made merely to retest UI or persistence changes.
