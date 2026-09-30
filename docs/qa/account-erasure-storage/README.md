# Account content erasure storage checkpoint — September 30

Dependency: draft PR159 at `8568a20`; branch `codex/account-erasure-storage`. This is a local schema-21 storage prerequisite, **not complete account deletion, a deployed change, or TestFlight acceptance**. Native/shared UI is unchanged. Live schema remains 20.

`account_erasure.erase_content` removes an enrolled owner's transcripts, notes, FTS entries, embeddings, learner jobs/results, retained quotes and memories, identity/correction graphs, chat/dependencies, snapshots, proactive bookkeeping, provider identity and credential bindings in one SQLite transaction. Only random erased owner/credential IDs and completion time remain, preventing old credentials from silently obtaining new owners. Fresh provider enrollment may create a new empty owner. Legacy founder owners are refused; migration is separate.

The owner row is removed, so existing foreign keys reject late content inserts; existing job/lease checks reject late results. Erasure failures roll back content and tombstones together. The caller must revoke all account sessions and provider grants first. No runtime caller or public endpoint exists in this checkpoint.

Both FTS indexes are rebuilt from remaining rows inside the same transaction. SQLite documents that core secure-delete alone may leave FTS traces; [FTS rebuilding](https://www.sqlite.org/fts5.html#the_rebuild_command) discards and reconstructs the index. This is logical active-database erasure, not a forensic storage, historical-backup or external-provider erasure guarantee. A release retention/restore policy remains required. Rebuilding both indexes adds transaction work proportional to their remaining contents; hosted volume/latency is not yet measured.

## Verification

Python 3.13 / SQLite 3.50.4; isolated temporary databases and fictional identities/content only. No provider calls, personal data, device mutation or live database writes.

```sh
PYTHONPATH=Backend /tmp/ellis-auth-venv/bin/python -m unittest discover -s Backend -p 'test_account*.py'
PYTHONPATH=Backend /tmp/ellis-auth-venv/bin/python -m unittest test_memory test_companion_chat test_companion_snapshots test_recording_notes test_memory_identity test_memory_atomic test_memory_vectors test_memory_indexing
/tmp/ellis-auth-venv/bin/python scripts/qa/account-erasure.py --output docs/qa/account-erasure-storage/replay.json
```

- 34 account tests pass, including eight new erasure cases. The graph fixture fills every application content table, including retained quotes and corrections; it tests storage relationships, not model output quality. Another owner's rows survive exactly. Migration/reopen/backup retains tombstones, old credentials cannot rebind, fresh enrollment starts empty, founder/unknown owners are refused, and a forced final-delete failure rolls everything back. Late learning, notes, chat, source sync and embedding writes cannot resurrect content.
- 68 impacted storage tests pass. Five migration assertions advance from schema 20 to 21. Three older synthetic downgrade fixtures now remove the account-identity table before replaying its migration; the original fixture setup caused an already-existing-table error. Production migrations were not weakened to bypass this error.
- The [replay receipt](replay.json) records exact implementation/script hashes. Actual localhost WebSockets accepted both populated owners, rejected cross-owner writes, rejected both revoked owner sessions with HTTP 401, and continued accepting the untouched owner. Actual storage APIs reopened that owner's original transcript, note and chat. Synthetic reservation rows were unchanged. Re-enrollment obtained a new empty owner. This is manually composed local revocation + storage behavior, not an account-deletion endpoint test.

Initial fixture-development failures (wrong fixture helper name, invalid failure code and incomplete graph/JSON setup) were corrected in test setup. The first broad storage run found stale schema assertions and the three downgrade-fixture errors described above. No acceptance criterion was removed to obtain passing results.

## Remaining lifecycle work

Authenticated/resumable deletion orchestration must prevent concurrent enrollment/refresh from reviving a deleting account, revoke Apple grants, quiesce in-flight work and prevent response delivery after deletion. Native confirmation and removal of local account files, caches and outboxes must reuse current UI components. Operational backup expiration and restore-time deletion replay must be defined and verified. Historical budget reservations stay charged. Existing-founder migration requires its own explicit source/target contract and preservation check. Full provider/device acceptance remains on PR159's release gates.

Do not deploy schema 21 with a schema-20-only rollback binary. Do not restore old backups over later usage or deletion records. This checkpoint performs no production deletion.
