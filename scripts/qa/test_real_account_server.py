"""Disposable resume preflight regressions. Never bind or call real providers."""
import asyncio
from contextlib import closing
import importlib.util
import fcntl
import json
import socket
from types import SimpleNamespace
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

QA = Path(__file__).resolve().parent
sys.path.insert(0, str(QA))
spec = importlib.util.spec_from_file_location('real_account_server', QA / 'real-account-server.py')
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
from account_sessions import AccountSessions
from account_tokens import GOOGLE, VerifiedIdentity
from provider_grants import ProviderGrants


class ResumeValidationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.admission = server.AccountQAAdmission(self.directory / 'usage.sqlite', total_microusd=1,
            limits={'stt': (100, 20, 5), 'ask': (100, 20, 5)})
        self.memory = server.MemoryStore(self.directory / 'memory.sqlite')
        self.sessions = AccountSessions(self.admission, self.memory)
        self.grants = ProviderGrants(self.admission, server.Fernet.generate_key())
        for name in ('cert.pem', 'key.pem', 'encryption.key', 'endpoint.txt'):
            (self.directory / name).write_text('unused; invalid DBs must fail first')
        (self.directory / 'status.json').write_text('{"preserve": "original status bytes"}\n')
        self.addCleanup(self.admission.close)

    def contents(self):
        return {p.name: p.read_bytes() for p in self.directory.iterdir() if p.is_file() and p.name != 'server.lock'}

    def assert_refused_without_writes(self):
        before = self.contents()
        with patch.object(server, 'AccountQAAdmission', side_effect=AssertionError('mutable initialization reached')), \
             patch.object(server, 'configured_accounts', side_effect=AssertionError('provider setup reached')), \
             patch.object(server, 'serve', side_effect=AssertionError('listener reached')):
            with self.assertRaisesRegex(RuntimeError, 'intact existing QA schema'):
                asyncio.run(server.main(self.directory, self.directory / 'unused-apple-key', resume=True))
        self.assertEqual(self.contents(), before)

    def test_empty_usage_refused_before_mutable_init_preserves_all_files(self):
        self.admission.close()
        (self.directory / 'usage.sqlite').write_bytes(b'')
        self.assert_refused_without_writes()

    def test_empty_memory_refused_before_mutable_init_preserves_all_files(self):
        (self.directory / 'memory.sqlite').write_bytes(b'')
        self.assert_refused_without_writes()

    def test_corrupt_database_refused_without_status_overwrite(self):
        (self.directory / 'memory.sqlite').write_bytes(b'not a SQLite database')
        self.assert_refused_without_writes()

    def test_missing_account_schema_refused(self):
        self.admission.db.execute('DROP TABLE account_session')
        self.assert_refused_without_writes()

    def test_incompatible_memory_version_refused(self):
        with closing(sqlite3.connect(self.directory / 'memory.sqlite')) as db:
            db.execute('PRAGMA user_version=0')
        self.assert_refused_without_writes()

    def test_wrong_required_columns_refused(self):
        self.admission.db.execute('DROP TABLE apple_grant')
        self.admission.db.execute('CREATE TABLE apple_grant(owner TEXT)')
        self.assert_refused_without_writes()

    def test_busy_lease_refused_without_writes(self):
        before = self.contents()
        with (self.directory / 'server.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaises(BlockingIOError):
                asyncio.run(server.main(self.directory, self.directory / 'unused', resume=True))
        self.assertEqual(self.contents(), before)

    def test_successful_resume_preserves_state_keys_endpoint_and_counters(self):
        challenge = self.sessions.challenge('google')
        self.sessions.exchange(challenge['challenge'], 'google',
            VerifiedIdentity(GOOGLE, 'fictional-subject', self.admission.clock() + 300), 'fictional-proof')
        server.certificate(self.directory)
        (self.directory / 'encryption.key').write_bytes(server.Fernet.generate_key())
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        (self.directory / 'endpoint.txt').write_text(f'wss://127.0.0.1:{port}/account\n')
        (self.directory / 'status.json').write_text(json.dumps(dict(
            scope='isolated local real-provider QA', model_spending_enabled=False,
            provider_calls={'apple.redeem.ok': 2})))
        apple_key = self.directory / 'fictional-apple-key'
        apple_key.write_text('unused by fictional provider setup')
        before = self.contents()
        def forbidden(*args, **kwargs):
            raise AssertionError('Real provider calls forbidden')
        accounts = SimpleNamespace(
            apple_oauth=SimpleNamespace(redeem=forbidden, validate_refresh=forbidden, revoke=forbidden),
            deletion=SimpleNamespace(google=SimpleNamespace(revoke=forbidden), quiesce=None))
        event_class = asyncio.Event
        def already_stopped():
            event = event_class(); event.set(); return event
        with patch.object(server, 'configured_accounts', return_value=accounts), \
             patch.object(server.asyncio, 'Event', already_stopped):
            asyncio.run(server.main(self.directory, apple_key, resume=True))
        after = self.contents()
        self.assertEqual({k: v for k, v in after.items() if k != 'status.json'},
                         {k: v for k, v in before.items() if k != 'status.json'})
        status = json.loads(after['status.json'])
        self.assertEqual(status['sessions'], 1)
        self.assertEqual(status['identity_counts'], {'google': 1})
        self.assertEqual(status['provider_calls'], {'apple.redeem.ok': 2})
        self.assertFalse(status['model_spending_enabled'])

    def test_valid_empty_enrollment_and_populated_schemas_are_read_only(self):
        before = self.contents()
        server.validate_resume_databases(self.directory)
        self.assertEqual(self.contents(), before)
        challenge = self.sessions.challenge('google')
        identity = VerifiedIdentity(GOOGLE, 'fictional-subject', self.admission.clock() + 300)
        self.sessions.exchange(challenge['challenge'], 'google', identity, 'fictional-proof')
        before = self.contents()
        server.validate_resume_databases(self.directory)
        self.assertEqual(self.contents(), before)


if __name__ == '__main__':
    unittest.main()
