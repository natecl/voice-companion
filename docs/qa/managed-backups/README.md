# Managed SQLite snapshot retention — local candidate

September 30, 2026. Verified on disposable fictional databases only. This is an
operator module with no runtime scheduler or production configuration. No actual
retention policy is selected by this checkpoint. The ten-second duration below
is an injected-clock fixture, not a proposed production retention duration.

`Backend/managed_backups.py` snapshots every top-level `*.sqlite` into a new
private `managed-backups/<uuid>/` set. Both memory and usage are required. It
requires an existing regular `database.lock`, acquires the runtime's exclusive
lease, then holds SQLite `BEGIN IMMEDIATE` transactions across all sources while
using SQLite's backup API. Sources must use rollback journals. Each copy passes
`integrity_check`; a private manifest records exact database hashes, creation,
caller-supplied positive integer retention seconds and expiry. The private
registry registers that manifest hash only after successful verification.
The representable year-9999 timestamp ceiling is a numeric validation bound,
not a retention policy.

Plan creation validates every registered manifest and database, including
permissions, links and exact directory contents, then writes the expired IDs and
registry hash to a private plan. Apply requires its separately supplied SHA-256,
reacquires the lease and validates the whole set before deleting any file. It
unlinks only enumerated files and removes the now-empty registered directory;
it never recursively deletes, adopts historical directories, or selects files
by names or mtimes. Completed expiry outcomes remain in the registry. New sets
or changed content invalidate an old plan. Unknown files/directories outside a
registered set are preserved; unexpected contents inside a registered set block
pruning. Missing manifests, symlinks (including ancestor components), hardlinks,
nonprivate artifacts, clock rollback and unavailable leases block the operation.
Supply canonical absolute paths; symlink aliases such as macOS `/tmp` are rejected.

Reproduce from repository root:

```sh
PYTHONPATH=Backend /tmp/ellis-auth-venv/bin/python -m unittest Backend.test_managed_backups -v
/tmp/ellis-auth-venv/bin/python docs/qa/managed-backups/rehearse.py
```

Twelve targeted regressions pass. The real four-subprocess CLI rehearsal creates
three SQLite copies, directly inspects their integrity, plans before and at
expiry with an injected clock, and applies exactly one managed set. It verifies
unchanged hashes for all active ledgers, unchanged historical/unknown files,
non-destructive planning and a durable registry expiry receipt. See
[receipt.json](receipt.json). The temporary source/copy databases are disposed
of by the harness; no private data, provider calls, device, server or deployment
is involved. The initial test run exposed Python 3.13 connection resource
warnings; connections were explicitly closed and the final targeted run is clean.

CLI shapes (requires an already authorized offline operator environment):

```text
python Backend/managed_backups.py snapshot --directory ABSOLUTE_DATA_DIRECTORY --retention-seconds EXPLICIT_SECONDS
python Backend/managed_backups.py plan --directory ABSOLUTE_DATA_DIRECTORY --plan ABSOLUTE_PLAN_FILE
python Backend/managed_backups.py apply --plan ABSOLUTE_PLAN_FILE --expected-sha256 INSPECTED_PLAN_SHA256
```

## Interruption and trust limits

Before the first unlink, apply durably writes private `prune-pending.json` with
the inspected plan and complete selected manifests. An I/O failure or process
interruption preserves that evidence and blocks subsequent module operations.
The regression injects failure after database unlinks and verifies the journal,
blocking behavior and unchanged sources. There is deliberately no automatic
retry/recovery command: an operator must inspect the journal, registry and actual
remaining files, reconcile only the exact original hash-verified set, and record
the outcome before clearing the marker. Do not delete or adopt unknown files to
unblock it. This is fail-closed partial-failure handling, not transactional
multi-file deletion. A snapshot failure before registration similarly leaves an
unregistered orphan for explicit inspection; pruning will never adopt it.

The runtime lease only excludes participating runtime versions. Production use
still requires verifying the deployed version and maintenance state. Private
permissions and hashes protect against accidental modification; this is not a
security boundary against a privileged operator able to rewrite the registry,
plan, hashes and files or concurrently replace paths while ignoring the lease.
No restore activation is implemented here, and snapshot usage ledgers must never
be blindly substituted for current spending/deletion ledgers.

Application-copy pruning does not erase filesystem/provider disk snapshots,
historical migration/QA copies, downloaded archives, off-host copies or physical
storage remnants. Those remain separately inventoried and governed; this evidence
cannot establish a maximum retention promise or complete account erasure.
