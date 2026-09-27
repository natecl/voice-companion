# Current memory-system audit

> Dated research/audit record. Preserve its findings and uncertainty; it does not describe the current deployed stack or authorize changing it. Read [current state](current-state.md) for adopted decisions, subsequent fixes, rejected candidates and remaining limits.

Audited September 26, 2026. Code baseline: `85e72cd8dd630c529b9fc7a043e7cc0b9cc5f229`, with documentation through `c3b8e9a`. The deployed service reports that same implementation, schema 3, and all memory/personal flags enabled. PR 31 is draft and unmerged; deployment is an internal trial, not acceptance. This audit changes no application code or deployed configuration.

## Verdict

The source-storage and lifecycle foundation is useful and worth retaining. The system is not yet a reliable personal memory harness: uncertainty can become a current claim, identities are inconsistently represented, retrieval can miss relevant evidence before Jev sees it, and an ordinary input-size failure can stop all background learning. These are application-design issues as well as model-quality issues. Another round of prompt changes alone is not an adequate repair plan.

## Current path

1. Native app persists a session and stages final transcript passages or an explicitly authored personal note in a durable owner-scoped outbox. Recording identity remains unknown.
2. Authenticated `/memory` accepts an idempotent source revision, returns a sync acknowledgment and queues learning. Sync success is not proof of successful learning.
3. Background writer sends the entire bounded source to Luna (maximum eight proposed memories), Jev checks textual support, and another Jev batch assesses attribution, modality, expiry and relation to existing claims.
4. SQLite commits accepted claims and their supporting source passages. Profile is a query over user/related claims, not an independent biography.
5. Ask retrieves lexical/recent candidates, Jev applies a relevance gate, and Luna receives selected evidence with citations. Personal-note source text is displayed separately from the verified claims given to the model.

Typical nonempty learning path: one Luna extraction plus two Jev calls. Recall with candidates: one Jev call plus one Luna answer. Work happens after session finalization, not continuous profile updates during speech. These calls are bounded and metered, not free.

## Findings, in priority order

### 1. High — unresolved corrections become new active facts

**Confirmed from saved real output and a local replay.** `select_claims` defaults every accepted candidate to `relation='new'`. If update/duplicate fails its threshold, or the relation is conflict, that default remains. `commit_claims` then creates an active claim. No conflict/possible-correction state reaches recall. The real named Maya correction scored .88 for update, below .90; the replay produced a new claim with a different subject. Both swimming and tennis remain active.

Evidence: [writer](../Backend/memory_writer.py), especially `select_claims` lines 36–95; [store](../Backend/memory_store.py), `_write_claim` lines 296–341; physical failure in [checkpoint evidence](personal-profile-recall.md).

**Repair:** separate support for a statement from confidence that it is the current truth or a replacement. Preserve an unresolved relation with its candidate targets and sources. Do not turn uncertainty into an authoritative active profile fact. Resolution stays internal; this does not require a memory approval inbox. Retest actual correction persistence and downstream answer behavior.

### 2. High — no consistent entity-resolution contract

Personal related subjects hash session ID, relationship and name, so the same daughter begins with a different subject ID in each note. A successful update judgment copies the old ID to the new claim. By contrast, ordinary named subjects hash only a normalized name, so different people named Maya can share a key. Name/relationship survive primarily inside prose and cached extraction, not as a durable structured entity record. Matching same-name keys does not prove identity.

Evidence: [profile identity](../Backend/profile_identity.py), `profile_subject` line 31; [writer](../Backend/memory_writer.py), `subject_key` line 17 and relation assignment line 85. Local probe confirms ordinary normalized names share a key; it does not claim a new live false merge occurred. Prior unshipped experiments did falsely accept an ambiguous other-person case.

**Repair:** a small owner-scoped entity/mention representation with source-backed names, relationship qualifiers, unresolved links and explicit distinction evidence. Stable IDs identify established entities; merely creating IDs does not establish that mentions refer to the same entity. Keep resolution separate from fact replacement. Jev can assess bounded evidence, but code must prevent unsupported transitions. Validate recordings and personal notes under the same identity policy.

### 3. High — a valid synced source can stop the learning worker

**Reproduced locally without provider calls.** Source admission accepts approximately 60 KB, but the entire serialized extraction request is capped at 16 KB. A roughly 21 KB synthetic source was accepted; extraction rejected it before inference; `MemoryWorker.run` returned after that error, leaving the following small source queued. This halts learning across the worker's owners until restart/operator intervention. `/health` still reports HTTP readiness independently of worker state.

Evidence: [source limits](../Backend/memory_store.py), `validate_source`; [extraction](../Backend/memory_models.py), `extraction_request` line 34; [worker](../Backend/memory_writer.py), `run` line 162; [health](../Backend/relay.py), `authorize`.

**Repair:** align admission with processable bounds or introduce bounded, context-preserving batches. Quarantine a bad individual job; reserve a global halt for global failures such as exhausted spend or unavailable credentials. Expose worker liveness, backlog and failure causes. Preserve no-blind-paid-retry behavior.

### 4. High for a growing library — candidate retrieval loses evidence before Jev

**Reproduced locally.** An older bird-sketching preference plus nine newer unrelated personal facts caused a paraphrased creative-weekend question to omit the relevant fact entirely. Jev cannot recover a candidate it never receives. A separate 52-claim fixture showed that the 50-item profile pool used for corrections omitted an older target before related-target ranking.

Evidence: [recall](../Backend/memory_recall.py), `profile_shortlist` line 54 and `combined_shortlist` line 90; [writer candidate pool](../Backend/memory_writer.py), lines 126–135; [profile query](../Backend/memory_store.py), `profile` line 404.

**Repair:** relevance/identity-aware lookup before applying small result limits. Evaluate lexical plus semantic candidate retrieval on held-out paraphrases; do not choose a vector database merely by fashion. Keep ranking separate from deciding whether evidence is admissible. Test unrelated-library growth and older correction targets, not only small positive examples.

### 5. Medium — one policy serves several different Jev decisions

Support, modality, attribution, replacement and recall all use .90 probability/.60 confidence. Recall preserves initial candidate order; Jev filters rather than reranks. Support uncertainty collapses to unsupported in the operational decision. Cached responses preserve the original score, but the active memory state does not preserve its full uncertainty meaning. All questions are currently Choice; Score/Noul are not used.

Evidence: [writer acceptance](../Backend/memory_writer.py), line 13; [support parser](../Backend/memory_models.py), line 88; [recall selection](../Backend/memory_recall.py), lines 133–145.

**Repair:** define policies by consequence and measure them with representative labels. Ranking evidence, withholding unsupported facts, merging people and superseding facts are different operations. Do not lower a threshold just to pass Maya, or assume the returned confidence is an independent verifier. Separate-question experiments already showed that decomposition alone does not establish reliable identity.

### 6. Medium — forgetting exists, but natural temporal memory is narrow

Corrections, supported duplicate consolidation, explicit expiry and deletion invalidation are implemented. Automatic machine-readable expiry requires a verbatim ISO date-time with timezone. “Today,” “this semester,” or “until Friday” remain prose; there is no normalized event-time model for them. Stable preferences correctly do not expire just from inactivity. Related-person deduplication across notes is deliberately restricted, so repeated mentions can accumulate.

Evidence: [expiry](../Backend/memory_writer.py), line 23; [extraction prompt](../Backend/prompts/memory-extraction-v1.md); [maintenance](../Backend/memory_store.py), `maintain` and `search`.

**Repair:** distinguish capture time, event time, validity, and uncertainty; introduce explicit tested rules for relative time. Expiry must not pretend an appointment actually happened. This is a missing capability for everyday-life memory, not a reason to add a user-facing forgetting workflow.

### 7. Medium — growing-library validation and learning observability need work

Recall snapshots load every live source and query claims per passage. Validation reconstructs and hashes that whole snapshot before/throughout answer generation, including periodic checks. Unrelated library changes can invalidate an answer's manifest. This is safe against stale context but can become expensive; no performance failure at scale was benchmarked in this audit. The health endpoint does not establish memory readiness. Worker logs report job ID and accepted count; sync UI reports “Saved and synced,” not whether learning was rejected or halted. The latter wording is truthful, but operational diagnosis is still mostly operator/database driven.

Evidence: [snapshot](../Backend/memory_store.py), `recall_snapshot` line 381; [validation](../Backend/memory_recall.py), line 151; [Ask monitoring](../Backend/ask.py); [sync status](../App/Sessions/SessionController.swift).

**Repair:** source/claim revisions or a cheap owner generation signal plus selected-evidence validation; measured latency and a content-free health/status path for learning. Keep user UI simple and diagnostics useful.

## Working foundations to retain

- Authenticated owner lookup, stable owner mapping, idempotent source revisions and durable native outbox.
- Permanent source tombstones prevent stale upload resurrection. Revision/deletion invalidates unsupported derivatives and cached job responses. Local saved answers containing a deleted source are removed on that device.
- Transactional claim writes validate job lease, source revision, ownership, subject/kind and lifecycle compatibility. Supported supersession is atomic.
- Independent Jev textual-support verification, strict response validation, cached stage results, no automatic paid retries, and canonical cumulative spending limits.
- Personal recall passes individual verified claims to Luna while preserving the original note for source inspection, preventing an unfiltered original note from reintroducing superseded text.
- Explicit memory-unavailable behavior, bounded answer context and current-source validation.

Boundaries: source deletion is not a claim of erasure from historical backups or every device. Personal-note origin is an authenticated app declaration, not voice identity or proof of authorship of pasted text. Recorded “I” remains unassigned. There is no standalone companion-wide Ask screen: a nonempty session supplies the current question context. No semantic chunking/compaction, adaptive observation scheduler, or general multi-turn Ask history is implemented. These are scope limits, not all immediate blockers.

## How the article changes priorities

[Dhravya Shah's Jev article](https://x.com/dhravyashah/status/2103314339239428201) is exploratory vendor research: it supports evaluating Jev for bounded decisions, semantic boundaries and relevance ranking, while warning that sentence-level removal can damage meaning. It does not validate our entity resolution or prescribe a fix. Its result that ranking worked better than a hard rejection gate is a useful hypothesis for our retrieval layer, not permission to relax write safeguards.

[TypeSafe's atomic-question guidance](https://docs.typesafe.ai/introduction) and [confidence documentation](https://docs.typesafe.ai/confidence) support explicit question boundaries and action-specific policies. Confidence summarizes the returned distribution; it is not a second independent evidence source. We should test each Jev role on its own merits.

No Supermemory integration is proposed. Keep Luna for extraction/answers and Jev for useful independent judgments while fixing the harness contracts and evaluating failure cases.

## Recommended sequence

1. Correctness: explicit uncertainty/conflict lifecycle plus structured entity evidence. Freeze positives, same-name negatives, missing-name cases and historical changes before further model iteration. Finish the failed correction gate here.
2. Reliability: isolate source failures, align size bounds, add context-preserving batching where needed, and expose learning readiness. Prove a bad job cannot stall an unrelated good one without calling providers.
3. Retrieval: remove premature recency cutoffs, compare candidate strategies and Jev ranking, and make revalidation cheap. Measure older paraphrased recall as the library grows.
4. Temporal handling: expand beyond explicit timestamps with a tested validity model. Then consider Jev-based boundary selection/routing when measured benefit justifies extra calls.
5. Repeat only affected paid cases; complete physical correction/recall/persistence/deletion gates before merging PR 31. Keep voice recognition a later input-identity slice; it does not solve identity of people mentioned in speech.

This is a recommendation, not a new implementation or a silent expansion of accepted scope.

## Evidence and limits

Read-only remote inspection: deployed implementation unchanged; schema 3; jobs seven done/two obsolete; claims three active/one invalid/one superseded; no active requests. Profile QA ledger remains 19 Luna + 43 Jev = 62 calls, $0.62 conservatively reserved of the approved $1. This audit made zero provider calls.

31 focused local source/lifecycle/recall/profile tests passed. Five local probes used temporary databases and saved synthetic responses: uncertain-update fallback, paraphrase shortlist loss, older correction target exclusion, worker halt on oversized input, and ordinary name-key equality. Reproduction: `PYTHONPATH=Backend python3 work/memory-audit-probes.py`; evidence in `work/memory-audit-probes.json` and `work/memory-audit-regressions.log`. Existing live successes and failures are retained in [profile recall evidence](personal-profile-recall.md).

No new physical-device test, paid model benchmark, production load test or full security/privacy audit was performed. Code inspection risks are distinguished above from reproduced behavior. Experimental prompts remain unshipped and the failed physical gate remains open.
