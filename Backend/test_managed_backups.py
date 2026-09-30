from contextlib import closing
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from maintenance import database_lease
from managed_backups import (MAX_TIMESTAMP, ROOT, apply_prune, digest, inspect_set,
                             plan_prune, registry, snapshot)


class ManagedBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve()
        (self.directory / 'database.lock').touch()
        for name in ('memory.sqlite', 'usage.sqlite', 'qa-budget.sqlite'):
            with closing(sqlite3.connect(self.directory / name)) as db:
                db.execute('CREATE TABLE evidence(value TEXT)')
                db.execute('INSERT INTO evidence VALUES (?)', (name,))
                db.commit()
        self.original = {p.name: digest(p) for p in self.directory.glob('*.sqlite')}
        self.plan = self.directory / 'plan.json'

    def create(self):
        return snapshot(self.directory, 10, clock=lambda: 100)

    def prepare(self):
        return plan_prune(self.directory, self.plan, clock=lambda: 110)['plan_sha256']

    def test_expire_exact_managed_set_preserves_unknown_and_live_ledgers(self):
        historical = self.directory / 'backups' / 'old'
        historical.mkdir(parents=True)
        unknown = historical / 'usage.sqlite'
        unknown.write_bytes(b'historical spending')
        manifest = self.create()
        foreign = self.directory / ROOT / 'unknown'
        foreign.mkdir(); (foreign / 'evidence').write_text('preserve')
        root, _, data = registry(self.directory)
        self.assertEqual(inspect_set(root, manifest['id'], data['sets'][manifest['id']]), manifest)
        self.assertEqual(plan_prune(self.directory, self.directory / 'early.json', clock=lambda: 109)['expired_count'], 0)
        approval = self.prepare()
        self.assertTrue((root / manifest['id']).exists())
        self.assertEqual(apply_prune(self.plan, approval, clock=lambda: 111)['expired_count'], 1)
        self.assertFalse((root / manifest['id']).exists())
        self.assertEqual(unknown.read_bytes(), b'historical spending')
        self.assertEqual((foreign / 'evidence').read_text(), 'preserve')
        self.assertEqual(self.original, {p.name: digest(p) for p in self.directory.glob('*.sqlite')})
        self.assertEqual(len(registry(self.directory)[2]['expired']), 1)
        with self.assertRaisesRegex(ValueError, 'Registry changed'):
            apply_prune(self.plan, approval, clock=lambda: 111)

    def test_invalid_retention(self):
        for duration in (None, 0, -1, True, 1.5, float('inf'), MAX_TIMESTAMP):
            with self.subTest(duration=duration), self.assertRaises(ValueError):
                snapshot(self.directory, duration, clock=lambda: 100)
        self.assertFalse((self.directory / ROOT).exists())

    def test_missing_or_busy_runtime_lease(self):
        with database_lease(self.directory), self.assertRaises(BlockingIOError):
            self.create()
        (self.directory / 'database.lock').unlink()
        with self.assertRaises(FileNotFoundError):
            self.create()

    def test_tampered_file_blocks_all_deletion(self):
        first = self.create(); second = self.create()
        approval = self.prepare()
        target = self.directory / ROOT / second['id'] / 'memory.sqlite'
        with target.open('ab') as out:
            out.write(b'tampering')
        with self.assertRaisesRegex(ValueError, 'changed'):
            apply_prune(self.plan, approval, clock=lambda: 111)
        self.assertTrue((self.directory / ROOT / first['id'] / 'memory.sqlite').exists())

    def test_plan_hash_and_registry_change(self):
        self.create(); approval = self.prepare()
        with self.assertRaisesRegex(ValueError, 'approval'):
            apply_prune(self.plan, '0' * 64, clock=lambda: 111)
        self.create()
        with self.assertRaisesRegex(ValueError, 'Registry changed'):
            apply_prune(self.plan, approval, clock=lambda: 111)

    def test_unknown_extra_file_in_registered_set_is_not_deleted(self):
        manifest = self.create(); approval = self.prepare()
        extra = self.directory / ROOT / manifest['id'] / 'unknown.txt'
        extra.write_text('preserve')
        with self.assertRaisesRegex(ValueError, 'Unexpected'):
            apply_prune(self.plan, approval, clock=lambda: 111)
        self.assertEqual(extra.read_text(), 'preserve')

    def test_missing_manifest_and_unsafe_permissions(self):
        manifest = self.create()
        path = self.directory / ROOT / manifest['id'] / 'manifest.json'
        path.chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'private'):
            self.prepare()
        path.chmod(0o600); path.unlink()
        with self.assertRaises(FileNotFoundError):
            self.prepare()

    def test_symlink_and_hardlink_rejected(self):
        manifest = self.create()
        path = self.directory / ROOT / manifest['id'] / 'memory.sqlite'
        path.unlink(); path.symlink_to(self.directory / 'memory.sqlite')
        with self.assertRaisesRegex(ValueError, 'Symlink'):
            self.prepare()
        path.unlink(); path.hardlink_to(self.directory / 'memory.sqlite')
        with self.assertRaisesRegex(ValueError, 'Hard-linked'):
            self.prepare()

    def test_registry_traversal_rejected(self):
        self.create()
        path = self.directory / ROOT / 'registry.json'
        data = json.loads(path.read_text()); data['sets']['../outside'] = '0' * 64
        path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError, 'registered'):
            self.prepare()

    def test_wal_source_rejected_without_registration(self):
        with closing(sqlite3.connect(self.directory / 'memory.sqlite')) as db:
            db.execute('PRAGMA journal_mode=WAL')
        with self.assertRaisesRegex(ValueError, 'rollback'):
            self.create()
        self.assertEqual(registry(self.directory)[2]['sets'], {})

    def test_interrupted_prune_preserves_exact_recovery_evidence(self):
        manifest = self.create(); approval = self.prepare()
        original_unlink = Path.unlink
        def fail_at_manifest(path, *args, **kwargs):
            if path.name == 'manifest.json':
                raise OSError('simulated interruption')
            return original_unlink(path, *args, **kwargs)
        with patch.object(Path, 'unlink', fail_at_manifest), self.assertRaises(OSError):
            apply_prune(self.plan, approval, clock=lambda: 111)
        journal = json.loads((self.directory / ROOT / 'prune-pending.json').read_text())
        self.assertEqual(journal['manifests'][manifest['id']], manifest)
        with self.assertRaisesRegex(ValueError, 'Interrupted prune'):
            plan_prune(self.directory, self.directory / 'retry.json', clock=lambda: 112)
        self.assertEqual(self.original, {p.name: digest(p) for p in self.directory.glob('*.sqlite')})

    def test_clock_rollback_rejected(self):
        self.create(); approval = self.prepare()
        with self.assertRaisesRegex(ValueError, 'Clock'):
            apply_prune(self.plan, approval, clock=lambda: 109)


if __name__ == '__main__':
    unittest.main()
