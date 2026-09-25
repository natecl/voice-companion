# Saved-conversation Ask — verification in progress

Checkpoint 3. Luna access was verified with a read-only model lookup. No comparative model evaluation is planned. A versioned 12-case synthetic functional suite is frozen in `Fixtures/ask-cases.json` before paid calls, with case-specific review criteria. The $5 total approved envelope remains; answers have a $2.50 allocation and $0.003 conservative per-request reservation.

Implementation: authenticated Ask WebSocket, bounded same-session input, Luna Responses with reasoning off and Standard processing, partial streaming, explicit cancellation/errors, source ID validation, saved Q&A with immutable source snapshots, and deletion with the session. Each question is independent; prior Q&A is not supplied to the model. Background Ask cancels. Capture remains independent and is not used for these tests.

Local evidence:
- 22 Python tests pass, including actual local WebSocket admission, repeated answers, budget/invalid-input rejection before provider calls, cancellation, revocation, invalid references, and additive ledger migration preserving usage/credentials.
- Existing native core tests pass; six new focused Ask lifecycle tests pass for snapshot/history persistence, deletion, background cancellation, invalid sources, interrupted reload, empty/oversized input, and initial storage failure without a pending answer or provider call.
- Actual iPhone simulator UI test streams a fixture answer, opens its source, relaunches and verifies saved Q&A. Screenshot exported and visually inspected. This is fixture evidence, not a real model response.
- Signed iPhone build passes; physical-iPhone Ask remains pending.

Ignored evidence: work/ask-backend-tests.log, work/ask-native-tests.log, work/ask-lifecycle-tests.log, work/ask-ui-tests.log, work/ask-ui-attachments/, work/ask-device-build.log.

Hosted evidence: deployed backend `ad07941`, then prompt correction `6226944`, to the existing internal service. SQLite backup integrity passed; budget, all six STT requests and all existing credentials were byte-for-value equal after additive policy migration. STT reservations remain $0.12. Fifteen bounded Luna calls (12 frozen cases plus three targeted checks after one utility failure) used 9,822 input and 487 output tokens: estimated $0.0012257, not verified billing; ledger Ask reservations are $0.045. Temporary QA credential revoked and exports removed. See [reviewed synthetic outputs](v1-ask-synthetic-evidence.md). Eleven of the initial twelve cases met the 3-second first-text target and all completed within 15 seconds. The original mixed-answer failure is preserved and its correction verified.

Native `2743de1` includes the storage-failure correction; six focused lifecycle tests and the signed physical-iPhone build pass. The subsequent commit changes only the server prompt, so it does not invalidate that native build evidence.

Pending: physical-iPhone Ask/reopen/source check after founder readiness. No checkpoint merge until real paths pass. No provider calls are made merely to retest UI/persistence changes.
