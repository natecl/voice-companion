# Automatic memory learning — checkpoint 2

September 25, 2026. Implements the learning checkpoint in [the memory plan](memory-implementation-plan.md). This is verified backend learning with synthetic evidence, not deployed phone memory or cross-session Ask. No native UI changes, user-facing forgetting, suggestion inbox, or Supermemory dependency.

## Working path

Authenticated source upload → durable queued job → one background consumer → Luna candidate extraction → bounded related-memory lookup → batched Jev judgments → validated atomic writes and lifecycle maintenance. Source upload acknowledgment does not wait for inference. Empty sources use no calls; filler uses extraction only. Incomplete recordings can contribute their finalized passages. Assistant answers are not ingestion sources.

Luna (`gpt-6-luna`, Standard/default, reasoning none, strict JSON schema, no tools) extracts up to eight atomic records. Jev (`jev-1.13.0`, rubric `memory-v4`) judges textual support, attribution, modality, relationship to existing records and explicit expiry. The initial rubric confused source support with independent truth verification; the corrected rubric explicitly asks what the transcript says. Neither model directly writes storage.

Accepted judgments require probability ≥0.90 and confidence ≥0.60. These are conservative evaluation gates, not calibrated accuracy guarantees. Unknown identity stays unknown and is never inferred from the device owner or Speaker 1. A hashed name is an entity label, not biometric or verified identity. Same-label records are merged only after a clear relationship judgment; ambiguous cases remain separate. The current writer never assigns the special `user` identity, so the personal profile stays empty until a separately supported attribution mechanism exists. Useful named and anonymous conversation memories still persist.

Expired context retains history. Corrected context supersedes the old record. Duplicates combine evidence. Source deletion/revision scrubs its cached model responses and removes support; stale in-flight results cannot recreate deleted content. A past expiry with unknown start retains a null start instead of inventing an interval.

## Limits and failure behavior

- Extraction request: at most 16,000 UTF-8 bytes including schema/instructions; 3,000 output tokens. Larger synchronized sources fail explicitly with `memory_extraction_too_large`; their saved transcript remains. No silent truncation or automatic batching.
- Related lookup: bounded lexical/entity baseline; at most four current records with the same subject label and kind per candidate. It is not semantic recall or a promise of complete duplicate detection.
- Jev request: at most 28,000 UTF-8 bytes, one batch. Dates are up to eight verbatim ISO timestamps in cited evidence. Jev selects an explicit applicable expiry; code validates the timestamp. Relative dates and ambiguous time remain unnormalized. Appointment start is not proof of completion.
- Provider timeouts: Luna 20 seconds, Jev 15 seconds. SDK retries are disabled. One learning consumer keeps provider concurrency at one; database work uses operation-scoped connections. Recording/Ask do not await the worker.
- Jobs persist revision, lease, extractor version, cached stage outputs, sanitized failure code and completion state. Provider usage and elapsed time are cached privately. Routine logs contain job IDs/counts only.
- A processing failure halts the background consumer for operator review. It does not retry paid work or take down source sync, STT or Ask. On restart, running jobs become interrupted; queued jobs remain eligible. Expired/revoked enrollments are excluded before scheduling. Reads enforce expiry even between maintenance passes.

Schema v2 adds job-stage caches and error codes to v1, without resetting sources or the spend ledger. Disable memory before reverting to code supporting only schema v1. Caches contain source-derived content and follow the source deletion lifecycle. The [foundation retention and backup deployment gates](memory-foundation.md) still apply.

## Approval and cost accounting

The founder approved up to **$0.25 within the existing $5 testing ceiling**. Allocation ID: `memory-qa-2026-09-25-025`. One idempotent administrative transaction reserved 250,000 micro-USD in the existing hosted ledger under the retired `jev` category. This is a mixed Luna/Jev QA allocation, not reactivation of the retired Ask intent router or an invoice. Global reservations became $0.555, including the full allocation.

A single private subledger reserves $0.005 before each bounded live call, never refunds failed/uncertain attempts, and rejects duplicate attempt IDs. Exact cached-request replay bypasses both provider and a new reservation. Do not delete/copy/reset the subledger to obtain another allowance. No paid calls run in unit tests or CI.

Live evaluation used **14 Luna + 17 Jev calls** across initial failures, targeted revisions and final validation: $0.155 in conservative per-call reservations. Reported usage: Luna 8,093 input / 815 output tokens; Jev 22,032 input / 3,125 output tokens. At the published Standard Luna $0.10/$0.50 per million input/output and Jev $0.042 per million input with free output, estimated model cost is **$0.002142144**. This is an estimate from returned usage, not a billing receipt. The full $0.25 allocation remains reserved; no remainder was reassigned.

Sources checked September 25: [Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [structured output](https://developers.openai.com/api/docs/guides/structured-outputs), [Jev models](https://docs.typesafe.ai/models), [Jev API](https://docs.typesafe.ai/api).

## Behavioral evidence and failures retained

Synthetic cases and expectations were frozen before their live runs in `Fixtures/memory-learning-cases.json`. Fresh cases are a held-out **variant set**, not a statistically independent benchmark. No general reliability claim follows from six examples.

1. Initial development preference: Luna extracted correctly; Jev support was 0.64 with confidence 0.47, so nothing was written. Rubric v2 clarified textual support. Cached extraction was reused; preference and correction then passed. Thresholds were unchanged.
2. Initial held-out run: preference, unknown speaker, hypothetical omission and temporary expiry passed. Correction text was correct but Luna left `expires_at` null; it would not retire automatically. This critical gate failed and stopped the run.
3. Rubric v3 added a separate date judgment. The correction was conservatively discarded at 0.84 probability rather than silently accepted. Rubric v4 explicitly separates this judgment from the extractor's nullable field and describes the date choices. Earlier failures remain in ignored evidence logs. A local syntax typo was caught before any provider request and fixed.
4. Regression v4: all six original cases passed, including correction, duplicate consolidation and controlled-clock expiration. Exact unchanged responses were reused; affected judgments and the previously unrun duplicate used live calls.
5. Fresh variant set: **6/6 passed** with live Luna/Jev. Inspected database: Nora's preference active with two sources; anonymous preference active with null subject; old Birch expiry superseded; corrected Birch expiry expired after clock advance. Both historical versions remain.

Ablation from the same responses: extraction alone already omitted the hypothetical and retained anonymous attribution. Jev did not repair an extraction error on those cases. On the original correction, the separate Jev expiry judgment restored the missing structured expiry from the source; on the fresh set Luna supplied it correctly and Jev confirmed it. Initial support/expiry wording caused false rejections. This is evidence for the narrow judgment role, not proof that Jev improves every memory or all extraction accuracy.

Provider responses from the fresh synthetic set are checked in at `Fixtures/memory-provider-responses.json` for offline lifecycle regression. They contain no real conversations, keys or production credentials. Tests replay these through the real writer/store, inspect expiry/duplicate/superseding, reopen the database and confirm no queued repeat work.

The real local WebSocket source upload also runs against `MemoryService` and the background worker with fixture providers: acknowledgment → automatic processing → persisted claim without another client action. Separate live-provider runs prove the real adapters through the same writer; no claim of a deployed cloud-to-phone path is made. Targeted cases additionally cover malformed output, missing source IDs, failure halt, revoked credentials, similar names, incomplete source, past expiry, deletion during inference and the fixed budget.

Evidence under ignored `work/memory-learning-qa/`: initial `development`, `development-v2`, `heldout`, `regression-v3`, `regression-v4`, `heldout-v3` SQLite stores/results and run logs; one allocation receipt and one budget ledger. `work/memory-learning-backend-final.log`: 52 backend checks passed. `work/memory-learning-final.log`: 23 focused memory checks passed after moving stage bookkeeping off the event loop. Earlier local regression logs are retained. Do not rerun paid suites to debug storage or rendering.

Reproduce without provider spend:

```sh
python3 -m unittest discover -s Backend -p 'test_memory*.py' -v
```

## Enablement and next checkpoint

Hosted configuration and installed apps remain unchanged and memory-disabled. `VOICE_ENABLE_MEMORY_LEARNING=1` additionally requires memory enabled, both server provider keys, and a provisioned `memory-allocation.json` plus the **canonical existing** `memory-budget.sqlite` on persistent storage. Startup must not create another spending grant. Do not copy the QA allocation into a second active spending ledger. Deployment, transfer of the canonical ledger, retention/backup reconciliation and client enrollment require the separate concrete rollout review in the plan.

Next: Jev-assisted cross-session retrieval, bounded answer context, source references, deletion propagation into saved answers, then founder-ready iPhone QA. This checkpoint alone does not make Ask aware of past conversations.
