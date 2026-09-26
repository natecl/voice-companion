# Background semantic indexing

Checkpoint 5F adds schema 12 and an opt-in durable local indexing queue. Setting `MemoryStore(..., embedding_model=contract)` enrolls newly stored completed source revisions atomically with source persistence, without inference in the source transaction. Incomplete captures, unchanged replays and startup migrations do not trigger bulk historical indexing. Existing completed sources without jobs are explicitly reported as `unindexed`.

`IndexWorker` processes authorized owners outside the answer path, using the pinned source/model cache. Completed, failed, queued and unindexed coverage are separately inspectable. A source-specific size failure is quarantined and the next source still indexes; failed jobs are not automatically retried. Under the service's exclusive process lock, interrupted purely local jobs can resume and reuse a completed cache write. Revision/deletion invalidates pending jobs and vectors; a late result cannot recreate old evidence. An expected-revision check also prevents a claimed older job from computing a newer source unnecessarily. Global model/runtime errors halt the worker.

Schema 12 adds only the queue and a correction-link lookup index; it performs no backfill or model call. Hosted startup/feature flags and combined resource acceptance are still pending. This is a runnable backend worker, not a claim that the deployed service runs it.

## QA and discovered retrieval fix

The actual pinned model processed six sources from queued → done; hybrid retrieval recovered all six designated paraphrases in the top three and deletion removed the selected source. `worker-proof.json` records that path. The first run exposed a rank-fusion defect: common query words such as “my” and “is” made unrelated lexical hits outrank the correct semantic result. Its result is preserved as `failed-worker-fusion.json`. Removing common function words **from query weighting only** fixed the original frozen gate. Source text and negation are preserved.

The existing 10/100/1,000-source hybrid benchmark then passed unchanged (all designated sources top five; max observed local query plus validation 20.558 ms). `hybrid-proof-v2.json` records the rerun. This does not establish hosted latency.

The full default suite passed 248 tests before the query-weighting regression and pre-computation revision tests were added; the final focused indexing/search/vector runs passed 5/5/5 tests. Storage checks cover failure isolation, restart/cache reuse, active-owner scope, revision during computation, revision before computation, deletion, default-off migration and incomplete sources. No new provider calls, STT, native changes or deployment.
