# Notes-first retrieval comparison

September 27, 2026. Offline evaluation against main `531d6fb`. This checkpoint adds an evaluation and evidence only; it changes no app, service, production data, provider role or deployment.

## Decision supported by this screen

Notes are a promising discovery layer for existing recordings. They are **not yet a proven replacement for the memory harness**. Recommend evaluating a smaller retrieval path: current conversation → relevant notes → original transcript evidence, with direct transcript fallback and separate retained knowledge. Keep the deployed path until the candidate earns replacement through matched answer and lifecycle QA.

Do not delete the existing correction, attribution or retention machinery based on seven retrieval queries. A compact implementation must still distinguish proposed versus final plans, one person's words versus the account owner's identity, and deleted recordings versus retained learned knowledge. This recommendation is not an implementation or migration approval.

## Method and provenance

`Backend/evaluate_notes_retrieval.py` runs five exact recorded Luna notes responses through the real notes generator/storage, then compares seven predefined question/required-passage cases in a shared corpus. The inputs cover conversations, a lecture, a vet appointment, reflection and an explicit plan correction. Outputs originate from the earlier paid notes screen in `Backend/fixtures/recording-notes`; no fresh provider calls occur.

The baseline calls real `memory_hybrid.retrieve` with no embedder: **lexical candidates only**, before final ranking/related-evidence expansion. The evaluation-only notes candidate uses the same FTS5 tokenizer, query terms and OR matching, selects up to three notes, and expands their cited original passages through real context hydration. Both cap results at twelve passages. No equal token-budget claim is made: context bytes are reported, and whole-note expansion can use substantially more evidence. Neither route generates new answers.

Required passages were chosen from the transcripts before inspecting retrieval output. Success means all specified evidence reached the packet, not that an answer was correct. For Cedar, p3 is required because it explicitly confirms the replacement as final; p2 only proposes it. The baseline can retrieve p2 while still failing this stricter evidence-completeness criterion.

## Observed results

| Question | Current lexical candidates | Notes + original passages |
| --- | --- | --- |
| When are Alex and Jordan meeting? | Required evidence present | Present |
| Who will send the agenda? | Present | Present |
| What explains ice cream sales and swimming? | Present | Present |
| Was homework assigned? | Present | Present |
| Does the dog have a confirmed diagnosis? | Present | Present |
| Is walking before class a decided routine? | Present | Present |
| Where will Cedar meet? | Final confirmation p3 missing | Present |

Aggregate: 6/7 versus 7/7. This is a diagnostic on five tiny synthetic recordings, **not an accuracy benchmark against the full deployed memory system**. Semantic retrieval, related-evidence expansion and Jev ranking might change the baseline result.

Manual inspection of the saved notes confirmed that this set preserves the unconfirmed diagnosis and undecided walking routine; the reflection says “the speaker,” not that the recording owner is identified. The correction note connects Cedar to the final Thursday/garden-pavilion plan and excludes the quoted spam instruction. This is summary inspection, not a new answer-generation or general prompt-injection guarantee.

Across the seven questions, original evidence text totaled 1,029 bytes for lexical candidates versus 1,908 bytes for notes expansion, excluding metadata and note text. Retrieving whole notes therefore did not demonstrate cheaper answer context; tighter passage selection needs evaluation.

A separate deliberately compressed, hand-authored lecture note omits the ice-cream/swimming example. Direct transcript retrieval finds the example; notes-only discovery misses it. Even finding that note via “correlation” cannot expand the example because its passage is no longer cited. This control establishes a failure mechanism, not the measured frequency of Luna omissions. Direct transcript fallback must cover omitted details; linked-passage expansion alone is insufficient.

## Lifecycle and source checks

The candidate exercised real storage/hydration: owner isolation, explicit memory opt-out, opening original cited passages, source revision invalidation, rejection of stale citation references, and removal of deleted notes all passed. These are prototype checks, not a production integration claim.

Separately, `evaluate_retention.py` replayed the current production companion socket/context/answer path with exact saved Jev/Luna responses and retained-memory state. All three answers persisted after reopen:

1. Correctly recalls Project Juniper's replacement location, community center instead of library.
2. Declines to quote exact words from a deleted transcript.
3. Declines to treat a project's meeting preference as the user's personal preference.

Retained citations correctly cannot open the deleted recording. This baseline uses previously learned synthetic state; it does not rerun extraction. The notes candidate cannot recover those facts from deleted notes under today's storage contract. Retaining learned knowledge independently is still necessary for the founder-approved deletion behavior. Keeping deleted notes would be a separate design decision, not an incidental fallback.

## Reproduce and inspect

Use a fresh output directory for each run:

```sh
PYTHONPATH=Backend /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 Backend/evaluate_notes_retrieval.py work/notes-comparison-new
PYTHONPATH=Backend /Library/Frameworks/Python.framework/Versions/3.13/bin/python3 Backend/evaluate_retention.py work/retention-comparison-new --replay Backend/fixtures/retained-memory/calls.json
```

Committed evidence: `Backend/fixtures/notes-retrieval/results.json` includes selected notes, references, missing passages, bytes and controls; `retention-summary.json` includes replay answers. The replay summary's historical reservation total is not new spending. New paid calls: **zero**. No microphone, physical phone or UI check was necessary for this backend-only evaluation.

Local receipts: `work/notes-comparison/final` and `work/notes-comparison/retention`. The first candidate harness run failed because it called a low-level hydrate helper with the wrong signature; it was corrected to use the actual public selection path and rerun. No app defect or provider retry was involved.

## Remaining evidence before replacement

A follow-up candidate needs matched end-to-end answer QA with long recordings, omitted details, paraphrases, cross-recording corrections, unresolved conflicts, identities, temporal qualification and retained knowledge. Bound token use and measure real answer latency/cost; this screen establishes neither savings nor latency improvements. Jev's value for notes reranking remains untested here. Use a separately approved allowance if new model requests are necessary; this screen spends none of the notes-rollout allowance.
