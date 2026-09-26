# Recording subject and answer-quality follow-up

September 26, 2026. Scope: the two issues found in physical companion QA, using saved text and isolated synthetic sources. No new transcription or microphone test.

## Findings and changes

The original recording split “Project Juniper.” and “Prefers morning meetings.” into separate passages. Extraction attached the predicate to an unidentified speaker and omitted the subject-bearing evidence. The library-location claim also lost its project association. This was not proof that cross-source identity or correction thresholds should be loosened.

Recording extraction now explicitly treats passage boundaries as possible continuations, recognizes named projects/groups as subjects, and includes subject-bearing evidence. Account ownership remains prohibited. A narrator hint is discarded only when cited passages mix the proposed label with missing diarization; contradictory labels still fail strict parsing. The raw response is retained. This keeps best-effort labels from invalidating otherwise usable text without guessing who the user is.

For recordings, Jev receives multiple cited excerpts as continuous text for each bounded question, with the original structured source still present. The recording-identity verifier accepts an exact quote spanning supplied excerpts joined by one space. It still rejects invented words and does not promote an uncertain verdict. Independent Jev policies and thresholds are unchanged. Chunk size now accounts for prompt overhead, preserving the 10 KB target and exact source coverage. Chunk and judgment versions are advanced for cache/audit separation.

Companion prompt v2 answers neutral recording questions directly. Identity warnings remain required when the user asks whether an unidentified speaker's statement is about them. Prompt v1 and its immutable evidence remain historical fixtures, rather than being relabelled as current proof.

## Actual evidence

Five failed candidates are preserved in `Backend/fixtures/subject-continuity/failed-candidates.json`: incomplete subject context, inconsistent narrator metadata, cross-passage quote rejection, and conservative Jev rejection. No failed run was called a pass. Initial regression failures also identified prompt-size pressure; the bounded chunk fix passed the existing long-source coverage/correction tests.

The final isolated pipeline used exact replay of the unchanged initial extraction/judgments and fresh calls for the changed lifecycle and answer checks. It proved:

- Library location retained as an active named-project fact.
- Explicit community-center correction became active, with the library fact superseded and the same established project entity on both.
- Competing project names and an unrelated quoted first-person preference were not assigned to a named project or account owner by extraction.
- Neutral meeting-preference and Maya/swimming answers remained sourced without unsolicited ownership caveats.
- “Am I an endurance runner?” still explicitly explained that the recorded speaker was not identified as the user.

Saved real provider requests/responses replay through the actual writer, independent judgments and atomic store with exact request equality. Current answer instructions, request bounds and citation validity match recorded results. The prior 302-test regression suite passed, plus two new exact replay tests. Tests distinguishing historical prompts remain explicitly historical; current prompt evidence is separate. The workflow follows the [official prompt/evaluation guidance](https://developers.openai.com/api/docs/guides/prompt-engineering) while retaining this repository's stricter bounded-cost and real-path acceptance rules.

## Remaining limitation

**Complete split-subject retention did not pass.** Jev still rejected the short morning-preference fragment under the unchanged 0.90 gates. Its words remain in the transcript and are available to source retrieval, but that preference did not become a derived memory. The final evaluator reports this separately as `complete_split_subject_retention=false`; the original two-fact expectation was not converted to a success. The corrected location lifecycle and response wording are independently verified improvements, not a claim that every memory-quality issue is solved.

No existing user source is reprocessed, no deleted source is restored, and no stored unresolved claim is retrospectively promoted by these code changes. Broader recall and calibration work would need a separate representative evaluation, not more tuning to Juniper alone.

## Cost and deployment boundary

Across diagnosis and validation: 21 new provider calls conservatively reserved at $0.01 each, including all failed candidates. Final canonical profile usage is $2.79/$2.90, leaving $0.11. Exact replay did not call or charge providers. No audio run, additional allocation, threshold reduction or hosting upgrade occurred. These reservations are not invoices and are already covered by the global allocation.


## Internal deployment verification

Deployed `1d55b2083580ae216026232703c35f8c5d709a83` through Render deployment `dep-das04gnpn0mc73e9qa5g`, following merged PRs #70 and #71. The final scope guard preserves the existing personal-text judgment format; 28 focused tests passed, including exact recording-provider replay. Existing internal rollout authorization was used; the Starter hosting plan is unchanged.

A consistent predeployment SQLite backup was taken with no active provider requests. Postdeployment read-only checks confirmed schema 15, integrity/foreign-key checks, and exact equality of sources, claims, support, learning jobs, chat turns/dependencies/snapshots and indexing jobs against that backup. The previously deleted correction remains tombstoned with no payload, support, chat dependency or snapshot. No old source was automatically reprocessed.

All three health routes returned HTTP 200; learning and indexing were idle with no failures. Authenticated companion history returned six turns, unauthenticated access was rejected, and its temporary verification credential was revoked. Provider accounting stayed unchanged at the values above; no additional paid calls were needed. Runtime memory was approximately 352 MiB with zero cgroup OOM events. The initial verification script incorrectly expected JSON from the plain-text `/health` route; correcting that check required no service change.

These checks verify deployment and preservation, not a new physical-device or broad memory-quality evaluation. The short-preference retention failure above remains open. Existing unresolved claims are not retroactively repaired.
