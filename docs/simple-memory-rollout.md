# Unified memory internal rollout

Status: founder-approved internal rollout completed September 27, 2026 UTC (September 26 local). This is not public-release or new physical-iPhone acceptance.

## Deployed behavior

Verified code from PRs 95–97 is live at `145f4c847fdf862a041e16221878f1117b77c756`, Render deployment `dep-das7tpt9fdbs73c8b7jg` (live 02:27:49 UTC). `VOICE_ENABLE_NOTES_RECALL=1` selects unified evidence recall and source-scoped learning together. Notes discover original passages alongside transcript search; Jev ranks bounded candidates with an independent evidence reserve. Compatible learned observations stay source-scoped, while independently verified corrections preserve identity and lifecycle guards. Existing normalized provenance/correction tables remain; this simplifies active orchestration, not the physical schema.

The service remains on the existing Starter plan, one instance and 1 GB disk `dsk-daqtfs7lot8c73dlevl0`, with automatic deployment disabled. Recording notes, independent verification, retained recording memories, rework, companion and semantic indexing remain enabled. No provider quotas, recording limits, Ask limits or allocation grants changed.

## Verification and evidence

Before deployment, there were no active requests or pending/running learning jobs. SQLite backup API snapshots of every root database passed integrity checks and SHA-256 manifest verification. The recovery directory is `/var/data/voice-companion/simple-memory-approved-k6li_06o`; it contains private data and must not be committed.

After deployment:

- Schema migrated from 17 to 18. The existing ready note was indexed; nine live sources remained. All pre-existing table rows in every backed-up database matched after migration, including usage and provider ledgers.
- Main runtime reservations remained 4,956,868 microUSD. Zero active requests and no new provider attempts. Learning jobs remained ten done and eight obsolete; no automatic re-learning/backfill occurred.
- `/health` returned `ready`; notes, learning and indexing health endpoints were idle with no failures. The actual serving Python process had the unified, notes, rework, independent-verification and retention flags enabled. SSH shell and wrapper-process flags do not represent runtime selection.
- Actual public TLS websocket requests read authenticated companion history and the existing ready note. Both endpoints rejected unauthenticated handshakes with HTTP 401. No Ask, capture, notes retry or generation request was sent.
- Read checks used a two-minute operator credential bound to the existing note owner and revoked in `finally`. No quota grant was issued. A second database comparison confirmed all old rows preserved; the only permitted additions were that credential and its owner mapping. Usage remained unchanged.
- Render service configuration comparison confirmed unchanged plan/disk and disabled auto-deploy. The live deployment receipt confirms the exact verified commit.

Local operator receipts and executable check scripts are in ignored `work/simple-memory-rollout/`: `backup.json`, `verification.json`, `verification-after-access.json`, `access.json`, `runtime.json`, `live-deploy.json`, and before/after service receipts. Scripts compare old rows without printing their contents, check existing note indexing and worker state, and execute the read-only websocket checks. Credentials and private source text are excluded from committed evidence.

To independently inspect rollout state, use `render deploys list srv-daqtfs7lot8c73dleuug --output json`, service configuration inspection, the four health endpoints above, read-only SQLite integrity/schema/index/ledger checks over the approved SSH connection, and authenticated `history`/notes `read` operations. Read the actual hosted Python process environment for the allowlisted feature flags only. Never print provider credentials or conversation contents.

The behavioral provider and exact-replay evidence for retrieval/learning is in [the foundation checkpoint](simple-memory-foundation.md). This deployment check validates production migration, configuration and read access; it does not claim another live model answer, new physical-device behavior, general accuracy, lower latency or reduced invoices. No app/API change requires a new native build for this backend rollout.

## Rollback and remaining boundary

If the new route regresses, disable `VOICE_ENABLE_NOTES_RECALL` and redeploy schema-18-compatible code, keeping current sources, usage charges and all other settings. Do not restore stale usage databases or run an old schema-17 binary against the migrated store. The backup is a recovery artifact, not a routine rollback mechanism.

The first simplified memory foundation is now internally enabled. Historical compatibility code and provenance tables remain intentionally available. Further cleanup requires its own concrete benefit and verification; it is not a prerequisite to this slice. Founder-assisted phone QA must wait for explicit readiness; new paid model QA needs a specific available allowance.
