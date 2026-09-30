# Backup and restore gap — September 30, 2026

Read-only inspection of the current hosted data directory found 24 top-level
SQLite databases and 464 nested backup/QA database or archive files, totaling
41,709,568 bytes across both groups. The oldest observed modification time was
September 25. These counts are an inventory, not a deletion list: nested files
include historical spending ledgers as well as content copies. Nothing was
deleted, restored or reconfigured.

The migration operator makes coordinated SQLite-native backups under the
database lease, but has no general retention or restore command. Current account
erasure writes tombstones in memory.sqlite and preserves deletion/session state
in usage.sqlite. Those protections can disappear if both files are replaced by
an older snapshot. The existing instruction against restoring old ledgers is
necessary but does not yet provide an executable restore gate.

Required implementation and acceptance:

- Inventory and distinguish content snapshots, current databases, spending
  ledgers, migration receipts and private off-host copies. Never expire a
  directory solely because its name includes backup or QA.
- Use a bounded, explicit retention policy for managed content snapshots and
  record expiry outcomes. Handle historical copies deliberately; no current
  policy or maximum retention promise is established by this audit.
- Preserve current spending, revoked sessions, accepted deletions and identity
  bindings when preparing a restore. Replay deletion protection before enabling
  any reader or worker. Refuse a restore when a sufficiently recent deletion
  record or identity mapping cannot be established.
- Rehearse on disposable copies: backup, delete one populated account, prepare
  restore, verify the account remains erased and stale credentials fail while
  the other owner and latest spending remain intact. Also cover pending deletion,
  re-enrollment and founder identity migration; no resurrection or owner reassignment.
- Keep restore preparation separate from live activation, with maintenance,
  hashes, integrity checks and an inspected candidate. Do not blindly restore
  an old usage ledger or replay a founder migration.

[Render persistent-disk documentation](https://render.com/docs/disks), checked
September 30, describes daily encrypted disk snapshots available for **at least**
seven days; it does not establish a seven-day maximum. It also warns against disk
snapshot restoration for custom database recovery. Application backup expiry
must therefore be distinguished from provider snapshot retention, and no bounded
provider-erasure claim should be made without supporting evidence.

This is an open release gate, not implemented retention or tested restore safety.
