# Notes-first companion memory

> Historical/bounded delivery document. The [September 28 product definition](product-source-of-truth.md#full-product-vision--september-28-2026) and [current gap audit](product-vision-audit-2026-09-28.md) govern the full vision and next proposed sequence. Older one-liners, exclusions and pending stages below retain their original checkpoint meaning.

> Historical delivery plan. For the implemented simplified memory path and verified internal deployment, read [current state](current-state.md), [foundation](simple-memory-foundation.md) and [rollout](simple-memory-rollout.md). Earlier pending stages, visible chat citations and deletion contracts below must be read with the later founder revisions.

Founder-authorized implementation, September 27, 2026. Preserve the exact one-liner and companion-first experience. This is a consolidation of the memory implementation, not a new product scope.

## Delivery and acceptance

1. **Searchable notes foundation:** index individual sourced note entries transactionally; existing notes migrate without generation. Preserve owner/revision/generation checks, pending/failed exclusion, deletion, and original passage references. Verify with exact saved generated notes and lifecycle regressions.
2. **Bounded recall candidate:** Jev ranks a bounded pool of notes, transcript fallbacks and relevant personal/retained evidence. Hydrate original passages with existing lifecycle and identity metadata; expand relevant corrections. Keep live/attached context and recent chat unchanged. Missing or failed notes cannot block direct transcript discovery. No summary-only truth or identity inference. Fail visibly on provider/budget errors; do not silently call a second provider.
3. **Thin personal layer and consolidation:** reuse supported user/profile-linked knowledge instead of creating a new profile database. Include only bounded relevant personal context with provenance; preserve relationships, interests and changing circumstances without mandatory categories. Keep nonpersonal retained knowledge separate. Reduce redundant learning/indexing only when the replacement preserves correction, temporal and deletion behavior; do not simply add a permanent parallel system.
4. **Matched answer QA and rollout:** compare real Jev/Luna answers on saved inputs with current behavior. Include omitted detail, uncertain diagnosis/routine, correction across recordings, attribution, retained knowledge and source opening, plus long-context bounds. Preserve failed cases and exact responses. Merge verified checkpoints; deployment remains a separate approval after backup. Founder-dependent physical QA waits for readiness.

## Checkpoint 1 evidence

Implemented schema18 `recording_note_index`, with one candidate per overview/item and title/heading context. Saving ready notes writes the index in the same transaction. Revision/enqueue/deletion clears prior entries. Migration indexes existing ready notes without regenerating them. Search joins current source, note state and generation, isolates owners, supports excluding the attached session and returns at most twelve entries. The maximum title+heading+item text fits the existing 2,000-character ranking input limit. This checkpoint does not connect the index to live companion retrieval.

48 focused tests passed on macOS/Python3.13: notes search/storage, source lifecycle, lexical retrieval and retained memory. Coverage includes schema17 migration, reopen, owner/exclusion, stale/failed/generation handling, revision replacement and deletion. The retention suite also ran actual local companion sockets with exact saved provider responses and inspected the three retained-answer scenarios.

Behavioral run: five recorded notes responses replayed through actual generation/storage (`work/notes-index-final`); then real persistent index queries for diagnosis, walking routine and homework returned saved note entries and valid original passage packets after database reopen. Inspected `index-results.json`; committed the synthetic receipt under `Backend/fixtures/notes-retrieval/index-results.json`. An initial behavioral check reused the comparison database after its intentional summary-omission mutation and correctly found no homework note; the final run uses fresh exact-replay notes. This was fixture isolation, not a production search change. Earlier seven-case comparison remains an evaluation of its own whole-note prototype, not a quality claim for this new entry index.

New paid calls: zero. No deployment or native UI change. Those storage checks alone do not establish Jev integration or answer quality; see the subsequent checkpoint below.

## Provider validation gate

Current TypeSafe introduction checked September27: typed Choice questions return probability distributions; independent questions share state. This supports the existing bounded candidate-judgment API shape, not a guarantee of ranking quality. Source: https://docs.typesafe.ai/introduction . Verify the exact request and recorded responses in the next checkpoint.

Founder-approved dedicated QA allowance: at most $0.15 for twelve calls (six Jev candidate rankings and six Luna answers), no automatic retries, subject to the unchanged global ledger ceiling. Reuse existing notes and transcripts; no new transcription or notes-generation calls. Cases: corrected plan, omitted detail, uncertain appointment, personal attribution, cross-recording correction, and retained knowledge after deletion. Approved in the subsequent founder message; provisioned as `notes-first-20260927-015`. If the global ceiling cannot fit it, stop rather than transfer unrelated allowances or exceed it.


## Checkpoint 2: bounded recall and thin personal context

Implemented `NotesFirstRecall`, selected by `VOICE_ENABLE_NOTES_RECALL=1` only when notes generation, memory rework and recall are enabled. Default remains off. The hosted service uses one selected recall implementation, not two model pipelines. No deployment has occurred.

Candidate capacity is reserved for four sourced note entries, four direct transcript candidates, two relevant supported personal/profile-linked claims, and two retained-knowledge candidates. One existing multi-candidate Jev request ranks the pool. Up to three nonduplicate useful candidates expand to original source passages and known correction relations, capped at eight final passages and 10KB of evidence metadata/text before the existing joint prompt bound. Large fallback passages use a bounded original span around query terms; offsets are retained. Coverage is explicitly partial.

The personal layer reads existing supported user/profile-linked claims with provenance. It creates no new profile database or extraction model. Ordinary recordings do not acquire user identity from their anonymous speaker labels. Retained nonpersonal knowledge has separate candidate space. Source revision/deletion and lifecycle validation remain deterministic. Invalid/provider/budget failures do not trigger paid retries; the existing companion protocol reports retrieval unavailable if recall fails.

Summaries are used to find evidence, not inserted as unverified facts into the answer prompt. Missing, failed or incomplete notes do not prevent transcript fallback. The current live/attached transcript and conversation history remain assembled by the existing companion context boundary.

### Real-provider evidence

Six actual local companion websocket exchanges used six Jev calls and six GPT-6 Luna calls through a budget-enforcing operator transport. Exact requests/responses are saved in `Backend/fixtures/notes-first/calls.json`; socket events and reviewed answers are in `results.json`. All six answers persisted after database reopen. Original cited passages opened; retained-memory citations correctly returned source unavailable. Exact-request replay on the final code reproduced every answer without a paid fallback.

| Frozen case | Observed answer |
| --- | --- |
| Cedar final plan | Thursday, garden pavilion; library cancelled |
| Detail deliberately omitted from the lecture note | Hot weather explains ice cream sales and swimming; original passage cited |
| Vet appointment uncertainty | No established diagnosis; food unchanged pending discussion of results |
| Personal context plus unknown speaker | Maya enjoys swimming; marathon statement cannot be attributed to the user |
| Cross-recording change | Birch now meets at community center, replacing library |
| Deleted recording | Juniper's corrected community-center location retained; original recording unavailable |

Notes in Cedar/appointment are exact prior generated outputs. The lecture omission is a hand-authored stress control. Personal/Birch claims are synthetic established-state fixtures, so this tests retrieval and source handling, not new extraction accuracy. Juniper uses the saved verified retained-memory fixture. This is a bounded acceptance screen, not a general accuracy or superiority benchmark against the full previous harness.

Jev provider round trips were 0.136–0.442 seconds; Luna's nonstreaming QA responses were 0.768–1.647 seconds. These are six observations with short fixtures, not production streaming-latency or cost guarantees. No microphone/provider transcription was rerun.

Budget receipt confirms twelve completed calls: $0.15 reserved, not actual invoice cost. Global reservations are $4.956868/$5. Funding used previously unreserved category headroom ($0.07 recording category and $0.08 Jev category), with allocation markers; existing grants, policy caps and daily counters were not reset or transferred. The dedicated QA allowance is exhausted. No automatic retries or new notes-generation calls occurred.

### Local integration and regression checks

35 targeted checks passed for recall, notes search, companion socket/context behavior, corrections and service startup, plus one operator-ledger check for idempotent funding, model call limits, cached exact responses and failed-call retry prohibition. A further real hosted-process check started with notes recall enabled, recovered chat and served authenticated history with no provider calls. Flag dependency validation fails closed.

New recall checks cover explicit opt-out before retrieval/spending, empty library, original-source hydration, notes/source mutation during judgments, correction expansion, context bounds, provider errors without retry and long-passage original offsets. Relevant old companion tests preserve live capture/follow-up behavior. Source navigation and reopen were additionally exercised by final provider replay. No native UI was changed.

Initial dry runs caught fixture-construction issues (serialized source key ordering and invalid test-claim overrides/kind); fixed before any live call. Operator tests exposed SQLite connection cleanup on rejected attempts; closed those connections and reran the affected test. Final deduplication avoids counting repeated evidence as multiple selected candidates and preserves exact paid requests/answers in replay.

Reproduce:

```sh
PYTHONPATH=Backend python3 Backend/evaluate_notes_first.py work/notes-first-replay-new --replay Backend/fixtures/notes-first/calls.json
PYTHONPATH=Backend python3 -m unittest Backend.test_notes_recall Backend.test_notes_search Backend.test_companion_service Backend.test_companion_context Backend.test_memory_related Backend.test_hosted_startup -q
python3 -m unittest discover -s scripts/evaluations -p test_notes_first_provider.py -q
```

### Consolidation boundary and rollout

The new read path is implemented and verified for these cases. The existing background writer, correction/identity lifecycle and retention storage remain shared because they supply the safeguards this screen exercised. We have not proven a replacement learning algorithm, retired the old recall implementation, or measured reduced total background inference cost. Keep the old implementation as rollback until internal rollout is accepted; remove it in a focused cleanup afterward. More aggressive writer simplification is separate from this verified retrieval checkpoint and must preserve retained knowledge.

For internal rollout: back up usage/memory databases, migrate schema18, enable the new flag on the existing Render plan, and verify startup/authenticated routes. No native rebuild is required for the unchanged protocol. Confirm sufficient already-approved runtime allowance before any founder check; do not use the exhausted operator QA grant for extra calls. Deployment requires separate founder approval; manual capture/chat acceptance waits for readiness. Roll back the flag to the prior recall path on failure; do not run schema17 code against the migrated database without a verified rollback plan.

## Subsequent matched gate: rollout held

The [nine-case matched comparison](matched-recall-comparison.md) includes real semantic retrieval on both paths. Existing indexed recall met nine reviewed cases; notes-first lost one side of the unresolved Northstar venue disagreement. The answer remained uncertain, but incomplete evidence violates the preservation gate. **Do not enable the candidate yet.** This later result supersedes the six-case screen as a rollout recommendation. Preserve the failed responses; diagnose candidate composition and usefulness selection before making further changes.
