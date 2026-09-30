# Migration maintenance startup

September 30, 2026. Candidate only; no hosted environment/deployment changes.
Stacked on PR167. This adds the controlled no-writer interval needed for the
founder migration, without an HTTP administration or migration endpoint.

`VOICE_MAINTENANCE=1` selects a startup-only health service before any ledger,
MemoryStore, provider client, recovery operation or worker is constructed.
`/health` returns HTTP200 with `state=maintenance`, `database_open=false` and
`workers=stopped`. All other paths, including account WebSocket upgrades and
worker health paths, return HTTP503 and Retry-After60. No background work starts.
Normal startup defaults to the existing behavior; malformed flags fail closed.
Changing this setting requires a controlled restart, not a live toggle that
could interrupt an unobserved active transaction.

Both modes retain the existing singleton `service.lock`. Normal runtime also
holds an exclusive `database.lock` through ledger closure. Offline operators must
hold `maintenance.database_lease(directory)` throughout the coordinated backup,
full inventory, schema preparation and migration transaction. Maintenance does
not hold that lease or open a database, so the operator can acquire it. A normal
service cannot start while the operator owns the lease, and an operator cannot
acquire it while the new normal service is running. Locks release on process exit;
never delete lockfiles to bypass exclusion.

Older deployed code does not participate in database.lock. Therefore the lock
alone does not prove quiescence until the exact new deployment/process and its
maintenance health have been verified. Retire the prior process, inspect active
work/reservations, preserve spending history, and obtain a fresh coordinated
backup before any migration. The schema21-compatible rollback and native plan
must be prepared before entering maintenance. Do not restart an old schema20-only
version against upgraded storage or restore old spending ledgers over new usage.
Leaving maintenance requires validated migration state and the matching native
transition; deployment success/health200 alone does not establish readiness.

## Executed evidence

Three maintenance tests and the impacted hosted startup test passed. These spawn
actual hosted.py processes and make actual HTTP/WebSocket requests. The maintenance
process runs without provider credentials against intentionally invalid SQLite
sentinel bytes; it reports truthful health, denies ten work/worker-health routes
and an account WebSocket upgrade, leaves both files byte-identical, and creates
only its two lockfiles. A duplicate service fails its singleton lock. The operator
lease can be held throughout maintenance but prevents normal startup before a
ledger file is opened. Conversely a running normal service blocks the operator
lease. The existing startup/crash-recovery test still preserves usage and marks
an interrupted reservation correctly. No provider calls or paid spending.

```sh
/tmp/ellis-auth-venv/bin/python -m unittest discover -s Backend -p 'test_maintenance.py' -v
/tmp/ellis-auth-venv/bin/python -m unittest discover -s Backend -p 'test_hosted_startup.py' -v
```

This is evidence for the local startup/exclusion mechanism. It does not prove
Render process turnover, a completed offline operator run, live migration or
physical phone acceptance. No production flag has been enabled.
