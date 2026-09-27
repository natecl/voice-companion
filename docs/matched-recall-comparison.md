# Matched recall comparison — September 27, 2026

**Decision: do not enable notes-first yet.** Both paths completed the same nine questions with saved, source-linked answers. The existing indexed harness met the reviewed requirements in all nine; notes-first met them in eight and omitted one side of an unresolved disagreement. These are bounded case outcomes, not general accuracy percentages.

## What was compared

Main `4826c68`, unchanged production implementations: `IndexedMemoryRecall(multi_source=True)` versus `NotesFirstRecall`, both using the pinned local BGE embedding adapter, original-source indexing, Jev ranking, existing lifecycle/correction expansion, companion context assembly and GPT-6 Luna answers. Same seeded data, query and time per pair; separate databases/chats to prevent cross-arm history leakage. The semantic model ran offline in `work/semantic-venv` using `work/embedding-models`. This fixes the earlier lexical-only comparison limitation.

Six cases reuse `evaluate_notes_first` fixtures: final plan, omitted detail, uncertain vet diagnosis, supported personal context versus anonymous speaker, known cross-recording correction, and knowledge retained after recording deletion. Three additional controlled fixtures cover unresolved competing venue reports, bicycle/bike paraphrasing, and a 40-passage (~12KB) recording with two distant details. Notes for these stress cases are hand-authored fixtures, not new generation-quality evidence.

The original small cases and stress inputs were fixed before paid execution. For the conflict case, the intended behavior is to preserve both competing reports and explain the absence of a confirmed venue. Transport completion and keyword presence alone do not establish this; every answer and citation was manually inspected. An explicit cited-session coverage check was added to preserve the discovered regression in replay. `status=complete` in raw results means socket/persistence/source checks passed, not that answer quality passed.

## Results

| Case | Existing indexed harness | Notes-first |
| --- | --- | --- |
| Cedar corrected final plan | Thursday / garden pavilion, old plan cancelled | Same correct outcome |
| Detail omitted from lecture note | Hot weather common cause, original evidence | Same correct outcome |
| Vet uncertainty | No established diagnosis, no food change yet | Same correct outcome |
| Personal context and unknown speaker | Maya swims; marathon claim cannot be assigned to user | Same correct outcome |
| Birch cross-recording correction | Community center replaces library | Same correct outcome |
| Deleted Juniper recording | Correct retained location; recording unavailable | Same correct outcome |
| Unresolved Northstar venue disagreement | Mentions Riverside Park and botanical garden; no confirmation | Only mentions Riverside Park; still uncertain, but loses the alternative report |
| Bicycle/bike paraphrase | Courtyard racks behind entrance | Same correct outcome |
| Longer Orion recording | Friday 5 pm and OR-4821, with sources | Same correct outcome |

Both paths preserved saved answers after reopen and original source navigation. Retained citations correctly could not open deleted transcripts. No new audio capture/transcription or extraction was performed. This compares retrieval/answer paths on established synthetic state, not all background memory learning or real-world distribution quality.

## Failure diagnosis

The full indexed pool contains the two original venue reports. Jev marks both helpful (probabilities 0.99 and 0.51), so Luna explains the disagreement.

The notes-first pool contains note and original-passage versions of each report. Jev marks the competing botanical-garden report only topical, both as a note (helpful 0.40, topical 0.59) and as an original passage (helpful 0.33, topical 0.66). The existing usefulness selector excludes them. Luna cannot mention evidence it never receives.

This demonstrates sensitivity to candidate-pool composition and the helpful/topical decision boundary. It does **not** prove Jev is generally unsuitable or that a threshold reduction is the right fix. The shared prompt distinguishes answer-bearing information from generic absence of information; an explicit lack of venue confirmation is relevant to this particular question. Simply adding more note entries does not protect disagreement context.

Next implementation should preserve relevant disagreement/uncertainty without indiscriminately adding topical noise, keep bounded context, and reuse this failed response to reproduce the issue. Any changed Jev prompt requires new quality evidence including negative cases. Do not deploy the candidate, lower thresholds just to pass Northstar, or erase the failed output.

## Usage and timing

Logical provider-token usage across all nine questions (including exact reused responses):

| Path | Jev input/output | Luna input/output |
| --- | --- | --- |
| Existing | 12,173 / 1,341 | 10,173 / 335 |
| Notes-first | 12,320 / 1,382 | 10,038 / 326 |

No overall input-token reduction was demonstrated. The smaller notes-first answer context in the disagreement case is explained by lost evidence and must not count as an efficiency win. On the long case, notes-first reduced Jev input from 4,137 to 1,826 tokens, but this benefit did not translate into lower aggregate Jev usage in this small suite. Token counts are not an invoice or a claim about background inference savings.

Most timing measurements cannot be treated as paired live latency: exact cached requests intentionally bypassed network calls. Original provider durations are retained per response, with reuse labels. Two fully fresh pairs (conflict and long) are too few to establish a latency advantage, and the QA answer transport is nonstreaming. No first-token or production-speed superiority is claimed.

## Spending and reproducibility

Founder approved at most $0.30/24 new calls and a cumulative $5.30 ceiling. Actual new calls: **19 (12 Jev, 7 Luna)**. Seventeen logical requests reused exact prior or same-run responses. New attempt reservations: $0.20, not invoice cost; the $0.30 grant remains reserved with $0.10 unconsumed. The operator script limits each model to twelve calls; no automatic paid retries occurred.

The new operator-only allocation is recorded in `matched-recall-20260927-030.sqlite`, separate from the application's unchanged $5 envelope. The combined envelope is $5.30; combined reserved grants are $5.256868. This avoids changing the deployed service's startup policy contract or its daily quotas. Existing grants and charges remain intact. Allocation and attempt receipts are committed; the unused allocation is not silently moved into another task or refunded.

Committed evidence: `Backend/fixtures/matched-recall/{calls,results,budget,provision}.json`. Calls contain exact synthetic requests/responses; results contain source events, original usage and explicit reuse labels. The final replay reproduced all eighteen arms and the same notes-first conflict failure. Pure replay has no paid fallback.

```sh
PYTHONPATH=Backend work/semantic-venv/bin/python Backend/evaluate_matched_recall.py work/matched-replay-new --cache work/embedding-models --replay Backend/fixtures/matched-recall/calls.json
work/semantic-venv/bin/python -m unittest discover -s scripts/evaluations -p test_matched_recall_provider.py -q
```

The operator test verifies idempotent allocation, unchanged runtime ledger cap/charges, exact cache reuse, per-model call cap and no retry after an uncertain failure. A complete dry socket run preceded the paid screen. The initial system Python lacked the optional embedder; the existing isolated semantic environment supplied the pinned model without installation/download or changes to dependencies. No native UI, deployed service or product code was modified by this comparison.
