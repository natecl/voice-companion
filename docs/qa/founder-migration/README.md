# Legacy owner to Google: offline storage primitive

September 30, 2026. Dependent on PR165; no hosted migration or deployment.

`Backend/account_migration.py` prepares a fingerprinted plan for a verified
legacy owner and exact existing Google identity. Applying that same plan keeps
all content under the legacy owner, changes only the Google identity binding,
and revokes source/destination credentials. The empty former Google owner and
its revoked credential mappings remain; historical budget rows are untouched.
Fresh verified Google enrollment subsequently receives the preserved owner.
Apple accounts and grants remain separate.

This operator-only primitive is not exposed by HTTP or a CLI. Its caller must
stop service/workers, take coordinated backups, verify source and destination
proof, and perform the separate native migration. It is not safe to substitute
an arbitrary owner ID or email comparison for those prerequisites. The existing
phone source was identified separately in the migration preparation document.

The function rejects nonempty destinations, changed identity/plan, enrolled
sources, deletion history, Apple grants, active affected requests, missing
credentials, unknown owner tables, unverified schema versions and WAL journals.
It opens existing files only. Identity update and credential revocation share
one attached-database transaction with FULL synchronization. SQLite documents
multi-file atomicity for file-backed non-WAL databases:
[ATTACH transaction guarantees](https://www.sqlite.org/lang_attach.html).
Both files must be on the same filesystem; journal mode is inspected, not changed.
After uncertain success, inspect state: blind replay is rejected rather than
revoking newly issued sessions.

## Executed evidence

`account-tests.txt`: 65 account regression tests passed, including eleven new
migration checks using actual temporary SQLite databases. They verify data and
Apple grant preservation, budget/policy/completed-reservation preservation,
old-session rejection and fresh Google owner selection; plan/identity/content
and active-work rejection; unknown-table refusal; WAL rejection; and rollback
of credential revocations when the binding update fails. No provider calls,
live database changes or physical-device acceptance are claimed.

The initial test run failed in a test assertion that passed an invalid fabricated
value to the credential digest validator after a successful cutover. Replaced
that assertion with inspection of the actual revoked Google credential's preserved
mapping. The application migration path was not weakened. The final regression
run above includes the additional future-entitlement inventory guard.

Reproduce:

```sh
/tmp/ellis-auth-venv/bin/python -m unittest discover -s Backend -p 'test_account*.py' -v
```

## Current hosted-copy rehearsal

`hosted-copy-rehearsal.json` records the September 30 rehearsal of the exact
migration module hash. A coordinated private snapshot held write locks across
all 24 hosted SQLite databases while copying. Downloaded hashes matched the
remote manifest. Original copies remain private and unchanged; a separate set
was upgraded from memory schema 20 to 21 and given the account-deletion tables
before migration comparisons. No live account/content migration occurred.

The first plan stopped with `migration_google_has_content`: opening chat had
created an empty `companion_chat` container. Inspection confirmed its only
columns are owner and ID, with zero destination turns or other content. The
migration now preserves this metadata row and still rejects every destination
turn, dependency, request or snapshot. A future additional chat column also
blocks migration. Three regression checks cover these distinctions; the refusal
was not bypassed by deleting data.

A second rehearsal began from fresh pristine copies. It verified the physical
app's previously inventoried legacy owner and the sole existing hosted Google
identity; this selection is **not fresh authenticated Google proof**. The plan
made no row changes. Applying it changed exactly the selected identity's owner
and five affected credentials' revoked flags. All rows in 42 memory tables and
18 usage tables were compared against precisely those allowed changes. All
other rows, including Apple content/grants and budget history, stayed identical.
The other 22 database files stayed byte-identical. Integrity and foreign-key
checks passed. The private script and databases remain outside Git; the receipt
contains no raw owners, subjects, credentials or personal content. No provider
or model call was made.

## Remaining gates

Fresh Google identity proof, operator orchestration/service quiescence, native legacy
sign-in transition and owner-scoped file migration, interruption/restart
acceptance, reviewed matching deployment and physical cutover remain required.
This bounded primitive is not a completed founder migration or full Phase 1.
