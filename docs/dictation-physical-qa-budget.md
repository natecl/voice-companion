# Bounded physical dictation QA funding

> Historical single-run QA funding and accounting. This document does not authorize another recording, answer, budget transfer or deployment; its original reservations remain part of the audit trail. See [current state](current-state.md) for selected behavior and current evidence boundaries.

Founder approved up to $0.04 from the existing budget for one short recording and one companion answer, including redistribution of transcription capacity. No overall cap increase, automatic paid retry, runtime reset or permission to deploy the unfinished dictation/personality PR.

Read-only preflight: runtime reservations 4,956,868 microUSD of 5,000,000. Transcription used its full 1,200,000 category cap; Ask used 2,923,868 of 2,950,000. Move exactly 20,000 unused microUSD from Ask to transcription: new category caps 1,220,000 / 2,930,000 / 850,000 (STT / Ask / Jev). Per-call reservations and daily limits remain unchanged. One STT plus one Ask reserves 23,000 microUSD; the $0.04 approval is an upper bound, not an instruction to consume the remainder.

`redistribute_dictation_policy` is an explicit operator action within a transaction, not an automatic startup allocation. It refuses active requests, unknown policy/global cap, insufficient donor capacity and mismatched approval metadata. An idempotent approval receipt preserves the change; all existing request charges remain untouched. Service startup recognizes the approved new split before an operator changes it, so restart will not fail due to policy mismatch. No credentials, recorded text or old usage rows are rewritten.

Local verification: 23 targeted admission, startup, budget and redistribution tests pass. The behavioral test opens a real SQLite ledger at the preflight amounts, reallocates twice without changing old rows, reopens through actual service startup, admits exactly one further STT reservation, rejects another for budget, and admits an Ask. Insufficient donor capacity rolls back. No live calls or production mutation occurred.

Delivery boundary: compatibility code can be merged independently of PR 99. Hosted deployment of this verified compatibility change still requires founder approval; only afterward apply the already-approved redistribution, inspect recording/Ask daily limits and relevant automatic-worker budgets, then wait for physical readiness. Do not start the phone check until all gates are clear. This does not fund a new notes or memory-learning evaluation.
