# Multiple independent recordings in one answer

September 26, 2026. Opt-in backend checkpoint 5H; no hosted rollout or native UI change. `IndexedMemoryRecall(..., multi_source=True)` can select up to three independently useful passages, then expand their linked corrections/conflicts. Existing default selection remains unchanged. Canonical storage, identity, deletion and temporal rules remain independent of model usefulness ranking; no source is erased by a ranking decision.

## Selection and limits

`memory_multi_ranking.py` supplies Jev 1.13.0 with a bounded shared candidate pool and one usefulness question per passage (`memory-usefulness-multi-v4`). It distinguishes concrete evidence from generic topic overlap and unrelated text. Multiple useful passages can survive without competing for a single winning slot. Unknown speakers and earlier states can remain useful without becoming verified user facts or current truth.

At most twelve candidates, 2,000 characters per passage, 28,000 serialized request bytes; excess input fails explicitly. At most three initial passages, 10,000 serialized selected-evidence bytes, and eight final sources through the existing Ask decoder. Correction expansion is never silently truncated. These are bounded retrieval results, not an exhaustive library answer. Semantic coverage remains separately qualified. This checkpoint exercises lexical retrieval end to end; prior semantic/fusion evidence is unchanged.

## Failed experiments and diagnosis

All original frozen acceptance sets were preserved. `Backend/fixtures/multi_source/failed-role-v1.json` dropped earlier-state and anonymous first-person evidence; v2 recovered those but dropped the medicine source from a compound question; v3 included a generic veterinary talk with no medication schedule. These are failures, not accepted limitations. Each was one versioned, bounded live batch, with no identical paid retry.

V4 supplies the other candidates in shared context, so relevance judgments can distinguish concrete answer evidence from generic discussion. This passed all seven development cases and five held-out cases: multi-topic, comparison, change, unknown speaker, uncertain identity, unrelated query, quoted instruction injection, commute changes, anonymous student, different named person, dietary restriction, and family details. This small synthetic screen is evidence for this integration, not a general accuracy guarantee.

## Behavioral QA

Local environment: Python 3.13 on the development Mac. `python3 -m unittest discover -s Backend` passed 263 tests before adding three socket checks; targeted `test_multi_ranking.py` then passed seven tests including those additional real-socket checks. Recorded role responses are matched against the current request contract. Socket checks cover citation delivery, source deletion while answering and unavailable memory. Shared ledger tests exercise idempotence, old-caller caps and atomic allocation failure.

Live environment: isolated scratch code and synthetic SQLite stores on the existing Render host, without replacing production code or processing real recordings. `evaluate_multi_ranking.py` runs one bounded batch; `--heldout` runs the frozen held-out batch. `evaluate_multi_answers.py` ran the actual SQLite → indexed retrieval → Jev → Luna streaming path. Evidence: `Backend/fixtures/multi_source/{answers,ranking-calls,multisource-role-v4,multisource-role-v4-heldout}.json`.

Observed answers:

- Lena's peanut allergy plus Biscuit's antibiotic every twelve hours, citing both correct recordings and excluding generic distractors. Recall 0.213 seconds.
- Lena's violin hobby compared with Marco's soccer hobby, citing both recordings. Recall 0.155 seconds.
- An unrelated haiku request received no personal memory or memory citation. Retrieval 0.003 seconds, no Jev call required.

No unchanged STT, microphone, native build or physical-device claim is made here. GPT-6 Luna's existing answer model and personality prompt are unchanged. No automatic paid retry is enabled.

## Authorized cost accounting

Founder approved an additional $0.20, total profile/rework cap $2.40. The existing global Ask category could not accommodate all $0.20, so provisioning reserved $0.10 each from the existing Ask and Jev categories, atomically and idempotently, without raising global/category caps or removing prior reservations. Old budget callers retain prior caps. Canonical ledgers are `/var/data/voice-companion/{usage,memory-budget}.sqlite`.

This gate used ten calls: five role batches (three failed development revisions, successful v4, held-out v4), two actual recall judgments and three Luna answers. Conservative reservation $0.10; canonical total now **$2.28 of $2.40** (88 Luna and 140 Jev calls), leaving **$0.12**. These are reserved estimates, not invoice totals. An accidentally omitted `--heldout` argument was rejected before inference by the duplicate-attempt guard; it incurred no additional provider call.

## Remaining work

Hosted model/resource acceptance and runtime wiring, bounded chat/attachment context, persistent main chat, recording-library connections, approved rollout and physical acceptance remain. Broader language/noisy-transcript/long-query quality is not established by these concise English synthetic cases.
