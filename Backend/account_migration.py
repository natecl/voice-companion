"""Operator-only legacy-to-Google cutover primitive; never called by enrollment.

Requires stopped services/workers, coordinated backups, verified source/destination
identity, and a separate native migration. No CLI or HTTP route exposes this yet.
Use file-backed rollback-journal databases on the same filesystem so SQLite's
attached-database transaction commits the identity binding and revocations together.
"""
import hashlib
import json
from pathlib import Path
import sqlite3

from account_erasure import OWNER_TABLES, INDEX_TABLES
from admission import Rejected

GOOGLE = 'https://accounts.google.com'


def migrate_offline(memory_path, usage_path, *, source_owner, google_owner,
                    google_subject, expected_plan=None):
    """Return a read-only plan; apply only with its exact fingerprint.

An uncertain completed call must be inspected, not blindly retried: the expected
old identity binding no longer matches after success. No user content is copied,
deleted or reassigned. The empty old Google owner remains with revoked credentials.
"""
    memory_path, usage_path = Path(memory_path).resolve(), Path(usage_path).resolve()
    if (memory_path == usage_path or not memory_path.is_file() or not usage_path.is_file()
            or memory_path.stat().st_dev != usage_path.stat().st_dev):
        raise Rejected('migration_database_pair_invalid')
    if not source_owner or not google_owner or source_owner == google_owner or not google_subject:
        raise Rejected('migration_identity_invalid')
    db = sqlite3.connect(memory_path.as_uri() + '?mode=rw', uri=True, isolation_level=None, timeout=2)
    try:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        db.execute('ATTACH DATABASE ? AS usage', (usage_path.as_uri() + '?mode=rw',))
        db.execute('PRAGMA usage.synchronous=FULL')
        if any(db.execute(f'PRAGMA {name}.journal_mode').fetchone()[0] != 'delete'
               for name in ('main', 'usage')):
            raise Rejected('migration_requires_rollback_journals')
        if db.execute('PRAGMA user_version').fetchone()[0] != 21:
            raise Rejected('migration_schema_unverified')
        db.execute('BEGIN EXCLUSIVE' if expected_plan else 'BEGIN')
        for owner in (source_owner, google_owner):
            if not db.execute('SELECT 1 FROM owner WHERE id=?', (owner,)).fetchone():
                raise Rejected('migration_owner_missing')
            if db.execute('SELECT 1 FROM erased_account WHERE owner=?', (owner,)).fetchone():
                raise Rejected('migration_owner_erased')
            if db.execute('SELECT 1 FROM usage.account_deletion WHERE owner=?', (owner,)).fetchone():
                raise Rejected('migration_deletion_exists')
            if db.execute('SELECT 1 FROM usage.apple_grant WHERE owner=?', (owner,)).fetchone():
                raise Rejected('migration_provider_conflict')
        if db.execute('SELECT 1 FROM account_identity WHERE owner=?', (source_owner,)).fetchone():
            raise Rejected('migration_source_not_legacy')
        if db.execute('SELECT issuer,subject FROM account_identity WHERE owner=?', (google_owner,)).fetchall() != [(GOOGLE, google_subject)]:
            raise Rejected('migration_google_identity_changed')

        # Refuse future owner tables until their migration policy is reviewed.
        known = set(OWNER_TABLES + INDEX_TABLES + ('erased_account', 'erased_account_credential'))
        tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        for table in tables:
            columns = {r[1] for r in db.execute('PRAGMA table_info("' + table.replace('"', '""') + '")')}
            if 'owner' in columns and table not in known:
                raise Rejected('migration_unknown_owner_table')
        known_usage = {'account_session', 'apple_grant', 'account_deletion',
                       'deletion_recovery', 'google_deletion', 'deleting_identity'}
        for (table,) in db.execute("SELECT name FROM usage.sqlite_master WHERE type='table'").fetchall():
            columns = {r[1] for r in db.execute('PRAGMA usage.table_info("' + table.replace('"', '""') + '")')}
            if 'owner' in columns and table not in known_usage:
                raise Rejected('migration_unknown_owner_table')
        inventory = {}
        for table in OWNER_TABLES + INDEX_TABLES:
            count = db.execute(f'SELECT count(*) FROM {table} WHERE owner=?', (google_owner,)).fetchone()[0]
            # Opening chat creates only an owner/id container. Keep it untouched;
            # all turn, request, dependency and snapshot rows still block cutover.
            metadata_only = table in ('account_identity', 'credential_owner')
            if table == 'companion_chat':
                metadata_only = {r[1] for r in db.execute('PRAGMA table_info(companion_chat)')} == {'owner', 'id'}
            if not metadata_only and count:
                raise Rejected('migration_google_has_content')
            inventory[table] = db.execute(f'SELECT * FROM {table} WHERE owner IN (?,?) ORDER BY owner',
                                          (source_owner, google_owner)).fetchall()
        for table in ('account_session',):
            inventory['usage.'+table] = db.execute(f'SELECT * FROM usage.{table} WHERE owner IN (?,?)',
                                                  (source_owner, google_owner)).fetchall()
        credentials = sorted({r[0] for r in db.execute(
            'SELECT credential FROM credential_owner WHERE owner IN (?,?) UNION '
            'SELECT credential FROM usage.account_session WHERE owner IN (?,?)',
            (source_owner, google_owner, source_owner, google_owner))})
        if not credentials:
            raise Rejected('migration_credentials_missing')
        for credential in credentials:
            if db.execute("SELECT 1 FROM usage.request WHERE credential_id=? AND state='active'", (credential,)).fetchone():
                raise Rejected('migration_request_active')
        inventory['credentials'] = [db.execute('SELECT * FROM usage.credential WHERE id=?', (key,)).fetchone()
                                    for key in credentials]
        if any(row is None for row in inventory['credentials']):
            raise Rejected('migration_credentials_missing')
        # Sort every row to keep dry-run fingerprints independent of query order.
        serial = lambda value: json.dumps(value, sort_keys=True, default=lambda v: v.hex() if isinstance(v, bytes) else str(v))
        fingerprint = hashlib.sha256(serial({k: sorted(serial(r) for r in rows)
                                            for k, rows in inventory.items()}).encode()).hexdigest()
        result = dict(plan=fingerprint, credentials_to_revoke=len(credentials),
                      content_owner_preserved=True, status='planned')
        if expected_plan is not None:
            if expected_plan != fingerprint:
                raise Rejected('migration_plan_changed')
            for credential in credentials:
                db.execute('UPDATE usage.credential SET revoked=1 WHERE id=?', (credential,))
            db.execute('UPDATE account_identity SET owner=? WHERE issuer=? AND subject=? AND owner=?',
                       (source_owner, GOOGLE, google_subject, google_owner))
            if db.execute('PRAGMA foreign_key_check').fetchall() or db.execute('PRAGMA usage.foreign_key_check').fetchall():
                raise Rejected('migration_integrity_failed')
            result['status'] = 'applied'
        db.execute('COMMIT')
        return result
    except BaseException:
        if db.in_transaction:
            db.execute('ROLLBACK')
        raise
    finally:
        db.close()
