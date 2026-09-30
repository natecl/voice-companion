"""Atomic content erasure, not an authenticated account-deletion endpoint.

The caller must first revoke the account's sessions and provider grants. This
module only owns memory.sqlite; it cannot delete usage ledgers, device files or
backups. Never call it for ordinary note deletion or founder-data migration.
"""
from admission import Rejected


SCHEMA = '''
BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS erased_account(owner TEXT PRIMARY KEY, erased_at REAL NOT NULL);
CREATE TABLE IF NOT EXISTS erased_account_credential(
 credential TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES erased_account(owner));
CREATE TRIGGER IF NOT EXISTS prevent_erased_owner_recreation BEFORE INSERT ON owner
 WHEN EXISTS(SELECT 1 FROM erased_account WHERE owner=NEW.id)
 BEGIN SELECT RAISE(ABORT, 'account_erased'); END;
PRAGMA user_version=21;
COMMIT;
'''

# Children precede parents. Tables without an owner column are handled explicitly
# below. Keep this inventory aligned with migrations; the coverage test fails when
# a new application table has no erasure policy.
OWNER_TABLES = (
    'proactive_connection', 'proactive_attempt', 'companion_dependency',
    'companion_request', 'companion_turn', 'companion_chat', 'companion_snapshot',
    'memory_correction', 'memory_identity_support', 'memory_identity_link',
    'memory_mention', 'memory_entity', 'memory_fact_evidence', 'support', 'claim',
    'memory_embedding', 'memory_index_job', 'retained_recording', 'recording_notes',
    'job', 'source', 'account_identity', 'credential_owner',
)
INDEX_TABLES = ('memory_passage_index', 'recording_note_index')
CHILD_TABLES = ('memory_correction_link', 'claim_relation_proposal', 'job_result', 'memory_chunk')


def require_live_credential(db, credential):
    if db.execute('SELECT 1 FROM erased_account_credential WHERE credential=?', (credential,)).fetchone():
        raise Rejected('account_erased')


def erase_content(store, owner):
    """Erase one provider-enrolled owner; retry safely after an uncertain response.

Retain only random owner/credential IDs and completion time to reject stale
credential rebinding. No provider subject, transcript or answer is retained here.
Deleting the owner also prevents late worker INSERTs through existing foreign
keys; their stale leases no longer exist. All changes commit or roll back together.
"""
    with store.transaction() as db:
        if db.execute('SELECT 1 FROM erased_account WHERE owner=?', (owner,)).fetchone():
            return {'status': 'erased'}
        if not db.execute('SELECT 1 FROM account_identity WHERE owner=?', (owner,)).fetchone():
            raise Rejected('account_not_enrolled')
        db.execute('INSERT INTO erased_account VALUES(?,?)', (owner, store.clock()))
        db.execute('INSERT INTO erased_account_credential SELECT credential,owner '
                   'FROM credential_owner WHERE owner=?', (owner,))
        db.execute('DELETE FROM memory_correction_link WHERE correction IN '
                   '(SELECT id FROM memory_correction WHERE owner=?)', (owner,))
        db.execute('DELETE FROM claim_relation_proposal WHERE claim IN '
                   '(SELECT id FROM claim WHERE owner=?)', (owner,))
        for table in ('job_result', 'memory_chunk'):
            db.execute(f'DELETE FROM {table} WHERE job IN (SELECT id FROM job WHERE owner=?)', (owner,))
        for table in INDEX_TABLES:
            db.execute(f'DELETE FROM {table} WHERE owner=?', (owner,))
            # Core secure_delete alone does not purge old FTS posting lists.
            # Rebuild from remaining content, without changing other owners' rows.
            db.execute(f"INSERT INTO {table}({table}) VALUES('rebuild')")
        for table in OWNER_TABLES:
            db.execute(f'DELETE FROM {table} WHERE owner=?', (owner,))
        db.execute('DELETE FROM owner WHERE id=?', (owner,))
    return {'status': 'erased'}
