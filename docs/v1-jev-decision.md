# Decision: defer Jev from V1

Founder accepted September 25, 2026. Continue with direct GPT-6 Luna and implement Ask while listening next. Jev is no longer a V1 delivery dependency. The one-liner and Proven, Better, New remain unchanged.

Why: Jev classified the frozen questions well (24/24, median 143ms), but Luna already understands these intents. Eight paired answer comparisons showed two useful improvements and one grounding regression, with median added first text 168ms. This small evaluation did not establish a reliable net benefit from an extra model and operational dependency. The grounding gate failed and is preserved as failed; deferral does not relabel it as a pass.

Keep [routing evidence](v1-jev-routing-evidence.md), [answer evidence](v1-jev-answer-evidence.md), and the closed unmerged [experiment PR #20](https://github.com/natecl/voice-companion/pull/20). Do not merge its runtime routing or evaluation infrastructure into the product. Preserve its charged ledger reservations and the $5 cumulative testing ceiling. The backend must remain compatible with the already-added Jev ledger category when returning to the direct baseline; retaining historical accounting does not enable Jev calls.

No further Jev tests or prompt retuning are required for V1. Direct-prompt improvements may be considered later for a specific demonstrated need; this decision does not authorize speculative prompt changes. Reconsider Jev when a concrete judgment (whether to retrieve context, update memory, or surface useful information) can demonstrably improve the product or avoid expensive work. Those remain hypotheses, not accepted next-slice features.

## Verification

Seven focused backend tests passed, including a new compatibility regression proving that retired Jev charges and credentials survive and direct Ask still admits requests. Final resource-cleanup adjustment passed that targeted test again. Hosted direct backend `0381158` started successfully; health returned 200. Budget, policies, all requests and credentials matched the pre-deferral SQLite backup exactly. Jev runtime code and hosted TypeSafe key are absent. No additional paid provider call was needed for this accounting/configuration change. Existing direct-Luna behavioral evidence remains applicable; its provider and native paths are unchanged.
