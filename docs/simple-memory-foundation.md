# Simpler memory foundation

Status: implementation in progress; existing hosted memory remains the baseline. This supersedes the proposed strict notes-first rollout, which remains held by the [matched comparison](matched-recall-comparison.md).

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
