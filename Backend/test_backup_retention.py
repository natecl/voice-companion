"""Managed-file worker and real hosted-process evidence on disposable data only."""
import asyncio
from contextlib import closing
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.request import urlopen

from admission import Admission
from backup_retention import RetentionWorker, STATUS_FILE, settings
from managed_backups import (ROOT, digest, expire_registered, lease, registry_lease,
                             snapshot, snapshot_read_lease)
from maintenance import database_lease


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        (self.directory / 'database.lock').touch(mode=0o600)
        for name in ('memory.sqlite', 'usage.sqlite'):
            with closing(sqlite3.connect(self.directory / name)) as db:
                db.execute('CREATE TABLE evidence(value TEXT)')
                db.execute('INSERT INTO evidence VALUES (?)', (name,))
                db.commit()
        self.manifest = snapshot(self.directory, 10, clock=lambda: 100)
        self.folder = self.directory / ROOT / self.manifest['id']


class RetentionTests(Fixture):
    def test_explicit_settings(self):
        self.assertIsNone(settings({}))
        self.assertEqual(settings({'VOICE_MANAGED_BACKUP_EXPIRY_ENABLED': '1',
                                   'VOICE_MANAGED_BACKUP_SCAN_SECONDS': '60'}), 60)
        for env in ({'VOICE_MANAGED_BACKUP_EXPIRY_ENABLED': 'yes'},
                    {'VOICE_MANAGED_BACKUP_EXPIRY_ENABLED': '1'},
                    {'VOICE_MANAGED_BACKUP_SCAN_SECONDS': '1'}):
            with self.assertRaises(ValueError): settings(env)
        for interval in ('0', '-1', '1.5', 'inf', '86401', '１２'):
            with self.assertRaises(ValueError):
                settings({'VOICE_MANAGED_BACKUP_EXPIRY_ENABLED': '1',
                          'VOICE_MANAGED_BACKUP_SCAN_SECONDS': interval})

    def test_prune_while_runtime_lease_held_opens_only_snapshot_databases(self):
        hashes = {p.name: digest(p) for p in self.directory.glob('*.sqlite')}
        connect = sqlite3.connect
        opened = []
        def snapshot_only(path, *args, **kwargs):
            self.assertIn('/managed-backups/', str(path))
            opened.append(str(path))
            return connect(path, *args, **kwargs)
        with database_lease(self.directory):
            # Reproduce why the former prune lease cannot run in a live service.
            with self.assertRaises(BlockingIOError):
                with lease(self.directory): pass
            with patch('managed_backups.sqlite3.connect', snapshot_only):
                result = expire_registered(self.directory, clock=lambda: 110)
        self.assertEqual(result['expired_count'], 1)
        self.assertTrue(opened)
        self.assertEqual(hashes, {p.name: digest(p) for p in self.directory.glob('*.sqlite')})
        self.assertEqual(len(list((self.directory / ROOT).glob('automatic-prune-plan-*.json'))), 1)

    def test_registry_lock_excludes_creation_prune_and_managed_reads(self):
        with registry_lease(self.directory):
            with self.assertRaises(BlockingIOError): snapshot(self.directory, 10, clock=lambda: 100)
            with self.assertRaises(BlockingIOError): expire_registered(self.directory, clock=lambda: 110)
            with self.assertRaises(BlockingIOError):
                with snapshot_read_lease(self.folder / 'memory.sqlite'): pass
        with snapshot_read_lease(self.folder / 'memory.sqlite'):
            with self.assertRaises(BlockingIOError): expire_registered(self.directory, clock=lambda: 110)
        self.assertEqual(expire_registered(self.directory, clock=lambda: 110)['expired_count'], 1)

    def test_restore_obeys_managed_registry_lock(self):
        from test_backup_restore import BackupRestoreTests
        fixture = BackupRestoreTests(); fixture.setUp()
        try:
            folder = fixture.directory / ROOT / ('a' * 32)
            folder.mkdir(parents=True, mode=0o700)
            fixture.snapshot.rename(folder / 'memory.sqlite')
            fixture.snapshot = folder / 'memory.sqlite'
            with registry_lease(fixture.directory), self.assertRaises(BlockingIOError):
                fixture.prepare()
            self.assertFalse(fixture.output.exists())
            result = fixture.prepare()
            self.assertEqual(result['status'], 'quarantined')
            from backup_restore import validate
            with registry_lease(fixture.directory), self.assertRaises(BlockingIOError):
                validate(fixture.output, result['manifest_sha256'])
        finally:
            fixture.doCleanups()

    def test_worker_scans_immediately_then_periodically(self):
        async def scenario():
            clock = [109]
            worker = RetentionWorker(self.directory, 1, clock=lambda: clock[0])
            task = asyncio.create_task(worker.run())
            for _ in range(100):
                if worker.status['scan_count'] == 1: break
                await asyncio.sleep(.01)
            self.assertEqual(worker.status['next_expiry'], 110)
            self.assertTrue(self.folder.exists())
            clock[0] = 110
            for _ in range(200):
                if worker.status['scan_count'] == 2: break
                await asyncio.sleep(.01)
            worker.stop.set(); await task
            self.assertEqual(worker.status['pruned_count'], 1)
            self.assertFalse(self.folder.exists())
            status = self.directory / STATUS_FILE
            self.assertEqual(status.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(status.read_text())['state'], 'stopped')
        asyncio.run(scenario())

    def test_tampering_stops_worker_and_restart_does_not_retry(self):
        (self.folder / 'usage.sqlite').write_bytes(b'fictional tampering')
        worker = RetentionWorker(self.directory, 1, clock=lambda: 110)
        asyncio.run(worker.run())
        self.assertEqual(worker.status['state'], 'failed')
        self.assertEqual(worker.status['scan_count'], 0)
        self.assertTrue((self.folder / 'memory.sqlite').exists())
        with patch('backup_retention.expire_registered', side_effect=AssertionError('must not retry')) as expire:
            restarted = RetentionWorker(self.directory, 1, clock=lambda: 111)
            asyncio.run(restarted.run())
            expire.assert_not_called()
        self.assertEqual(restarted.status['state'], 'failed')

    def test_recognized_failed_status_is_preserved_exactly_on_restart(self):
        previous = RetentionWorker(self.directory, 1).status
        previous.update(state='failed', scan_count=7, pruned_count=3,
                        last_success_at=101, next_expiry=120, failure='OSError')
        path = self.directory / STATUS_FILE
        path.write_text(json.dumps(previous, indent=4) + '\n')
        path.chmod(0o600)
        before = path.read_bytes()
        with patch('backup_retention.expire_registered') as expire:
            worker = RetentionWorker(self.directory, 1, clock=lambda: 110)
            asyncio.run(worker.run())
            expire.assert_not_called()
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(worker.status, previous)
        self.assertTrue(self.folder.exists())

    def test_unknown_automatic_plan_is_preserved_while_new_plan_is_exclusive(self):
        root = self.directory / ROOT
        unknown = root / 'automatic-prune-plan.json'
        unknown.write_bytes(b'unknown operator evidence')
        unknown.chmod(0o600)
        result = expire_registered(self.directory, clock=lambda: 110)
        self.assertEqual(result['expired_count'], 1)
        self.assertEqual(unknown.read_bytes(), b'unknown operator evidence')
        plans = list(root.glob('automatic-prune-plan-*.json'))
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].stat().st_mode & 0o777, 0o600)
        receipt = json.loads((root / 'registry.json').read_text())['expired'][0]
        self.assertEqual(digest(plans[0]), receipt['plan_sha256'])

    def test_registry_busy_is_deferred_without_plan_or_deletion_then_expires(self):
        async def scenario():
            worker = RetentionWorker(self.directory, 1, clock=lambda: 110)
            with registry_lease(self.directory):
                task = asyncio.create_task(worker.run())
                for _ in range(100):
                    if worker.status['state'] == 'deferred': break
                    await asyncio.sleep(.01)
                self.assertEqual(worker.status['state'], 'deferred')
                self.assertTrue(self.folder.exists())
                self.assertEqual(list((self.directory / ROOT).glob('automatic-prune-plan-*.json')), [])
                self.assertFalse((self.directory / ROOT / 'prune-pending.json').exists())
            for _ in range(200):
                if worker.status['pruned_count'] == 1: break
                await asyncio.sleep(.01)
            worker.stop.set(); await task
            self.assertEqual(worker.status['pruned_count'], 1)
            self.assertIsNone(worker.status['failure'])
            self.assertFalse(self.folder.exists())
        asyncio.run(scenario())

    def test_unknown_status_file_is_preserved(self):
        path = self.directory / STATUS_FILE
        for contents in ('{"unrecognized": "preserve"}', 'not valid json'):
            with self.subTest(contents=contents):
                path.write_text(contents)
                path.chmod(0o600)
                before = path.read_bytes()
                worker = RetentionWorker(self.directory, 1, clock=lambda: 110)
                asyncio.run(worker.run())
                self.assertEqual(worker.status['state'], 'failed')
                self.assertEqual(path.read_bytes(), before)
                self.assertTrue(self.folder.exists())

    def test_interrupted_prune_stops_without_retry(self):
        original = Path.unlink
        def interrupted(path, *args, **kwargs):
            if path.name == 'manifest.json': raise OSError('fictional interruption')
            return original(path, *args, **kwargs)
        worker = RetentionWorker(self.directory, 1, clock=lambda: 110)
        with patch.object(Path, 'unlink', interrupted):
            asyncio.run(worker.run())
        self.assertEqual(worker.status['state'], 'failed')
        self.assertTrue((self.directory / ROOT / 'prune-pending.json').exists())
        with self.assertRaisesRegex(ValueError, 'Interrupted prune'):
            expire_registered(self.directory, clock=lambda: 111)


class HostedRetentionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name).resolve()
        (self.directory / 'database.lock').touch(mode=0o600)
        with closing(sqlite3.connect(self.directory / 'memory.sqlite')) as db:
            db.execute('CREATE TABLE fixture(value TEXT)'); db.commit()
        admission = Admission(self.directory / 'usage.sqlite', total_microusd=5_000_000,
                              limits={'stt': (2_000_000, 20_000, 6)})
        admission.enroll(); admission.close()
        self.manifest = snapshot(self.directory, 10, clock=lambda: int(time.time()) - 100)
        self.folder = self.directory / ROOT / self.manifest['id']
        self.hashes = {p.name: digest(p) for p in self.directory.glob('*.sqlite')}
        (self.directory / 'old-backup-usage.sqlite').write_bytes(b'unknown historical ledger')
        (self.directory / ROOT / 'unknown').mkdir()
        (self.directory / ROOT / 'unknown' / 'keep').write_bytes(b'unknown content')

    def process(self, *, enabled, maintenance=False):
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
        env = {k: v for k, v in os.environ.items() if not k.startswith('VOICE_')}
        env.update(VOICE_DATA_DIR=str(self.directory), PORT=str(port), XAI_API_KEY='unused-local-fixture')
        if enabled:
            env.update(VOICE_MANAGED_BACKUP_EXPIRY_ENABLED='1', VOICE_MANAGED_BACKUP_SCAN_SECONDS='1')
        if maintenance: env['VOICE_MAINTENANCE'] = '1'
        process = subprocess.Popen([sys.executable, str(Path(__file__).with_name('hosted.py'))],
                                   env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: self.stop_process(process))
        for _ in range(200):
            try:
                with urlopen(f'http://127.0.0.1:{port}/health', timeout=.1) as result:
                    self.assertEqual(result.status, 200)
                break
            except OSError:
                if process.poll() is not None: self.fail(process.communicate())
                time.sleep(.01)
        else: self.fail('Hosted process did not become ready')
        return process, port

    @staticmethod
    def stop_process(process):
        if process.poll() is None: process.terminate()
        process.communicate(timeout=5)

    def assert_pruned(self):
        for _ in range(200):
            path = self.directory / STATUS_FILE
            if path.exists():
                status = json.loads(path.read_text())
                if status['state'] == 'idle' and status['pruned_count'] == 1: break
                if status['state'] == 'failed': self.fail(status)
            time.sleep(.01)
        else: self.fail('No successful expiry status')
        self.assertFalse(self.folder.exists())
        self.assertEqual(self.hashes, {name: digest(self.directory / name) for name in self.hashes})
        self.assertEqual((self.directory / 'old-backup-usage.sqlite').read_bytes(), b'unknown historical ledger')
        self.assertEqual((self.directory / ROOT / 'unknown' / 'keep').read_bytes(), b'unknown content')

    def test_running_hosted_service_prunes_with_runtime_lease_held(self):
        _, port = self.process(enabled=True)
        self.assert_pruned()
        with self.assertRaises(BlockingIOError):
            with database_lease(self.directory): pass
        with urlopen(f'http://127.0.0.1:{port}/health', timeout=1) as response:
            self.assertEqual(response.read(), b'ready\n')

    def test_disabled_then_restart_catches_up(self):
        process, _ = self.process(enabled=False)
        self.assertTrue(self.folder.exists())
        self.assertFalse((self.directory / STATUS_FILE).exists())
        self.stop_process(process)
        self.process(enabled=True)
        self.assert_pruned()

    def test_maintenance_expiry_preserves_active_database_bytes(self):
        self.process(enabled=True, maintenance=True)
        self.assert_pruned()
        with database_lease(self.directory): pass


if __name__ == '__main__':
    unittest.main()
