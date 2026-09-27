# Notes-first companion memory

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

New paid calls: zero. No deployment or native UI change. Jev integration and complete-answer quality remain pending, not passed by these storage checks.

## Provider validation gate

Current TypeSafe introduction checked September27: typed Choice questions return probability distributions; independent questions share state. This supports the existing bounded candidate-judgment API shape, not a guarantee of ranking quality. Source: https://docs.typesafe.ai/introduction . Verify the exact request and recorded responses in the next checkpoint.

Proposed dedicated QA allowance: at most $0.15 for twelve calls (six Jev candidate rankings and six Luna answers), no automatic retries, subject to the unchanged global ledger ceiling. Reuse existing notes and transcripts; no new transcription or notes-generation calls. Cases: corrected plan, omitted detail, uncertain appointment, personal attribution, cross-recording correction, and retained knowledge after deletion. This is a request, not an approved or provisioned allocation. If the global ceiling cannot fit it, stop rather than transfer unrelated allowances or exceed it.
