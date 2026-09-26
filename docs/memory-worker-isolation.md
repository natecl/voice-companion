# Memory rework checkpoint 2A — isolate job-local failures

An accepted source larger than the extraction request limit previously caused the worker to exit, leaving subsequent valid recordings queued. The worker now continues only for an explicit allowlist: extraction/support/judgment request-size limits, obsolete jobs, and stale relation targets. The writer has already marked those jobs failed or obsolete. No retry, source truncation, model fallback, quota reset or paid replay is added.

Budget denial, provider/authentication failures, malformed model output, storage errors and unknown exceptions still halt all learning for review. A malformed provider response might reflect a systemic issue, so it is deliberately not treated as an isolated bad recording. Failed jobs are not requeued after restart. Original source content remains stored and available for an explicitly reviewed future processing strategy.

## Observability

`/health` remains service liveness. `/health/learning` returns a content-free JSON diagnostic: starting/running/idle/halted/stopped, a sanitized last failure, and process-local completed/quarantined counts (or disabled). No owner, source text, credentials or provider exception body is included. A halted learner deliberately does not fail service liveness: an automatic process restart could resume unrelated paid work without reviewing a global failure. Operators must inspect the learning diagnostic; HTTP 200 on this endpoint means the diagnostic request succeeded, not that learning is healthy. Counts reset on restart; durable job states remain in SQLite. Backlog age/chunk-stage diagnostics belong to the next checkpoint.

## Behavioral QA

Python 3.13, local Mac, temporary databases and injected provider adapters; no paid inference.

```sh
python3 -m unittest discover -s Backend -p 'test_memory_worker.py' -q
python3 -m unittest discover -s Backend -q
```

Five focused tests exercise actual queue/writer/storage behavior and a local HTTP server:

- Oversized source followed by a valid source: first failed, second learned once, three fixture provider-stage calls total. Restart makes no extra calls.
- Budget/authentication/unknown failure: worker halted and following source remained queued, without a retry.
- Reservation denial: zero provider calls.
- Source deleted during extraction: obsolete result rejected; subsequent source learned.
- Actual HTTP requests: learning reports halted with sanitized reason while liveness remains available.

Final full backend suite: **113 tests passed**. Broader checks cover changed hosted startup and relay authorization plus shared worker behavior. No prompts, provider contracts, schema changes, live data edits, app installation or deployment.

This fixes isolation, not oversized-source learning. Chunking remains checkpoint 2B. Existing oversized jobs stay failed until an explicit bounded recovery/backfill decision; they do not silently incur new calls. Provider-quality and physical-device QA are not claimed by these local storage/HTTP checks.
