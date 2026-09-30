# Offline account-deletion-safe candidate preparation

This checkpoint provides **prepare and validate only**. It does not activate a
restore, expire backups, implement retention, or complete the disaster-recovery
or account-erasure release gate. No deployed database, device, provider, or
private QA data was used. All acceptance inputs are disposable fictional SQLite
fixtures; provider revocation is mocked at its boundary.

**Narrow equivalence gate:** after account-erasure replay, every canonical
application table outside current authentication/tombstone state must equal the
authoritative current database. Post-snapshot ordinary recording deletion,
correction, or other content changes cause refusal and no manifest is published.
FTS virtual/shadow index representation is excluded from this comparison; source,
note, claim, correction and provenance tables are included. This deliberately
conservative gate cannot recover arbitrary historical content and is not a
general recovery system. Activation remains unsupported.

## Authority and limits

An operator must establish that `memory.sqlite` and `usage.sqlite` are the actual
latest coordinated authoritative generation, under stopped readers/workers and
an implementation that honors `database.lock`. The latest accepted deletions,
revoked sessions, identity bindings, and spending history must survive
independently of any old content snapshot before that snapshot is usable.
**Caller-supplied hashes cannot prove freshness or authenticity.** They bind the
selected files and detect changes; independently record and retain them and the
returned manifest hash. Pointing this command at an old pair with newly computed
hashes does not establish authority. If current authoritative state is lost or
its provenance is uncertain, do not prepare a candidate.

The input snapshot contains historical memory only. Historical usage is never
accepted. The current usage database is copied byte-for-byte, preserving every
spending, reservation, challenge, exchange, session, provider-grant and deletion
row. Surviving owners and provider identities must match exactly between snapshot
and current state after removing completed deletions. Ordinary credential
rotation is supported by installing current credential mappings. Owner additions,
re-enrollment, and founder identity migration are refused; there is no heuristic
identity merge, email match, or migration replay.

For surviving owners, no content merge or reconciliation is attempted. Their
snapshot content must already be equivalent to the authoritative current
canonical application tables. This blocks resurrection of ordinary recording
deletions and rollback of corrections. It also refuses new or otherwise changed
content, even when a future reviewed recovery policy could safely handle it.
Strict equality is the supported boundary of this prepare-only checkpoint.

Only the exact reviewed schema21 memory and full account-enabled usage schemas
are accepted. Schema hashes cover tables, indexes, triggers, and SQL definitions,
not just `user_version`. Unknown schemas, noncanonical/symlink paths, journal
sidecars, unavailable current files, pending deletion, incomplete provider
revocation markers, inconsistent tombstones, active/queued work, and contention
for the runtime lease or SQLite write locks are refused. The existing runtime
lease must already be a canonical regular single-link file; preparation and
validation never create a missing lease. All input files must be single-link.
Validation rejects a nonprivate quarantine (directory mode other than 0700 or
artifact mode other than 0600), symlinks and hard-linked artifacts. A historical snapshot
with active work must be separately reviewed; the operator does not silently
clear or reschedule jobs. Schema fingerprint differences from historical
migration forms also require explicit review.

Preparation creates a new mode-0700 quarantine containing mode-0600
`memory.sqlite`, `usage.sqlite`, and `manifest.json`. It never overwrites an
existing output or modifies original input bytes. Existing `erase_content`
replays completed account erasures into the copy, including FTS rebuilds;
current tombstone and identity/credential tables then replace their historical
counterparts. Integrity, foreign-key, canonical-content equivalence, account-state and byte-hash checks precede
the manifest. A failure after copying leaves an unmanifested private quarantine
for operator inspection; it is never eligible for validation or activation.
Neither this command nor its validator protects against a malicious operator or
host filesystem administrator who can replace both trusted evidence and inputs.

## Operator interface

Resolve input paths to their canonical absolute locations first. Do not copy
these placeholders into a live environment. Pins come from the independent
review of the authoritative generation, not from an unverified recovered pair.

```sh
PYTHONPATH=Backend python Backend/backup_restore.py prepare \
  --directory /canonical/current \
  --snapshot /canonical/backups/old-memory.sqlite \
  --output /canonical/quarantine/new-candidate \
  --snapshot-hash VERIFIED_SNAPSHOT_SHA256 \
  --memory-hash VERIFIED_CURRENT_MEMORY_SHA256 \
  --usage-hash VERIFIED_CURRENT_USAGE_SHA256

PYTHONPATH=Backend python Backend/backup_restore.py validate \
  --output /canonical/quarantine/new-candidate \
  --manifest-hash INDEPENDENTLY_RETAINED_PREPARE_RESULT_SHA256
```

`prepare` reports `quarantined`, deletion count, the manifest hash and
`activation_supported: false`. The private manifest records input paths/hashes
and candidate hashes. `validate` holds the same exclusive lease and SQLite write
locks, checks schema/integrity/account relationships and all pinned hashes, and
reports `validated_quarantine`. Any changed current state invalidates this
candidate; create a new one after reviewing the new authoritative generation.
Validation is a point-in-time observation, not an activation authorization.
There is no apply or activate subcommand.

## Reproducible local acceptance

From the repository root with backend dependencies installed:

```sh
PYTHONPATH=Backend python -W error::ResourceWarning -m unittest Backend.test_backup_restore
PYTHONPATH=Backend python -m unittest Backend.test_account_erasure Backend.test_migration_operator
PYTHONPATH=Backend python docs/qa/backup-restore/rehearse.py
```

The first suite executes the actual CLI in subprocesses. It enrolls two
fictional accounts, populates every account-owned content table and child graph,
makes a memory snapshot, records later spending, completes one account deletion
through the local deletion workflow, prepares a quarantined candidate, and
validates it. It inspects that all erased-owner rows are absent, all unrelated
owner rows and child rows survive, the complete latest usage file is identical,
and stale access, refresh, and owner-rebinding credentials fail. It also tests
current credential rotation, real local founder migration refusal,
re-enrollment/new-owner refusal, pending deletion, active work, missing current
state, unknown schema, runtime/SQLite contention, sidecar/symlink rejection,
inconsistent deletion records, unrevoked sessions, missing/nonregular/linked lease,
nonprivate/linked quarantine, post-snapshot source deletion and correction, output overwrite rejection,
and tampering with each input, each candidate database and the manifest.

The fixture constructs current schemas with the real runtime constructors;
matching hard-coded schema hashes is therefore exercised as part of every test.
No test establishes live-provider deletion, independently durable latest-state
storage, retention expiry, hosted activation, or physical-device behavior.
