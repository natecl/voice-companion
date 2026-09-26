# Opt-in hosted companion runtime

September 26, 2026. This checkpoint wires existing verified components into `hosted.py`; it does not deploy or enable them on Render.

## Configuration

- `VOICE_ENABLE_MEMORY_REWORK=1` requires memory, personal learning, learning, recall and Ask already explicitly enabled. It selects EvidenceWriter with chunking, Jev semantic boundaries, expiry and consolidation, plus multi-source IndexedMemoryRecall. Global reservation receipts and the canonical profile/rework subledger must both exist; startup grants no spending.
- `VOICE_ENABLE_COMPANION=1` requires rework and exposes authenticated `/companion` Ask/history/source operations. Startup recovers interrupted chat under the exclusive service lock, without replaying inference.
- `VOICE_ENABLE_SEMANTIC_INDEX=1` requires rework and `VOICE_EMBEDDING_CACHE`. The pinned embedder loads from a prewarmed cache with `local_files_only=True`; a missing cache fails startup instead of downloading implicitly. Only completed new source revisions enqueue indexing. Existing sources are not automatically backfilled.
- `VOICE_INSTALL_SEMANTIC=1` installs the optional pinned semantic requirements at build time. It is separate from runtime activation so dependencies/cache can be prepared before enabling the model. Other builds retain the lightweight dependencies.

Workers start only after the listener binds. `/health/indexing` reports content-free state/counters/failure status alongside existing learning health. The old routes remain unchanged when flags are absent. Chat never falls through into STT admission.

## Verification

297 backend tests passed. Real local hosted-process startup with enabled rework recovered an interrupted main chat and served authenticated history while keeping all usage reservations unchanged. Relay socket QA proved disabled-route 404, unauthenticated 401, streamed/saved chat and zero STT sessions. Invalid flag combinations fail closed.

A separate run used the actual pinned local embedding model offline, the real hosted process and real Admission ledger. A synthetic source's paid-learning job was deliberately held failed in this disposable QA database; its independent indexing job ran through the real worker into a 384-dimensional stored vector, with no provider calls. This isolates the changed local indexing/runtime boundary without claiming new extraction-quality evidence. Command:

```sh
VOICE_TEST_EMBEDDING_CACHE="$PWD/work/embedding-models" HF_HUB_OFFLINE=1 PYTHONPATH=Backend \
  work/semantic-venv/bin/python -m unittest \
  test_companion_runtime.RuntimeTests.test_actual_rework_process_recovers_chat_and_serves_history_without_spend
```

That real-runtime check first found a thread-affinity defect hidden by the earlier admission fake: IndexWorker queried the admission SQLite connection from a worker thread. It now snapshots active credentials on the owning event loop before dispatching storage work. A dedicated regression test uses the actual ledger; no SQLite safety checks were disabled. The failed run is not acceptance evidence.

The offline model probe returned 384 dimensions in about 0.97 seconds with approximately 315 MiB peak RSS on this Mac. This is not a Linux/Render memory guarantee. Read-only hosted inspection found a 512 MiB cgroup limit, about 237 MiB total current usage, with about 63 MiB anonymous memory and substantial reclaimable file cache. Do not sum RSS and all cached usage as if both were irreducible. Nevertheless, model load, parallel capture/chat/learning and memory growth need headroom and a hosted acceptance check. No model was loaded into the live 512 MiB service during this preparation.

## Rollout prerequisites

Prepare consistent backups of canonical source, usage and memory-budget databases; migrate and inspect a private copy before deployment. Preserve existing owners, source revisions, tombstones, ledgers and failed jobs. Do not restore older databases as a rollback that resurrects deletions, and do not run an old binary on a new schema.

The earlier capacity recommendation was Render's 2 GB `1c-2g` (legacy `standard`) compute plan. The official [pricing page](https://render.com/pricing) lists $25/month versus the current 512 MB Starter's $7/month; the founder explicitly declined this $18/month increase. Keep the current Starter plan and qualify its capacity; do not silently disable semantic retrieval or weaken acceptance. See [plan definitions](https://render.com/docs/compute-plans). Final hosted resource acceptance remains required.

The canonical profile/rework ledger still reserves $2.38 of $2.40. No paid calls were made in the native/runtime checkpoints. A proposed additional $0.50 QA allocation would require explicit approval and category-budget reallocation within the existing $5 overall cap; current Ask/Jev category headroom alone cannot cover it. Do not reset spent attempts, silently increase limits or enable learning with insufficient allowance.

After approval: back up/validate the exact deployment commit; install dependencies with runtime flags still off; prewarm the pinned cache; confirm resource headroom and migrations; provision the approved allowance once; enable the reviewed runtime flags; inspect health/queues without bulk reprocessing; activate/install the matching native interface. Then explain the physical-iPhone sequence and wait for founder readiness. Final capture/chat/recall/correction/relaunch/source deletion acceptance remains pending.
