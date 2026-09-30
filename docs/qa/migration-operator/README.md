# Offline founder migration operator

September 30, 2026. Candidate stacked on PR168; no live changes.

`Backend/migration_operator.py` makes the reviewed migration primitive executable
without a public administration endpoint. An operator supplies a private identity
JSON file with exactly `source_owner`, `google_owner`, `google_subject`, independently
verified through the phone source and fresh provider proof. IDs/subjects remain
outside Git and shell arguments; CLI output contains only status/counts.

## Required operating sequence

Verify the exact new deployed maintenance process and retirement of the old
process first. Old hosted versions do not participate in database.lock. Confirm
no unresolved active work, preserve the native baseline and fresh local snapshot,
and prepare a matching schema21-compatible rollback. Do not run this command
against an ordinary live service or substitute lockfile existence for quiescence.
The private plan and all backups must remain protected operator artifacts.

```sh
python Backend/migration_operator.py prepare --directory /private/data/root \
 --identity-file /private/verified-identity.json --plan /private/migration-plan.json
python Backend/migration_operator.py apply --plan /private/migration-plan.json
```

**Prepare modifies schema; it is not a read-only dry run.** Under the exclusive
database lease it checks existing memory/usage databases and rollback journals,
locks all root SQLite databases while taking coordinated SQLite backups, checks
backup integrity, then upgrades memory20 to21 and initializes account-deletion
tables without opening/reconfiguring spending policies. It invokes the primitive's
strict identity/content guards, fingerprints all prepared database files, and
saves the plan with private permissions. It will not overwrite an existing plan.
Backup files are mode0600 in a private directory. If preparation fails, remain in
maintenance and inspect the retained backup/schema state; never assume no schema
changes occurred or delete artifacts to force a retry.

Apply holds the same exclusive lease and refuses changed database files, changed
backup files, added/removed databases or an incompatible plan. It passes the exact
primitive fingerprint to the atomic identity/revocation operation. Successful
replay is refused because the prepared files changed. If a response is lost,
inspect actual identity/session state; never blindly rerun or restore historical
ledgers over later usage. The command does not deploy, toggle maintenance, alter
native files, prove a human's identity or authorize itself to migrate arbitrary
owners. The retained native owner references remain unchanged.

## Evidence

Three operator tests pass, including actual CLI subprocesses for prepare/apply,
plan privacy, logical backup equality/integrity, success/replay refusal, changed
backup/ledger refusal, runtime lease refusal and existing-plan protection. Initial
fixtures omitted the deployed Apple-grant table; fixed the fixture rather than
bypassing the migration guard. The initial backup assertion incorrectly required
SQLite backup files to have identical raw headers; it now compares complete SQL
dumps and integrity, while hashes still detect later backup tampering.

The actual CLI then ran on a fresh copy of the 24 coordinated hosted databases.
All 24 backups matched pristine schema/row dumps. Prepare upgraded schema20 to21;
apply preserved the original content owner and revoked five affected credentials.
Every row in 42 memory and 18 usage tables was compared with exactly two allowed
changes: selected Google identity owner and affected credential revoked flags.
All other rows matched, the other 22 database files remained byte-identical, and
all pristine download hashes still matched. The receipt pins the operator source
hash. Private databases, identity file, plan and rehearsal script stay outside Git.

No hosted/phone changes or paid calls. Render maintenance transition, coordinated
live cutover and physical Release acceptance remain required.

```sh
/tmp/ellis-auth-venv/bin/python -m unittest discover -s Backend -p 'test_migration_operator.py' -v
```
