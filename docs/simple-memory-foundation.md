# Simpler memory foundation

Current status: checkpoints 1–3 passed their bounded acceptance and PRs 95–97 were internally deployed; see [rollout](simple-memory-rollout.md). Unified recall and source-scoped learning share the existing provenance/lifecycle store. This supersedes the strict notes-first candidate that failed the [matched comparison](matched-recall-comparison.md). Sections below preserve the chronological candidate, approval and QA record; their “pending” or “disabled” statements describe those earlier stages, not current rollout status.

## Outcome

Keep the companion grounded in what the user captured, with a small supported personal layer. Notes and transcripts are searched together. Notes help discovery; original passages supply evidence when available. Derived knowledge can survive ordinary recording deletion with an unavailable-source label. Anonymous speakers do not become the user.

The founder authorized simplifying **both background learning and recall**, not merely adding another retrieval adapter. Preserve uncertainty, explicit corrections, attribution, source revisions, owner isolation, and deletion behavior. Do not erase these safeguards to reduce line count. Do not claim the replacement is complete while the old learning machinery remains necessary.

## Delivery sequence

1. **Separate source verification from reconciliation.** Isolate extraction and independent source checks without changing prompts, metering, cache keys, or writes. Reuse the verified core in the simpler learning path. This is a behavior-preserving foundation, not the finished memory system.
2. **Unify evidence discovery and selection.** Search notes and transcripts together; deduplicate evidence before ranking. Keep relevant competing evidence instead of using Jev's single helpful/topical choice as a hard exclusion. Maintain bounded context, original citations, retained memories, and the thin personal projection. Compare against the frozen disagreement and other matched cases before rollout.
3. **Consolidate learning and storage ownership.** Implement the smaller derived-memory path using the source-local verification boundary. Personal facts and retained knowledge need explicit provenance; avoid generating a second general knowledge graph. Remove redundant orchestration only when correction, temporal qualification, uncertainty and retention behavior have replacement evidence. Preserve existing data and a reversible migration.
4. **Verify and switch one path.** Run saved fixtures first, then bounded live provider QA for changed requests, and the affected app flow. Only after acceptance and deployment approval switch the hosted writer/reader together. Retire superseded paths and flags after the rollback boundary is verified.

No UI expansion, voice identity, proactive participation, automatic backfill, or unrelated paid transcription is part of this slice. Existing source verification stays independent of Luna extraction; any changed model role needs its own evidence.

## Checkpoint 1 evidence

`memory_source_pipeline.SourceVerifier` now owns source-local extraction and verification. `EvidenceWriter` delegates to it, retaining reconciliation and commit behavior. No new tables, models, prompts or flags.

- `PYTHONPATH=Backend python3 -m unittest test_memory_evidence_writer test_source_verification test_memory_evidence_chunks`: 40 passed.
- `PYTHONPATH=Backend python3 Backend/evaluate_source_verification.py work/simple-memory-source-replay --transport /usr/bin/false --replay Backend/fixtures/source-verification/verified-calls.json`: 17 exact saved response replays, zero new provider calls. Actual writer executed through SQLite commit/reopen; morning preference survived, library became superseded by community center, anonymous recordings did not become profile facts, and frozen support/admission cases passed.
- The false transport prevents a cache miss from reaching a provider. This verifies refactor equivalence, not fresh provider quality or the future simplified learner.

## Budget and release gates

The previous matched-comparison allowance does not authorize new rework prompts; its Jev call sublimit is exhausted. Prepare exact new requests and a bounded QA proposal before seeking additional spend. No deployment is authorized by a code merge. Preserve failed comparison evidence and report any unmet acceptance criterion explicitly.

## Checkpoint 2 candidate: unified evidence recall

Implemented in the existing disabled `NotesFirstRecall` candidate, not a third hosted recall adapter. Its legacy class/flag name is retained until rollout cleanup. Discovery fuses transcript hybrid search, note references, supported personal references and retained knowledge. Notes resolve to original excerpts; repeated hits within one route do not multiply its vote. Jev sees each distinct excerpt once, without a second generated paraphrase competing against it.

The two strongest discovery results reserve context independently of Jev's relevance choice. Jev then orders additional helpful/topical candidates up to four selected excerpts, with existing correction expansion, eight-source and byte limits. Unrelated choices cannot add extra excerpts beyond that independent reserve. An oversized required reserve fails explicitly rather than silently discarding it. This is a bounded selection hypothesis, not a guarantee of complete recall. It can include irrelevant evidence; live QA must check abstention and distraction as well as disagreement retention. `available` means evidence was supplied, not that the question is answered by it.

Local evidence:
- 55 targeted unified/notes/search/context/retention tests passed, including existing retained-memory socket replay.
- The adversarial Northstar regression supplies a deliberately incorrect `unrelated` judgment for the competing report; both original sources survive, including the organizer's lack of confirmation. This is fault injection, not provider performance evidence.
- Nine frozen cases plus an unanswered ticket-price question executed through the real local companion socket, SQLite save and reopen with the pinned local semantic model and synthetic response transport. This verifies plumbing only, not answer quality.
- Exact saved-response replay cannot complete the changed answer context: it stops on a cache miss, with no paid fallback. Fresh bounded QA is required before merging or enabling this candidate. Earlier comparison evidence is preserved; reproduce the old candidate on its recorded commit, not this branch.

Proposed live QA: ten candidate cases, at most ten Jev and ten Luna calls, reuse exact responses when possible, no retries; reserve at most $0.25. Do not reset runtime allowances or deploy. Review corrections, omitted detail, veterinary uncertainty, personal attribution, retained/deleted sources, disagreement, semantic paraphrase and long-source coverage. Source citation/opening and persistence checks run in the harness. If the reserve introduces irrelevant context, assess answer abstention before accepting it. The smaller background learner and data migration remain subsequent checkpoints, not delivered by this read-path change.

## Approved checkpoint 2 QA result

Founder approved $0.25 / up to ten Jev and ten Luna calls, cumulative ceiling $5.55. `unified-recall-20260927-025` is operator-only; runtime quotas and the app's $5 startup envelope were unchanged. Source code under test: `9994a11` (subsequent changes only add QA tooling, evidence and documentation).

All ten cases completed through the actual local companion websocket, saved and reopened. Reviewed results:

| Case | Observed answer behavior |
| --- | --- |
| Corrected plan | Thursday at garden pavilion, library cancelled |
| Summary omission | Retrieved hot weather explanation from transcript |
| Appointment uncertainty | No established diagnosis; preserved the recorded qualification |
| Personal attribution | Maya swims; anonymous marathon speaker not asserted to be user |
| Cross-recording correction | Community center replaces library |
| Retained knowledge | Community center remembered; deleted recording unavailable |
| Northstar disagreement | Both Riverside Park and botanical garden retained; neither confirmed |
| Semantic paraphrase | Bicycle query finds courtyard bike racks |
| Long source | Friday 5 pm deadline and OR-4821 receipt both supplied |
| Absent information | Explicitly says ticket price is not given |

Twenty logical calls used **nine new calls (3 Jev, 6 Luna)** and eleven exact cached responses. New attempts reserved **$0.135 of the $0.25 cap**, not a claim of final invoiced cost. All attempts completed; no automatic retries. The unanswered question was a fresh Jev/Luna pair. The Northstar pair exactly matched previously successful original-evidence requests and reused those responses. This proves context recovery for that frozen case, not a new independent sample of model quality.

`Backend/fixtures/unified-recall/{calls,results,provision,budget}.json` contains synthetic-source evidence and receipts. Exact replay of all ten cases passed with no network transport:

```sh
PYTHONPATH=Backend work/semantic-venv/bin/python Backend/evaluate_unified_recall.py work/unified-recall-replay --cache work/embedding-models --replay Backend/fixtures/unified-recall/calls.json
```

Original citations reopened their source passages; retained citations returned `source_unavailable`. The answer context sometimes includes incidental excerpts (e.g. room-layout discussion in the long case). The answers ignored that noise in this sample; no claim of universally better relevance, lower cost, or faster answers is made. Local sockets and non-streaming QA transport do not establish physical-device behavior or production latency. No deployment performed. Learning/storage consolidation remains the next checkpoint.

## Checkpoint 3 candidate: source-scoped learning

Implemented as `EvidenceWriter(source_scoped=True)` using the existing derived-claim store, provenance and atomic correction/deletion machinery. Default remains false; the unified feature switch now selects both this policy and unified recall, but remains off in the deployed service. No schema migration or copied second memory store is needed. The candidate uses deterministic overlapping chunks and does not consolidate duplicate claims across recordings. Compatible additions remain separately sourced observations; only non-addition relationships proceed to cross-source identity checks. Corrections still require independent support, identity, relationship, current-applicability and atomic snapshot checks. Unknown or truncated candidate sets remain conservative.

An attempted optimization that trusted the extractor's change hint failed completed-change regression tests: the independent relationship check can detect corrections extraction missed. That optimization was removed. Do not reintroduce it. The remaining optimization checks semantic relationships before identity and skips identity only for independently accepted compatible additions. Contextual original excerpts remain available for correction identity.

Local verification: 53 source-scoped, original-writer, verification and chunk tests pass. Behavioral guards cover current/historical/future changes, uncertain identity, same-source correction chains, source validity and surviving attribution uncertainty. A mixed-property case proves a swimming correction leaves an unrelated apples preference intact. Supported daughter/colleague reports remain separate without asserting those people are identical. Legacy ordered-call replay tests remain on the old writer; they are not evidence of the new call order.

Actual recording-writer replay consumed ten exact saved responses without new spending, retained the first preference/location, then stopped before a missing exact response for the narrower Luna identity request. This request verifies the library-to-community-center correction, with the unrelated morning preference removed from identity matching. Provider acceptance is pending; no merge or deployment is justified yet.

Concrete QA: `Backend/evaluate_source_verification.py --source-scoped` exercises the writer, correction, persistence, frozen negative verification cases, then recording deletion and retained-memory hydration. Using `/usr/bin/false` as transport forbids paid cache-miss fallback. Proposed approval: repurpose at most $0.05 from the unused $0.115 unified-recall QA allocation, maximum two Luna and two Jev calls, no retries; preserve the $5.55 combined ceiling and runtime quotas. Do not provision or spend the reallocation before approval. Existing extraction/support responses are reused; Sol verification is unchanged.

This simplifies orchestration, not the physical database schema. Historical compatibility code and old hosted defaults remain until replacement acceptance and separately approved rollout. Existing normalized provenance/identity/correction tables stay to preserve their tested guarantees; further table removal is not assumed necessary for the first slice.

## Checkpoint 3 verified result and rollout boundary

The founder approved repurposing $0.05 from unused unified-recall QA, without increasing the $5.55 combined ceiling. The operator reserves that child grant inside the parent ledger before any call, preventing the same allowance from being spent twice. It allows at most two Luna and two Jev calls, with no automatic retries. One new Luna identity call completed, reserving $0.02; fifteen exact responses were reused. These are reservation bounds, not invoices. No new Sol call or runtime quota change occurred.

The actual source-scoped writer retained morning preference and library location, then independently verified and applied the community-center correction. The morning preference remained active, the library claim became superseded, and corrected/original claims shared the verified identity. No recording became an account-owner profile fact. Reopen matched stored results. Named-family and student-continuity support passed; negation, unknown-owner, quoted-person and future-metadata negative gates retained their expected outcomes. Deleting both recordings retained eligible derived knowledge and correction state; hydrated citations explicitly report original source unavailable.

Evidence: `Backend/fixtures/source-scoped-learning/{calls,results,provision,budget}.json`. Exact-response replay passes without network fallback:

```sh
PYTHONPATH=Backend python3 Backend/evaluate_source_verification.py work/source-scoped-replay-new --transport /usr/bin/false --replay Backend/fixtures/source-scoped-learning/calls.json --source-scoped
```

Final integration: 87 targeted checks pass, including actual local hosted process startup/history with the unified switch enabled. The switch requires independent source verification and constructs the same writer policy exercised above; the old disabled-switch behavior remains available for rollback. No new public API or app UI is introduced. The one-store approach retains existing provenance/correction tables; it simplifies orchestration without rebuilding or duplicating the database. No broad claim of faster learning or long-recording semantic quality follows from this short fixture.

### Internal rollout procedure (subsequently approved and completed)

Read-only preflight found deployed schema 17, nine live sources, ten completed/eight obsolete learning jobs, no queued learning jobs, and one ready note. The actual service process has notes, rework, independent verification and retained memory enabled; unified recall remains disabled. SSH shell variables differ from the serving process and must not be used as rollout-state evidence.

1. Confirm the service is idle; make consistent SQLite backups with integrity checks and a manifest. Preserve usage ledgers and existing data.
2. Deploy the verified merged revision on the existing Render tier/disk, preserving all other configuration. Schema 18 adds the already-tested notes search index; verify old rows and ready-note indexing after migration.
3. Enable `VOICE_ENABLE_NOTES_RECALL=1` to select unified retrieval and source-scoped learning together. Keep provider budgets, recording/Ask quotas and existing notes-generation limits unchanged; no automatic re-learning/backfill.
4. Verify health, authenticated history, storage integrity, selected configuration and job state. No new provider spend is authorized by rollout approval. If a paid or founder-assisted check becomes necessary, stop for its specific allowance/readiness.
5. If rollout fails, turn the unified switch off while keeping schema-18-compatible code. Do not restore stale usage ledgers or roll an old schema-17 binary over the migrated database. Preserve failure evidence. Remove obsolete compatibility code only after the internal rollback boundary and acceptance are established.

The founder subsequently approved this rollout. Deployment and post-deployment checks are complete; see [rollout evidence and limits](simple-memory-rollout.md). Earlier candidate statuses above describe their historical checkpoints.
