# Automatic expiry — local candidate, disabled by default

This packet adds expiry scheduling for registered managed copies. It does not
create periodic backups, choose a retention duration, adopt historical copies,
change provider retention, enable production, or activate restores.

Configuration is explicit:

- `VOICE_MANAGED_BACKUP_EXPIRY_ENABLED=1` enables the worker. Omission means disabled.
- When enabled, `VOICE_MANAGED_BACKUP_SCAN_SECONDS` is required: an integer from
  1 to 86400. This is the scan cadence, not a content-retention duration.
- Every snapshot still requires caller-supplied `--retention-seconds`; the worker
  respects each manifest's registered expiry and never supplies a duration.

Both normal hosted startup and maintenance startup run an immediate scan followed
by periodic scans when enabled. Normal operation retains its lifetime
`database.lock`. The worker only reads/hashes/integrity-checks snapshot databases
and manages registered snapshot files; it never opens active database files.
There is no provider request, paid hosting dependency or unauthenticated endpoint.

## Coordination and exact application

`managed-backups.lock` is a private, canonical, single-link file separate from the
runtime lease. Snapshot creation acquires **database lease → registry lease**,
then keeps its existing SQLite coordination. Restore preparation/validation also
holds the registry lease when its snapshot is beneath a managed root. File-only
manual plan/apply and automatic expiry acquire only the registry lease.

An automatic scan validates every registered set, then persists
`managed-backups/automatic-prune-plan-<uuid>.json` with exclusive creation before applying that exact plan/hash
under the same lease. Each plan remains inspectable and its hash identifies the durable expiry receipt. Preexisting files, including an unknown `automatic-prune-plan.json`, are never replaced. No plan cleanup is introduced. Every successful
expiry keeps its receipt in the registry; the existing pending journal contains
the entire selected set if deletion is interrupted. Unknown/historical data are
never adopted or recursively removed.

Registry acquisition contention occurs before any plan/deletion and reports
`deferred`; the next scheduled scan tries again. Validation, actual prune,
malformed registry, pending-journal or status-write failures stop the worker.
They are not automatically retried. A persisted failed status also blocks scans
after process restart, preserving its exact original bytes, counters, timestamps and error class. This distinction prevents an ordinary snapshot/restore
from permanently disabling expiry without retrying a partially failed deletion.

## Inspection and recovery

The atomic mode-0600 file `managed-backup-retention-status.json` contains only the
module/version, state, successful scan count, pruned count, last-success time,
next future expiry and sanitized exception class. It contains no owner IDs,
transcripts, paths, provider credentials or exception messages. Counts are for
the current worker instance; registry receipts remain the durable expiry record.
Startup/failure logs identify the worker without exposing sensitive context.
Disabled startup leaves any existing status intact and creates no worker files.

Unrecognized or malformed status files are preserved, not overwritten. If a
status file cannot be written, the worker stops and logs that inspection is
required. A stale status is not proof of a running worker; compare its timestamp
with the actual process/configuration. No new health endpoint is added.

After a failure, an operator must inspect the recorded state, registry, latest
plan and any `prune-pending.json`, reconcile exact affected files and preserve an
incident receipt. Only after resolving the cause may the operator archive/remove
the recognized failed status and restart the worker. Do not clear a pending
journal or delete unknown files merely to make a retry pass. No automated
partial-prune repair is included.

## Verification

```sh
PYTHONPATH=Backend /tmp/ellis-auth-venv/bin/python -W error::ResourceWarning -m unittest Backend.test_managed_backups Backend.test_backup_retention Backend.test_backup_restore Backend.test_maintenance Backend.test_hosted_startup -v
/tmp/ellis-auth-venv/bin/python docs/qa/managed-backups/rehearse.py
```

The 46 targeted tests include four new real disposable hosted-process launches:
normal service expiry while its database lease remains held; disabled startup;
restart with immediate catch-up; and maintenance-mode expiry. They verify intact
active ledger hashes, preserved historical/unknown files and healthy local
service responses. No provider request occurs; the service uses an unused dummy
credential with provider features disabled.

Other regressions reproduce the former database-lease obstruction, assert that
the janitor opens only managed snapshot databases, cover immediate and periodic
scans, registry contention then safe expiry, snapshot/prune and restore/prune
exclusion, private status, malformed/foreign and recognized-failure status preservation, unknown-plan preservation, tampering,
interrupted deletion and no failed-operation retry across restart. The prior
four-subprocess CLI rehearsal remains passing. Raw targeted results are in
[automatic-expiry-tests.txt](automatic-expiry-tests.txt).

Expiry occurs on the next successful scan, with scan runtime, downtime and
coordination delays. This does not establish a strict wall-clock maximum during
service outages, contention or operator-dependent failures. Historical migration
copies, downloaded archives, provider snapshots and off-host copies remain
outside this module. Production duration, enablement and deployment are still
separate review/authorization gates.

One intervening combined run hit the existing maintenance test's readiness poll
timeout. Its output is preserved in
[automatic-expiry-startup-timeout.txt](automatic-expiry-startup-timeout.txt).
The isolated test passed immediately and the next unchanged combined run passed
all 44 tests at that revision. No timeout or acceptance condition was relaxed; the transient
startup timeout was not reproduced and its cause remains unestablished.
