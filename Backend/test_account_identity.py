"""Synthetic identities only: does not establish Google/Apple token verification."""
import concurrent.futures
import json
from pathlib import Path
import tempfile
import unittest

from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from admission import Admission, Rejected
from memory_store import MemoryStore
from memory_service import MemoryService
from relay import Relay
from test_memory import source

GOOGLE = 'https://accounts.google.com'
APPLE = 'https://appleid.apple.com'


class AccountIdentityTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / 'memory.sqlite'
        self.store = MemoryStore(self.path)

    def bind(self, credential, subject='person-a', issuer=GOOGLE):
        return self.store.owner_for_identity(credential, issuer=issuer, subject=subject)

    def test_reauthentication_and_restart_keep_owner_and_sources(self):
        owner = self.bind('first-session')
        self.store.put_source(owner, source())
        self.store = MemoryStore(self.path)
        self.assertEqual(self.bind('second-session'), owner)
        self.assertEqual(self.store.owner_for('second-session'), owner)
        self.assertEqual(self.store.source(owner, 'session-a'), source())
        self.assertEqual(self.bind('first-session'), owner)

    def test_provider_subject_pair_is_identity_not_email_or_subject_alone(self):
        owners = {self.bind('google-a'), self.bind('google-b', 'person-b'),
                  self.bind('apple-a', issuer=APPLE)}
        self.assertEqual(len(owners), 3)
        with self.assertRaises(TypeError):
            self.store.owner_for_identity('extra', issuer=GOOGLE, subject='a', email='same@example.test')

    def test_existing_credentials_cannot_be_adopted_or_reassigned(self):
        founder = self.store.owner_for('founder')
        self.store.put_source(founder, source())
        owner = self.bind('account-session')
        for credential, subject in [('founder', 'person-a'), ('founder', 'new-person'),
                                     ('account-session', 'new-person')]:
            with self.assertRaisesRegex(Rejected, 'owner_conflict'):
                self.bind(credential, subject)
        self.assertEqual(self.store.owner_for('founder'), founder)
        self.assertEqual(self.store.source(founder, 'session-a'), source())
        self.assertIsNone(self.store.source(owner, 'session-a'))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM account_identity').fetchone()[0], 1)

    def test_invalid_identity_never_mutates_owner_tables(self):
        for issuer, subject in [('https://evil.test', 'a'), (GOOGLE, ''), (APPLE, None),
                                (GOOGLE, 'a\nb'), (APPLE, 'x' * 256), (GOOGLE, 42)]:
            with self.assertRaisesRegex(Rejected, 'invalid_account_identity'):
                self.bind('attempt', subject, issuer)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM owner').fetchone()[0], 0)

    def test_concurrent_first_sessions_get_one_owner(self):
        def bind(i):
            return self.bind(f'session-{i}')
        with concurrent.futures.ThreadPoolExecutor(4) as executor:
            owners = list(executor.map(bind, range(8)))
        self.assertEqual(len(set(owners)), 1)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM owner').fetchone()[0], 1)
            self.assertEqual(db.execute('SELECT count(*) FROM credential_owner').fetchone()[0], 8)

    def test_version_19_upgrade_and_backup_keep_founder_content(self):
        owner = self.store.owner_for('founder')
        self.store.put_source(owner, source())
        with self.store.connect() as db:
            db.execute('DROP TABLE account_identity')
            db.execute('PRAGMA user_version=19')
        self.store = MemoryStore(self.path)
        self.assertEqual(self.store.owner_for('founder'), owner)
        self.assertEqual(self.store.source(owner, 'session-a'), source())
        account = self.bind('new-account')
        backup = Path(self.directory.name) / 'backup.sqlite'
        self.store.backup(backup)
        restored = MemoryStore(backup)
        self.assertEqual(restored.owner_for_identity('restored-session', issuer=GOOGLE,
                                                   subject='person-a'), account)
        self.assertEqual(restored.source(owner, 'session-a'), source())


class AccountSocketTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_owners_reauthentication_and_cross_owner_rejection(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            ledger = Admission(path / 'usage.sqlite', total_microusd=100,
                               limits={'stt': (100, 20, 6)})
            self.addCleanup(ledger.close)
            store = MemoryStore(path / 'memory.sqlite')
            sessions = []
            for subject in ('person-a', 'person-b', 'person-a'):
                credential, token = ledger.enroll()
                owner = store.owner_for_identity(credential, issuer=GOOGLE, subject=subject)
                sessions.append((credential, token, owner))
            first, other, renewed = sessions
            self.assertEqual(first[2], renewed[2])
            self.assertNotEqual(first[2], other[2])
            relay = Relay('unused', admission=ledger, memory=MemoryService(ledger, store))
            async with serve(relay.handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
                url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/memory'
                async def request(session, **data):
                    async with connect(url, additional_headers={'Authorization': 'Bearer ' + session[1]}) as client:
                        await client.send(json.dumps(dict(version=1, **data)))
                        return json.loads(await client.recv())
                ack = await request(first, owner=first[2], operation='upsert', source=source())
                self.assertEqual(ack['status'], 'stored')
                ack = await request(renewed, owner=renewed[2], operation='upsert', source=source())
                self.assertEqual(ack['status'], 'unchanged')
                for operation in [dict(operation='upsert', source=source(text='Overwrite attempt')),
                                  dict(operation='delete', session_id='session-a')]:
                    ack = await request(other, owner=first[2], **operation)
                    self.assertEqual(ack['message'], 'memory_owner_mismatch')
                self.assertEqual(store.source(first[2], 'session-a'), source())
                self.assertIsNone(store.source(other[2], 'session-a'))
                ledger.revoke(first[0])
                from websockets.exceptions import InvalidStatus
                with self.assertRaises(InvalidStatus) as revoked:
                    await request(first, owner=first[2], operation='upsert', source=source())
                self.assertEqual(revoked.exception.response.status_code, 401)
                ack = await request(renewed, owner=renewed[2], operation='upsert', source=source())
                self.assertEqual(ack['status'], 'unchanged')
            self.assertEqual(ledger.usage(), [])


if __name__ == '__main__':
    unittest.main()
