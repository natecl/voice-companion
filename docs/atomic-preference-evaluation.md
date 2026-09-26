# Atomic verification evaluation — not approved for production

September 26, 2026. Founder approved up to $0.30 for a bounded follow-up to the [context experiment](preference-context-evaluation.md). This checkpoint delivers reproducible evaluation evidence, not a fix for the open retention defect.

## Method and outcome

The candidate independently classifies transcript support, expression mode and reported temporal status. Application code compares those classifications with the proposal using the existing 0.90 gates. It preserves raw source text and never treats Luna's proposal as evidence. These tests use hand-authored candidate proposals; they are not end-to-end extraction, identity or memory-write acceptance.

Version 1 passed 9 of 10 development/control cases: it recovered the split person statement and both complete-sentence controls, preserved the project location, accepted pet/family examples, and rejected competing subjects, an unrelated quotation, a historical contradiction and a hypothetical. It still rejected the original split project preference: support 0.77, despite modality 0.99 and temporal status 1.0. This is not a passing fix.

Version 2 clarified conversational fragments and group shorthand. It worsened support judgments, failing the project and person cases and rejecting the previously accepted location. It was rejected. Both versions and all responses are preserved.

Version 1 was then evaluated on six cases prepared before the development runs. Student and parent positives passed; negation, future-as-current and topic-change negatives were rejected. A tentative plan did not pass the expected future-status gate (0.62). That case's phrase “might join” admits an uncertain temporal reading, so its annotation needs review before calibration; the original failed expectation remains preserved rather than relabelled as a pass. Five of six passed under the original labels. This small synthetic set cannot establish a general error rate or probability calibration.

## Decision

Neither candidate replaces the deployed verifier. No thresholds were lowered, user sources rewritten, missed facts silently promoted, or deleted context restored. No additional transcription or physical-device test was needed for this isolated backend evaluation. A writer-path test would be required for any eventual accepted candidate; it was not run for these failed candidates.

Stop prompt iteration on the Juniper example. The useful next decision is whether to evaluate a different independent entailment verifier for factual support while retaining Jev for bounded modality/time and lifecycle judgments, or undertake a larger, carefully labelled calibration study. A different verifier must use original source evidence and pass positives, misattribution negatives and lifecycle checks. Neither option is implemented or claimed effective here; do not replace independent verification with Luna accepting its own extraction.

## Accounting and validation

26 new Jev calls reserved $0.26; $0.04 of the approved $0.30 remains. Cumulative canonical QA reservations: Luna 121/$1.21, Jev 195/$1.95, total $3.16/$3.20. These are conservative reservations, not invoices. No paid retries. Saved requests replay offline.

`PYTHONPATH=Backend python3 -m unittest test_atomic_preference test_preference_context test_subject_continuity test_rework_budget test_companion_runtime` passed 14 tests. Exact replay reproduces the failed outcomes and retains the deployed location lifecycle. An initial fixture-packaging script failed before copying saved files; correcting that local script required no model calls. Passing tests here establish reproducibility, not completion of the retention fix.

Budget recognition code from PR #74 was deployed as `a7f43b073b5c17d3cb359577ea123966859bb44c` before operator provisioning. All three hosted health routes returned 200; learning/indexing were idle without failures. Global reservations after provisioning were Ask $2.879, Jev $0.753 and STT $0.340, total $3.972 within the unchanged $5 cap. Prior reservations remain intact. The evaluation allowance is opt-in; hosted learning does not gain automatic spending permission from this QA approval. The earlier hosted learning allowance remains exhausted.
