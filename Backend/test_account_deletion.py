"""Local deletion workflow and real sockets; provider revocation is a fixture."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import AsyncMock, Mock, patch

from cryptography.fernet import Fernet
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import InvalidStatus
from account_deletion import AccountDeletion
from account_sessions import AccountSessions
from account_service import AccountService
from account_tokens import GOOGLE, APPLE, VerifiedIdentity
from admission import Admission, Rejected
from memory_store import MemoryStore
from provider_grants import ProviderGrants
from relay import Relay
from test_memory import source


class AccountDeletionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)
        self.now = 100000
        self.admission = Admission(self.path / 'usage.sqlite', total_microusd=100,
                                   limits={'stt': (100, 20, 5)}, clock=lambda: self.now)
        self.addCleanup(self.admission.close)
        self.memory = MemoryStore(self.path / 'memory.sqlite')
        self.sessions = AccountSessions(self.admission, self.memory)
        self.key = Fernet.generate_key()
        self.grants = ProviderGrants(self.admission, self.key)
        self.apple = Mock()
        self.deletion = AccountDeletion(self.sessions, self.grants, self.apple)
        self.deletion.quiesce = AsyncMock()
        self.sequence = 0

    def enroll(self, subject='fictional-a', provider='google'):
        self.sequence += 1
        identity = VerifiedIdentity(GOOGLE if provider == 'google' else APPLE, subject, self.now + 300, 'phone')
        challenge = self.sessions.challenge(provider)
        return self.sessions.exchange(challenge['challenge'], provider, identity, 'fictional-token-' + str(self.sequence))

    def state(self, owner):
        return self.admission.db.execute('SELECT state FROM account_deletion WHERE owner=?', (owner,)).fetchone()[0]

    async def test_delete_revokes_all_devices_preserves_other_owner_and_charges(self):
        first, second, other = self.enroll(), self.enroll(), self.enroll('fictional-b')
        for account in (first, other):
            self.memory.put_source(account['owner'], source())
        request = self.admission.reserve(first['token'], 'stt')
        self.admission.finish(request, completed=True)
        ledger = self.admission.db.execute('SELECT * FROM request').fetchall()
        self.assertEqual(await self.deletion.delete(first['refresh_token']), {'status': 'deleted'})
        for account in (first, second):
            with self.assertRaises(Rejected): self.admission.authorized(account['token'])
            with self.assertRaises(Rejected): self.sessions.refresh(account['refresh_token'])
        self.admission.authorized(other['token'])
        self.assertEqual(self.memory.source(other['owner'], 'session-a'), source())
        self.assertIsNone(self.memory.source(first['owner'], 'session-a'))
        self.assertEqual(ledger, self.admission.db.execute('SELECT * FROM request').fetchall())
        self.assertEqual(self.state(first['owner']), 'complete')
        self.assertNotEqual(self.enroll()['owner'], first['owner'])
        self.apple.revoke.assert_not_called()

    async def test_provider_failure_survives_restart_and_blocks_enrollment(self):
        account = self.enroll(provider='apple')
        self.grants.save_apple(account['owner'], 'phone', 'fictional-apple-refresh')
        self.memory.put_source(account['owner'], source())
        self.apple.revoke.side_effect = Rejected('identity_provider_unavailable')
        with self.assertRaises(Rejected): await self.deletion.delete(account['refresh_token'])
        self.assertEqual(self.state(account['owner']), 'pending')
        self.assertIsNotNone(self.memory.source(account['owner'], 'session-a'))
        with self.assertRaises(Rejected): self.admission.authorized(account['token'])
        with self.assertRaisesRegex(Rejected, 'account_deletion_pending'): self.enroll(provider='apple')
        self.apple.revoke.assert_called_once_with('phone', 'fictional-apple-refresh')
        self.sessions = AccountSessions(self.admission, MemoryStore(self.memory.path))
        self.deletion = AccountDeletion(self.sessions, ProviderGrants(self.admission, self.key), self.apple)
        self.deletion.quiesce = AsyncMock()
        self.apple.revoke.side_effect = None
        self.now += 40 * 86400  # An accepted deletion can finish after its app session expires.
        self.assertEqual(await self.deletion.delete(account['refresh_token']), {'status': 'deleted'})
        self.assertEqual(self.grants.apple_for(account['owner']), [])
        self.assertEqual(self.state(account['owner']), 'complete')
        self.assertEqual(self.apple.revoke.call_count, 2)
        await self.deletion.delete(account['refresh_token'])
        self.assertEqual(self.apple.revoke.call_count, 2)

    async def test_partial_grant_revocation_only_retries_unfinished_client(self):
        account = self.enroll(provider='apple')
        self.grants.save_apple(account['owner'], 'a-phone', 'phone-refresh')
        self.grants.save_apple(account['owner'], 'b-mac', 'mac-refresh')
        self.apple.revoke.side_effect = [None, Rejected('identity_provider_unavailable')]
        with self.assertRaises(Rejected): await self.deletion.delete(account['refresh_token'])
        self.assertEqual(self.grants.apple_for(account['owner']), [('b-mac', 'mac-refresh')])
        self.apple.revoke.side_effect = None
        await self.deletion.delete(account['refresh_token'])
        self.assertEqual([call.args[0] for call in self.apple.revoke.call_args_list], ['a-phone', 'b-mac', 'b-mac'])

    async def test_incomplete_quiescence_never_erases_or_calls_provider(self):
        account = self.enroll(provider='apple')
        self.grants.save_apple(account['owner'], 'phone', 'refresh')
        self.memory.put_source(account['owner'], source())
        self.deletion.quiesce.side_effect = TimeoutError()
        with self.assertRaises(TimeoutError): await self.deletion.delete(account['refresh_token'])
        self.assertEqual(self.state(account['owner']), 'pending')
        self.assertIsNotNone(self.memory.source(account['owner'], 'session-a'))
        self.apple.revoke.assert_not_called()
        self.deletion.quiesce.side_effect = None
        await self.deletion.delete(account['refresh_token'])
        self.assertIsNone(self.memory.source(account['owner'], 'session-a'))

    async def test_interrupted_final_receipt_retries_erased_storage_idempotently(self):
        account = self.enroll()
        from account_erasure import erase_content
        def interrupted(store, owner):
            erase_content(store, owner)
            raise RuntimeError('fixture crash after content commit')
        with patch('account_deletion.erase_content', side_effect=interrupted):
            with self.assertRaises(RuntimeError): await self.deletion.delete(account['refresh_token'])
        with self.assertRaisesRegex(Rejected, 'account_deletion_pending'): self.enroll()
        self.assertEqual(await self.deletion.delete(account['refresh_token']), {'status': 'deleted'})
        self.assertNotEqual(self.enroll()['owner'], account['owner'])

    def test_deletion_configuration_is_explicit_and_default_off(self):
        from account_service import configured_accounts
        env = {'VOICE_ENABLE_ACCOUNTS': '1', 'VOICE_ACCOUNT_ENCRYPTION_KEY': self.key.decode()}
        with patch('account_tokens.AccountTokenVerifier'), patch('apple_oauth.AppleOAuth'):
            self.assertIsNone(configured_accounts(env, self.admission, self.memory).deletion)
            self.assertIsNotNone(configured_accounts(dict(env, VOICE_ENABLE_ACCOUNT_DELETION='1'), self.admission, self.memory).deletion)
            with self.assertRaisesRegex(ValueError, 'Invalid account deletion feature flag'):
                configured_accounts(dict(env, VOICE_ENABLE_ACCOUNT_DELETION='yes'), self.admission, self.memory)

    async def test_unauthorized_or_unwired_request_has_no_effect(self):
        account = self.enroll()
        for token in ('short', 'unknown-' * 8):
            with self.assertRaises(Rejected): await self.deletion.delete(token)
        self.deletion.quiesce = None
        with self.assertRaisesRegex(Rejected, 'account_deletion_unavailable'):
            await self.deletion.delete(account['refresh_token'])
        self.assertEqual(self.admission.db.execute('SELECT count(*) FROM account_deletion').fetchone()[0], 0)
        self.admission.authorized(account['token'])

    async def test_real_socket_endpoint_cancels_only_target_owner_and_retries(self):
        first, other = self.enroll(), self.enroll('fictional-b')
        arrived = {a['token']: asyncio.Event() for a in (first, other)}
        stopped = {a['token']: asyncio.Event() for a in (first, other)}
        class HeldContent:
            async def handle(_, socket):
                token = socket.request.headers['Authorization'].removeprefix('Bearer ')
                arrived[token].set()
                try:
                    await socket.wait_closed()
                finally:
                    stopped[token].set()
        service = AccountService(self.sessions, Mock(), grants=self.grants, apple_oauth=self.apple, deletion=self.deletion)
        relay = Relay('unused', admission=self.admission, accounts=service, memory=HeldContent())
        async with serve(relay.handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
            url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}'
            async def request(**fields):
                async with connect(url + '/account') as ws:
                    await ws.send(json.dumps(dict(version=1, **fields)))
                    return json.loads(await ws.recv())
            async with connect(url + '/memory', additional_headers={'Authorization': 'Bearer ' + first['token']}) as a:
                async with connect(url + '/memory', additional_headers={'Authorization': 'Bearer ' + other['token']}) as b:
                    await asyncio.wait_for(asyncio.gather(*(event.wait() for event in arrived.values())), 2)
                    args = dict(operation='delete_account', refresh_token=first['refresh_token'], confirmation='delete_account')
                    malformed = await request(**args, owner=other['owner'])
                    self.assertEqual(malformed['message'], 'invalid_account_request')
                    self.assertFalse(stopped[first['token']].is_set())
                    self.assertEqual((await request(**args))['status'], 'deleted')
                    await asyncio.wait_for(a.wait_closed(), 2)
                    self.assertTrue(stopped[first['token']].is_set())
                    self.assertFalse(stopped[other['token']].is_set())
                    await b.ping()
                    self.assertEqual((await request(**args))['status'], 'deleted')
                    with self.assertRaises(InvalidStatus) as denied:
                        async with connect(url + '/memory', additional_headers={'Authorization': 'Bearer ' + first['token']}): pass
                    self.assertEqual(denied.exception.response.status_code, 401)

    async def test_idle_socket_does_not_hold_account_mutation_lock(self):
        service = AccountService(self.sessions, Mock(), grants=self.grants, apple_oauth=self.apple, deletion=self.deletion)
        relay = Relay('unused', admission=self.admission, accounts=service)
        async with serve(relay.handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
            url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/account'
            async with connect(url):
                async with connect(url) as active:
                    await active.send(json.dumps(dict(version=1, operation='challenge', provider='google')))
                    result = json.loads(await asyncio.wait_for(active.recv(), 1))
                    self.assertEqual(result['type'], 'account_result')

    async def test_pending_apple_exchange_rejects_before_redeeming_new_grant(self):
        account = self.enroll(provider='apple')
        self.deletion.begin(account['refresh_token'])
        verifier = Mock()
        verifier.verify.return_value = VerifiedIdentity(APPLE, 'fictional-a', self.now + 300, 'phone')
        service = AccountService(self.sessions, verifier, grants=self.grants, apple_oauth=self.apple, deletion=self.deletion)
        relay = Relay('unused', admission=self.admission, accounts=service)
        async with serve(relay.handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
            challenge = self.sessions.challenge('apple')
            async with connect(f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/account') as ws:
                await ws.send(json.dumps(dict(version=1, operation='exchange', provider='apple',
                    challenge=challenge['challenge'], identity_token='fixture', authorization_code='fixture')))
                self.assertEqual(json.loads(await ws.recv())['message'], 'account_deletion_pending')
        self.apple.redeem.assert_not_called()


if __name__ == '__main__': unittest.main()
