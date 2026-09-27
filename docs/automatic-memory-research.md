# Automatic memory for the listening companion

> Dated research/audit record. Preserve its findings and uncertainty; it does not describe the current deployed stack or authorize changing it. Read [current state](current-state.md) for adopted decisions, subsequent fixes, rejected candidates and remaining limits.

Research date: September 25, 2026. Research and architecture recommendation, not an implemented feature or vendor commitment. Reviewed official TypeSafe/Supermemory documentation, alternative implementations and original research. No provider evaluations, installations, account changes or uploads of user transcripts were performed.

## Accepted product direction

The founder wants automatic memory formation, not proposed memories or a confirmation inbox. Relevant context can carry across conversations and inform answers inside a new meeting. Founder clarification after this research: memory maintenance is internal, with no Forget button or memory-management UI. Superseding, expiration, invalidation and duplicate consolidation happen automatically; useful historical evidence remains available. Existing session deletion remains supported. The [implementation plan](memory-implementation-plan.md) supersedes earlier user-managed forgetting proposals. Separate the source of a claim from its current interpretation. This extends the verified current-session V1; it does not change the one-liner or retroactively claim memory was delivered.

The founder explicitly does not want to adopt Supermemory. It is a research reference only: no SDK, service, self-hosted deployment or provider comparison is proposed. Build our own focused memory harness, borrowing useful engineering concepts rather than its infrastructure. This constraint is accepted; the design below is a proposal, not an implemented or approved architecture.

Recommendation: own source records, memory lifecycle, retrieval and context assembly. Use Jev for bounded judgments where errors would otherwise become persistent. Luna produces candidate records; Jev judges selected properties; code applies validated transitions. Keep live transcription and current-session Ask independent of memory processing. No graph database is required just to implement versioned claims and source links.

## Lessons from Supermemory, without adopting it

Supermemory separates original documents from extracted memories. Its update, extension and derivation relationships distinguish changed information, compatible detail and inference. Borrow this distinction: changing an appointment should supersede its old time, while learning its location should add detail. An inference must remain distinguishable from something actually said. These are design precedents, not measurements of accuracy on our conversations. [Graph memory](https://supermemory.ai/docs/concepts/graph-memory)

Its profiles distinguish relatively stable information from recent context. Our equivalent should be a small derived cache of broadly useful, source-backed information, alongside query-specific retrieval. The profile must remain rebuildable; it must not become an unsupported biography or attach every personal detail to every answer. [Profiles](https://supermemory.ai/docs/concepts/user-profiles)

Its asynchronous pipeline illustrates an important readiness distinction: indexed source text and fully consolidated memory are different states. Our system should expose processing state internally and retrieve recent evidence while extraction catches up. Saving a transcript must not falsely imply all durable memories already exist. [Pipeline](https://supermemory.ai/docs/concepts/how-it-works)

Its search can return memories alongside document chunks. Borrow the two-level recall pattern: concise memories help personalization, while original passages preserve detail and allow verification. Its API's term “hybrid” describes those result types and should not be treated as proof of any particular lexical/vector algorithm. [Search](https://supermemory.ai/docs/recall/search)

Its documentation distinguishes soft forgetting from document deletion. Our own lifecycle must explicitly cover derived claims, profile entries, caches and in-flight jobs. A hidden search result is not the same thing as erased data. [Memory operations](https://supermemory.ai/docs/recall/memory-operations), [document operations](https://supermemory.ai/docs/ingestion/document-operations)

The general lesson is that a memory harness owns the entire loop: what is extracted, what it means, how it changes, when it is retrieved, what enters the answer, and how it is corrected or removed. A vector index alone handles only part of that loop.

## What the broader research changes

LongMemEval tests extraction, multi-session reasoning, temporal reasoning, updates and abstention. Its analysis finds that reducing history to isolated facts can discard useful information; retrieval granularity, expanded indexing and time-aware retrieval matter. For us: retain addressable transcript passages alongside extracted memories, and evaluate each stage separately. A retrieved relevant passage is not automatically a correct answer. [Original paper](https://arxiv.org/html/2410.10813v2)

Event-oriented representations preserve participants and time together. A recent simple-baseline paper argues for compact event-like propositions rather than disconnected triples or opaque summaries. This is particularly appropriate to meetings, promises and changing appointments. We should borrow the representation before assuming a complicated graph is necessary. [Event-centric memory](https://arxiv.org/html/2511.17208v1)

Hindsight separates facts, experiences, entity summaries and beliefs, with retain/recall/reflect operations. Its useful lesson here is to keep evidence separate from inference and make consolidation traceable; we do not need a second reasoning agent for every answer. [Hindsight paper](https://arxiv.org/abs/2512.12818)

Graphiti provides temporal graph updates and provenance, and documented search recipes combine semantic/lexical retrieval and graph structure. Mem0 offers extraction plus optional relationship graphs. They are additional references for our own implementation, not proposed dependencies. Borrow temporal validity, provenance and retrieval recipes without deploying their frameworks. [Graphiti overview](https://help.getzep.com/v2/graphiti/getting-started/overview), [search](https://help.getzep.com/graphiti/working-with-data/searching), [Mem0 graph memory](https://docs.mem0.ai/open-source/features/graph-memory)

Context engineering remains selective: retain history outside the prompt, then assemble only what helps the present question. A larger context window does not eliminate irrelevant or contradictory context. [Anthropic engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

Persistent memory also extends the lifetime of bad input. Memory-poisoning research studies how untrusted text becomes durable influence. For our product, a quoted instruction in a meeting must remain conversation data; memory cannot rewrite system behavior, identity, permissions or tool authorization. [Original study](https://arxiv.org/abs/2606.04329)

## The memory model we should own

Use three representations, each serving a different job:

1. **Conversation evidence:** transcript passages with session ID, revision and timestamps; preserve distinctions between speakers, quoted speech and assistant output. Searchable even when no personal fact is safely attributable.
2. **Structured memories:** preferences, people/entities, commitments, decisions, recurring constraints and events. Each has source references, subject, stated-versus-inferred status and lifecycle.
3. **Compact current profile:** a derived selection of reliable, broadly useful memories. Rebuild/invalidate it when its source changes or is forgotten.

Proposed minimum record, not a vendor schema:

```text
id, user_id, subject_id_or_unknown, kind, claim
source_session_id, source_revision, source_span_ids
observed_at, event_time_or_interval, valid_from, valid_to
status: active | superseded | disputed | expired | forgotten
basis: stated | inferred
attribution_evidence, replaces_id, extraction_version
```

Store evidence confidence, attribution uncertainty and relevance separately. One magic confidence score cannot describe all three. `observed_at` means when we learned a fact; event time means when it happened/applies. An old recording uploaded today must not automatically override a newer real-world fact.

Automatic does not mean indiscriminate. A phrase like “I am moving to Boston” can be remembered as a statement from an unknown participant without asserting the user lives there. Never carry numeric Speaker 1 identity across sessions. Reliable user attribution needs additional evidence; text-only Jev cannot recover identity absent from the input. Named people, projects and meeting decisions can still be remembered automatically without solving voice biometrics first.

Examples:

- A friend says they dislike morning meetings: remember a preference about that identified friend, not the user.
- Someone speculates “we might launch Friday”: preserve a tentative plan, not a commitment.
- A lecturer says “imagine I am a surgeon”: keep the educational context, not a biographical fact.
- A later correction moves an appointment: supersede the earlier schedule while preserving its source history.
- Two people disagree: retain attributed competing claims; do not decide truth by last-write-wins.
- The companion suggests a plan: store as assistant advice only if useful; do not count it as an independent user commitment or repeated evidence.

A commitment can stop being active after its date without erasing the episode. Stable preferences should not disappear merely because the user does not repeat them. Repeated copies of one transcript are one source, not increasing corroboration.

## Jev's concrete role

Current docs list `jev-1.13.0`, text-only, $0.042 per million input tokens with free output. It returns Choice, Score and Noul judgments; it is not a prose generator or database. Independent questions can share a state. Pin model and rubric versions. [Models](https://docs.typesafe.ai/models), [primitives](https://docs.typesafe.ai/introduction), [batching](https://docs.typesafe.ai/patterns/fan-out)

| Decision | Proposed Jev use | Deterministic responsibility |
| --- | --- | --- |
| Is this passage worth extracting? | Broad recall-oriented Choice: meaningful event/preference/decision versus filler/quotation/uncertain | Keep original evidence even if extraction is skipped; avoid filtering away rare useful facts |
| Does a candidate follow from its source? | Noul or explicit supported/contradicted/unclear Choice | Require real span IDs and reject fabricated references |
| Whom does it concern? | Choice over supplied known entities plus unknown | Never equate microphone owner with speaker; enforce user boundaries |
| Is it stated, hypothetical or inferred? | Choice with explicit examples | Store basis and modality; do not silently promote inference to fact |
| Does it duplicate/update/conflict with a retrieved memory? | One bounded pairwise judgment after candidate retrieval | Version updates transactionally; retain conflicts and source history |
| Is a retrieved item helpful now? | Score a small shortlist against question and current conversation | Apply access, deletion and temporal filters first; enforce prompt budget |
| Is a draft claim supported by a cited passage? | Targeted citation-support check for evaluated problem cases | Source-ID validation always runs; model checking cannot guarantee truth |

Official TypeSafe cookbooks cover candidate entity alignment, RAG passage classification, extraction verification and citation checking. They demonstrate patterns, not calibrated performance on our speech. [Alignment](https://docs.typesafe.ai/cookbooks/entity_alignment), [RAG filtering](https://docs.typesafe.ai/cookbooks/classifying_rag_passages), [extraction cascade](https://docs.typesafe.ai/cookbooks/sde_cascade), [citations](https://docs.typesafe.ai/cookbooks/citation_check)

Start with candidate support/attribution and pairwise update decisions. The founder subsequently selected Jev for relevance assessment of retrieved candidates in the next slice; verify that role on held-out retrieval before enabling it. Do not put a Jev call in front of every search just to decide whether to search: a false negative can erase the product's continuity, and search may be cheaper/faster than gating it. Explicit “this meeting only” intent can be handled directly; otherwise retrieve bounded candidates and discard irrelevant results.

Jev confidence summarizes the distribution over supplied options; it is not an independently proven correctness rate. Calibrate thresholds for each action on our labeled data. Wrong-subject writes and false merges warrant much stricter acceptance than missing a low-value preference. [Confidence](https://docs.typesafe.ai/confidence)

TypeSafe documents weaknesses in date arithmetic, numerical precision, indirection, irrelevant long state and adversarial content. Resolve dates and compare ranges in code; provide short relevant spans; keep unknown outcomes. Its SDK retries by default, so explicitly preserve our bounded retry/spend policy. [Limitations](https://docs.typesafe.ai/model-jaggedness/jev-1.13), [model/SDK policy](https://docs.typesafe.ai/models)

Our prior Jev experiment classified a tiny held-out intent set well but failed the paired-answer grounding gate. It does not establish memory performance. Reintroduction for a different, useful judgment is reasonable; the [failed routing evidence](v1-jev-decision.md) remains failed. Do not reuse its thresholds as memory thresholds.

## Proposed pipeline

```text
Microphone -> streaming transcript -> current-session Ask stays responsive
                        |
              revision-aware stable passages
                        |
          durable, idempotent background memory job
                        |
         extract candidate records (generative model)
                        |
      retrieve possible duplicates / related prior facts
                        |
       Jev: support, attribution, modality, relationship
                        |
       code: validate, version, commit; update indexes
                        |
        searchable evidence + memories + compact profile
                        |
New Ask -> current snapshot + relevant past sources -> Luna answer
```

Automatic extraction at session end is the smallest complete first write path. Once proven, add periodic batches of stable passages during longer sessions. Never launch extraction on every partial token or wait for all memory writes before showing the current transcript. Already learned history can inform the current meeting from its start. Fresh session text remains available directly even before its memories are consolidated.

A durable queue and source revision key prevent duplicate writes after disconnects. Late transcript corrections supersede dependent memories; a deleted session's tombstone prevents an old worker from recreating it. Retry transient background work within a recorded cap and with idempotency; do not create unbounded new paid runs. Keep the existing $5 evaluation ledger and obtain a concrete memory-testing allocation before provider work.

At answer time, search with the question plus a small relevant portion of current conversation so “what about that deadline?” has a referent. Fetch the compact profile and relevant evidence in parallel where useful. For custom retrieval, combine lexical/name matching with semantic candidates; consider a bounded entity expansion for questions needing multiple sources. Avoid exhaustive pairwise Jev comparisons across the user's archive.

Freeze an answer context manifest: current session/revision/cutoff, memory versions and source IDs. Label current-conversation evidence separately from older context and assistant inference. If retrieval fails, answer from current context only and say past context is unavailable; never equate a retrieval outage with “you never told me.” Historical questions may need superseded records; current-state questions normally should not.

Internal invalidation must remove unsupported claims from the profile and cached retrieval and prevent stale-job recreation. Superseding and expiration instead retain temporal history. Saved answer copies referencing deleted sources also require lifecycle handling. Account deletion must cover cloud content and outstanding jobs, not just local JSON. This requires new durable backend content and user ownership: our present relay deliberately persists no transcripts, so memory is a real data-lifecycle change.

## Keeping the implementation small and inspectable

Use four focused responsibilities rather than a new service fleet:

- **Memory writer:** turns a stable source revision into candidate records and bounded judgments.
- **Memory store:** owns source links, versions, transactions, user isolation, deletion and job state.
- **Memory retriever:** finds permitted evidence and claims for the current question.
- **Context builder:** assembles a bounded, source-labeled snapshot for the answer model.

Start with ordinary persistent records and typed relationships. Treat embeddings and the compact profile as rebuildable indexes, not the authoritative memory. Select the smallest storage solution that supports our hosting, ownership and deletion requirements; a graph database is not a prerequisite.

Key background jobs by user, session, source revision and extractor version. Commit memory transitions transactionally and keep a durable processing cursor. A revision or deletion check immediately before commit prevents stale workers from restoring invalid claims. A failed memory job must not prevent transcript saving or current-session Ask. Record job outcomes, source IDs, model/rubric versions, token usage and latency; avoid logging entire private conversations by default.

Retrieval applies authenticated ownership, deletion and temporal constraints in code before ranking. Lexical matches help exact names; embeddings help paraphrases. Retrieve a small candidate set, then use Jev for semantic relevance as agreed for the next slice. Preserve contextualized source passages for questions where extracted facts are insufficient. [Contextual retrieval](https://www.anthropic.com/engineering/contextual-retrieval)

Updates need two clocks: when we learned the claim and when it applies. A backfilled old conversation should not overwrite a recent correction merely because it arrived later. Contradictions can remain separate attributed claims. If several sources support a memory, deleting one requires reevaluating remaining support; deleting a source must not leave its unsupported derivatives active.

No fact-forgetting UI is planned. Internal retirement must distinguish historical validity from unsupported or deleted information, including source-passage fallback. Session deletion invalidates the source and dependent records; define saved-answer and backup handling too. Corrections require source and subject attribution; quoted transcript instructions remain untrusted content.

## Cost and latency implications

Illustrative Jev-only arithmetic, assuming the quoted input-token rate and counted total state/questions: 60 batches per hour at 2,000 tokens each costs $0.00504; 30 hours costs $0.1512. Batching shared state is useful, but repeated long histories can erase the saving. This excludes generation, embedding, storage, transcription and answers; token usage must be measured. Jev is cheap, not free. [TypeSafe pricing](https://docs.typesafe.ai/models)

Set a proposed memory-retrieval overhead target (for example p95 under 500ms) before testing; it is not a vendor guarantee. Write-time Jev can be asynchronous. A chain of Jev routing, search, Jev reranking and Luna generation adds serial latency; add stages only for measured quality or cost benefit. Our observed direct-Ask latency already varies, so report retrieval time separately from generation and phone display.

## What to prove before implementation is called successful

Use a small frozen multi-session corpus built for this app, not only vendor leaderboards. Include friends/lectures/appointments, unknown speaker identity, similar names, changed commitments, relative dates, conflicting accounts, hypothetical statements, ASR revisions, quoted prompt injection, assistant-generated suggestions, corrections, deletion and reprocessing. Keep development examples separate from held-out cases.

Compare our bounded evidence-retrieval baseline with the same system plus structured memory, then with Jev judgments added. Hold answer model, questions, source history and context budget fixed. This isolates whether memory and Jev improve results. No Supermemory integration or vendor competition is needed.

Measure memory-write precision/recall, wrong-subject rate, false merges, stale-current answers, useful cross-session answer rate, attribution/source support, failure to abstain, deletion resurrection, tenant isolation, freshness lag, p50/p95 latency and cost per captured hour/Ask. Define must-pass cases for wrong-user leakage, source fabrication and deleted-data resurrection; a zero observed count in a small set is not a universal guarantee.

LongMemEval's categories and Supermemory's open MemoryBench can help structure the harness, but chat benchmarks are not proof of noisy multi-speaker audio handling. Do not rank products using scores with different readers, token budgets, judges or datasets. [LongMemEval](https://arxiv.org/abs/2410.10813), [MemoryBench](https://supermemory.ai/docs/memorybench/overview)

The first product acceptance scenario should span conversations: a fact is captured automatically in session A; a question in B uses it with the original source; C corrects it; D uses the new fact and can explain its change; temporary context is retired automatically and stays out of current-state answers after replay/restart while remaining available as history. Source deletion must prevent invalidated content from resurfacing. No approval or suggestion inbox occurs anywhere. One final physical-iPhone path is necessary once fixtures and provider contracts pass; repeated audio runs are not needed to debug memory lifecycle code.

## Proposed implementation sequence

1. Define source revisions, ownership, memory records and deletion semantics. Build synthetic multi-session fixtures and a persistent job/store path. Prove replay, corrections, internal lifecycle maintenance and deletion locally before paid model calls.
2. Add automatic session-end candidate extraction and a small Jev judgment batch for source support, attribution and updates. Evaluate against the same extractor without Jev, with a separately agreed provider budget. Keep unknown attribution as conversation evidence, not a user approval queue.
3. Add bounded cross-session recall and source-linked answers. Preserve the existing current-session path and clearly distinguish past context. Prove capture, cross-session recall and correction on iPhone when the founder is ready; test automatic expiration with a controlled fixture clock. No user-facing forgetting step.
4. Only after that loop works, consider incremental in-session consolidation, more sophisticated retrieval or additional Jev roles where measured failures justify them.

The next design decisions are persistent backend storage, authenticated ownership and extraction schema. Research supports these responsibilities, but does not select a database or authorize a deployment. Keep the implementation in a few focused modules in the existing backend; avoid a separate service per pipeline stage.
