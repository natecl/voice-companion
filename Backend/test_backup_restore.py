"""Disposable populated SQLite + actual operator CLI; no server or provider calls."""
import asyncio
from contextlib import contextmanager, closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock

from account_deletion import AccountDeletion
from account_migration import migrate_offline
from account_erasure import OWNER_TABLES, INDEX_TABLES, CHILD_TABLES
from account_sessions import AccountSessions
from account_tokens import GOOGLE, VerifiedIdentity
from admission import Admission, Rejected
from backup_restore import prepare, validate, digest, rows
from cryptography.fernet import Fernet
from maintenance import database_lease
from memory_store import MemoryStore
from provider_grants import ProviderGrants
import test_account_erasure


@contextmanager
def database(path):
    with closing(sqlite3.connect(path)) as db, db:
        yield db


class BackupRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.directory = self.root/'current'; self.directory.mkdir()
        (self.directory/'database.lock').touch(mode=0o600)
        self.store = MemoryStore(self.directory/'memory.sqlite', embedding_model='fixture-model-v1')
        self.admission = Admission(self.directory/'usage.sqlite', total_microusd=100, limits={'ask': (100,20,3)})
        self.addCleanup(self.admission.close)
        self.sessions = AccountSessions(self.admission, self.store)
        self.grants = ProviderGrants(self.admission, Fernet.generate_key())
        self.a, self.b = self.enroll('fictional-a'), self.enroll('fictional-b')
        self.owner, self.other = self.a['owner'], self.b['owner']
        self.credential = self.admission.authorized(self.a['token'])
        for owner in (self.owner, self.other):
            test_account_erasure.AccountErasureTests.populate(self, owner)
        with self.store.transaction() as db:
            db.execute("UPDATE proactive_attempt SET state='silence'")
            db.execute("UPDATE memory_index_job SET state='done',lease=NULL")
        self.snapshot = self.root/'old-memory.sqlite'
        self.store.backup(self.snapshot)
        self.output = self.root/'quarantine'
        # New spending after snapshot: it must not be rolled back.
        self.admission.db.execute("INSERT INTO request VALUES('latest-spend',?,'ask',1,20,'completed')", (self.credential,))
        self.delete()

    def enroll(self, subject):
        challenge = self.sessions.challenge('google')
        return self.sessions.exchange(challenge['challenge'], 'google',
            VerifiedIdentity(GOOGLE, subject, int(self.admission.clock())+300), 'proof-'+subject)

    def delete(self):
        deletion = AccountDeletion(self.sessions, self.grants, Mock(), google=Mock())
        async def quiet(owner):
            pass
        deletion.quiesce = quiet
        self.assertEqual(asyncio.run(deletion.delete(self.a['refresh_token'])), {'status': 'awaiting_google_revocation'})
        self.assertEqual(asyncio.run(deletion.finish_google(self.a['refresh_token'], 'fictional-grant')), {'status': 'deleted'})

    def pins(self):
        return dict(snapshot_hash=digest(self.snapshot), memory_hash=digest(self.directory/'memory.sqlite'),
                    usage_hash=digest(self.directory/'usage.sqlite'))

    def prepare(self):
        return prepare(self.directory, self.snapshot, self.output, **self.pins())

    def cli(self, *args, success=True):
        result = subprocess.run([sys.executable, str(Path(__file__).with_name('backup_restore.py')), *args],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0 if success else 1, result.stderr)
        self.assertNotIn('fictional-', result.stdout + result.stderr)
        return json.loads(result.stdout) if success else result

    def cli_prepare(self, success=True):
        args = ['prepare', '--directory', str(self.directory), '--snapshot', str(self.snapshot), '--output', str(self.output)]
        for key, value in self.pins().items():
            args += ['--'+key.replace('_','-'), value]
        return self.cli(*args, success=success)

    def test_actual_cli_populated_deletion_and_validation(self):
        before = self.pins()
        result = self.cli_prepare()
        self.assertEqual(result['replayed_deletions'], 1)
        self.assertFalse(result['activation_supported'])
        self.assertEqual(self.pins(), before)
        self.assertEqual(digest(self.output/'usage.sqlite'), before['usage_hash'])
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)
        for name in ('memory.sqlite', 'usage.sqlite', 'manifest.json'):
            self.assertEqual((self.output/name).stat().st_mode & 0o777, 0o600)
        with database(self.snapshot) as old, database(self.output/'memory.sqlite') as new:
            for table in OWNER_TABLES + INDEX_TABLES:
                self.assertGreater(old.execute(f'SELECT count(*) FROM {table} WHERE owner=?', (self.owner,)).fetchone()[0], 0, table)
                self.assertEqual(new.execute(f'SELECT count(*) FROM {table} WHERE owner=?', (self.owner,)).fetchone()[0], 0, table)
                self.assertEqual(old.execute(f'SELECT * FROM {table} WHERE owner=? ORDER BY rowid', (self.other,)).fetchall(),
                                 new.execute(f'SELECT * FROM {table} WHERE owner=? ORDER BY rowid', (self.other,)).fetchall(), table)
            for table in CHILD_TABLES:
                self.assertEqual(len(rows(new, table))*2, len(rows(old, table)), table)
                self.assertTrue(rows(new, table) <= rows(old, table), table)
        restored = MemoryStore(self.output/'memory.sqlite')
        with self.assertRaisesRegex(Rejected, 'account_erased'):
            restored.owner_for(self.credential)
        restored_admission = Admission(self.output/'usage.sqlite', total_microusd=100, limits={'ask': (100,20,3)})
        try:
            with self.assertRaisesRegex(Rejected, 'unauthorized'):
                restored_admission.authorized(self.a['token'])
            with self.assertRaisesRegex(Rejected, 'unauthorized'):
                AccountSessions(restored_admission, restored).refresh(self.a['refresh_token'])
        finally:
            restored_admission.close()
        # Constructors are idempotent and did not invalidate the prepared hashes.
        checked = self.cli('validate', '--output', str(self.output), '--manifest-hash', result['manifest_sha256'])
        self.assertEqual(checked['status'], 'validated_quarantine')

    def test_rotation_preserves_current_credentials_and_all_usage(self):
        rotated = self.sessions.refresh(self.b['refresh_token'])
        expected = self.pins()
        self.prepare()
        with database(self.output/'memory.sqlite') as new, self.store.connect() as current:
            self.assertEqual(rows(new, 'credential_owner'), {tuple(r) for r in current.execute('SELECT * FROM credential_owner')})
        self.assertEqual(digest(self.output/'usage.sqlite'), expected['usage_hash'])
        self.assertEqual(MemoryStore(self.output/'memory.sqlite').owner_for(self.admission.authorized(rotated['token'])), self.other)

    def test_pending_deletion_cli_refusal(self):
        self.admission.db.execute("UPDATE account_deletion SET state='pending'")
        self.cli_prepare(success=False)
        self.assertFalse(self.output.exists())

    def test_reenrollment_refused(self):
        self.admission.db.execute('DELETE FROM account_exchange')
        self.enroll('fictional-a')
        with self.assertRaisesRegex(ValueError, 'Owner mapping changed'):
            self.prepare()

    def test_founder_identity_migration_refused(self):
        legacy_credential, _ = self.admission.enroll()
        legacy = self.store.owner_for(legacy_credential)
        google = self.enroll('fictional-founder')
        self.snapshot = self.root/'before-migration.sqlite'
        self.store.backup(self.snapshot)
        identity = dict(source_owner=legacy, google_owner=google['owner'], google_subject='fictional-founder')
        plan = migrate_offline(self.store.path, self.directory/'usage.sqlite', **identity)
        migrated = migrate_offline(self.store.path, self.directory/'usage.sqlite', **identity, expected_plan=plan['plan'])
        self.assertEqual(migrated['status'], 'applied')
        with self.assertRaisesRegex(ValueError, 'Identity mapping changed'):
            self.prepare()

    def test_new_owner_refused(self):
        self.store.owner_for('new-legacy-owner')
        with self.assertRaisesRegex(ValueError, 'Owner mapping changed'):
            self.prepare()

    def test_missing_current_and_unknown_schema_refused(self):
        usage = self.directory/'usage.sqlite'
        usage.rename(self.directory/'missing.sqlite')
        with self.assertRaises(ValueError):
            prepare(self.directory, self.snapshot, self.output, snapshot_hash=digest(self.snapshot), memory_hash=digest(self.store.path), usage_hash='0'*64)
        (self.directory/'missing.sqlite').rename(usage)
        with database(self.snapshot) as db:
            db.execute('CREATE TABLE unreviewed(value TEXT)')
        with self.assertRaisesRegex(ValueError, 'Unreviewed database schema'):
            self.prepare()

    def test_active_work_refused_in_snapshot_current_and_usage(self):
        for path in (self.snapshot, self.store.path):
            for table, active in (('job', 'running'), ('memory_index_job', 'queued'),
                                  ('recording_notes', 'generating'), ('companion_turn', 'pending'),
                                  ('proactive_attempt', 'pending')):
                with database(path) as db:
                    original = db.execute(f'SELECT rowid,state FROM {table} WHERE owner=?', (self.other,)).fetchall()
                    self.assertTrue(original, table)
                    db.execute(f'UPDATE {table} SET state=? WHERE owner=?', (active, self.other))
                with self.assertRaisesRegex(ValueError, 'Active work'):
                    self.prepare()
                with database(path) as db:
                    db.executemany(f'UPDATE {table} SET state=? WHERE rowid=?', [(state, rowid) for rowid, state in original])
        self.admission.db.execute("UPDATE request SET state='active'")
        with self.assertRaisesRegex(ValueError, 'Active work'):
            self.prepare()

    def test_lease_and_sqlite_writers_excluded(self):
        with database_lease(self.directory):
            with self.assertRaises(BlockingIOError):
                self.prepare()
        with database(self.snapshot) as db:
            db.execute('BEGIN IMMEDIATE')
            with self.assertRaises(sqlite3.OperationalError):
                self.prepare()
        self.assertFalse(self.output.exists())

    def test_sidecars_and_symlinks_refused(self):
        sidecar = Path(str(self.snapshot)+'-wal'); sidecar.touch()
        with self.assertRaisesRegex(ValueError, 'sidecar'):
            self.prepare()
        sidecar.unlink()
        link = self.root/'alias.sqlite'; link.symlink_to(self.snapshot)
        with self.assertRaisesRegex(ValueError, 'canonical regular'):
            prepare(self.directory, link, self.output, **self.pins())

    def test_inconsistent_deletion_and_unrevoked_credentials_refused(self):
        self.admission.db.execute('UPDATE credential SET revoked=0 WHERE id=?', (self.credential,))
        with self.assertRaisesRegex(ValueError, 'Deleted session'):
            self.prepare()
        self.admission.db.execute('UPDATE credential SET revoked=1 WHERE id=?', (self.credential,))
        self.admission.db.execute('DELETE FROM google_deletion')
        self.admission.db.execute('DELETE FROM account_deletion')
        with self.assertRaisesRegex(ValueError, 'tombstones disagree'):
            self.prepare()

    def test_existing_canonical_single_link_lease_required(self):
        lease = self.directory/'database.lock'
        lease.unlink()
        with self.assertRaisesRegex(ValueError, 'single-link'):
            self.prepare()
        self.assertFalse(lease.exists())
        target = self.root/'lease-target'; target.touch()
        lease.symlink_to(target)
        with self.assertRaisesRegex(ValueError, 'single-link'):
            self.prepare()
        lease.unlink(); lease.hardlink_to(target)
        with self.assertRaisesRegex(ValueError, 'single-link'):
            self.prepare()
        lease.unlink(); lease.mkdir()
        with self.assertRaisesRegex(ValueError, 'single-link'):
            self.prepare()
        lease.rmdir(); lease.touch(mode=0o600)
        result = self.prepare()
        lease.unlink()
        with self.assertRaisesRegex(ValueError, 'single-link'):
            validate(self.output, result['manifest_sha256'])
        self.assertFalse(lease.exists())

    def test_private_quarantine_required_for_validation(self):
        result = self.prepare()
        self.output.chmod(0o755)
        with self.assertRaisesRegex(ValueError, 'private canonical'):
            validate(self.output, result['manifest_sha256'])
        self.output.chmod(0o700)
        for name in ('memory.sqlite', 'usage.sqlite', 'manifest.json'):
            path = self.output/name
            path.chmod(0o644)
            with self.assertRaisesRegex(ValueError, 'private quarantine artifacts'):
                validate(self.output, result['manifest_sha256'])
            path.chmod(0o600)
            link = self.root/'extra-link'; link.hardlink_to(path)
            with self.assertRaisesRegex(ValueError, 'single-link'):
                validate(self.output, result['manifest_sha256'])
            link.unlink()
            path.rename(link); path.symlink_to(link)
            with self.assertRaisesRegex(ValueError, 'single-link'):
                validate(self.output, result['manifest_sha256'])
            path.unlink(); link.rename(path)
        alias = self.root/'quarantine-link'; alias.symlink_to(self.output)
        with self.assertRaisesRegex(ValueError, 'private canonical'):
            validate(alias, result['manifest_sha256'])

    def test_post_snapshot_source_deletion_refused(self):
        self.store.delete_source(self.other, 'session-a')
        self.assertIsNone(self.store.source(self.other, 'session-a'))
        before = self.pins()
        self.cli_prepare(success=False)
        self.assertFalse((self.output/'manifest.json').exists())
        self.assertEqual(self.pins(), before)

    def test_post_snapshot_correction_refused(self):
        with self.store.transaction() as db:
            db.execute("UPDATE claim SET text='Fictional corrected claim' WHERE owner=?", (self.other,))
        with self.assertRaisesRegex(ValueError, 'Historical content differs'):
            self.prepare()
        self.assertFalse((self.output/'manifest.json').exists())

    def test_hash_tampering_and_overwrite_refused(self):
        wrong = self.pins(); wrong['snapshot_hash'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'hash changed'):
            prepare(self.directory, self.snapshot, self.output, **wrong)
        result = self.prepare()
        with self.assertRaisesRegex(ValueError, 'new quarantine'):
            self.prepare()
        manifest_hash = result['manifest_sha256']
        for path in (self.snapshot, self.store.path, self.directory/'usage.sqlite', self.output/'memory.sqlite', self.output/'usage.sqlite', self.output/'manifest.json'):
            original = path.read_bytes()
            path.write_bytes(original + b'tampered')
            with self.assertRaisesRegex(ValueError, 'hash changed'):
                validate(self.output, manifest_hash)
            path.write_bytes(original)
        self.assertEqual(validate(self.output, manifest_hash)['status'], 'validated_quarantine')


if __name__ == '__main__':
    unittest.main()
