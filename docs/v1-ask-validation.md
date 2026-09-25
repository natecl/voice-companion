# Saved-conversation Ask — verification in progress

Checkpoint 3. Luna access was verified with a read-only model lookup. No comparative model evaluation is planned. A versioned 12-case synthetic functional suite is frozen in `Fixtures/ask-cases.json` before paid calls, with case-specific review criteria. The $5 total approved envelope remains; answers have a $2.50 allocation and $0.003 conservative per-request reservation.

Implementation: authenticated Ask WebSocket, bounded same-session input, Luna Responses with reasoning off and Standard processing, partial streaming, explicit cancellation/errors, source ID validation, saved Q&A with immutable source snapshots, and deletion with the session. Each question is independent; prior Q&A is not supplied to the model. Background Ask cancels. Capture remains independent and is not used for these tests.

Local evidence:
- 22 Python tests pass, including actual local WebSocket admission, repeated answers, budget/invalid-input rejection before provider calls, cancellation, revocation, invalid references, and additive ledger migration preserving usage/credentials.
- Existing native core tests pass; five new focused Ask lifecycle tests pass for snapshot/history persistence, deletion, background cancellation, invalid sources, interrupted reload, empty/oversized input.
- Actual iPhone simulator UI test streams a fixture answer, opens its source, relaunches and verifies saved Q&A. Screenshot exported and visually inspected. This is fixture evidence, not a real model response.
- Signed iPhone build passes; physical-iPhone Ask remains pending.

Ignored evidence: work/ask-backend-tests.log, work/ask-native-tests.log, work/ask-lifecycle-tests.log, work/ask-ui-tests.log, work/ask-ui-attachments/, work/ask-device-build.log.

Pending: hosted deployment/migration verification, 12 bounded Luna functional cases with semantic review and latency observation, then a physical-iPhone Ask/reopen/source check after founder readiness. No checkpoint merge until real paths pass. No provider calls are made merely to retest UI/persistence changes.
