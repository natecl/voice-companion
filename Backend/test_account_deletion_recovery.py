"""Fresh proof recovers deletion authority, never a content session."""
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from account_tokens import AccountTokenVerifier, VerifiedIdentity, GOOGLE, APPLE
from account_deletion import AccountDeletion
from account_service import AccountService
from account_sessions import AccountSessions
from admission import Rejected
from memory_store import MemoryStore
from relay import Relay
import test_account_deletion as deletion_fixtures
from test_memory import source


class DeletionRecoveryTests(unittest.IsolatedAsyncioTestCase):
    setUp = deletion_fixtures.AccountDeletionTests.setUp
    enroll = deletion_fixtures.AccountDeletionTests.enroll

    def proof(self, subject='fictional-a', provider='google'):
        self.sequence += 1
        challenge = self.sessions.challenge(provider)['challenge']
        identity = VerifiedIdentity(GOOGLE if provider == 'google' else APPLE, subject, self.now + 300, 'phone')
        return challenge, provider, identity, 'recovery-proof-' + str(self.sequence)

    async def test_recovery_rotates_only_recovery_receipt_and_never_issues_session(self):
        account = self.enroll()
        self.deletion.begin(account['refresh_token'])
        before = self.admission.db.execute('SELECT * FROM account_session').fetchall()
        first = self.deletion.recover(*self.proof())
        second = self.deletion.recover(*self.proof())
        self.assertEqual(first['owner'], account['owner'])
        self.assertNotIn('token', first)
        self.assertNotIn('refresh_token', first)
        self.assertEqual(before, self.admission.db.execute('SELECT * FROM account_session').fetchall())
        self.assertEqual(self.admission.db.execute('SELECT count(*) FROM deletion_recovery').fetchone()[0], 1)
        for operation in (lambda: self.admission.authorized(second['deletion_token']),
                          lambda: self.sessions.refresh(second['deletion_token'])):
            with self.assertRaises(Rejected): operation()
        with self.assertRaises(Rejected): await self.deletion.delete(first['deletion_token'], recovery=True)
        raw = (self.path / 'usage.sqlite').read_bytes()
        self.assertNotIn(second['deletion_token'].encode(), raw)
        # Original accepted receipt remains usable after recovery rotation.
        self.assertEqual(await self.deletion.delete(account['refresh_token']), {'status': 'deleted'})
        self.assertEqual(await self.deletion.delete(second['deletion_token'], recovery=True), {'status': 'deleted'})

    async def test_other_identity_active_account_expired_and_replayed_proofs_fail(self):
        account = self.enroll()
        with self.assertRaisesRegex(Rejected, 'no_account_deletion_pending'):
            self.deletion.recover(*self.proof())
        self.deletion.begin(account['refresh_token'])
        for args in (self.proof('other'), self.proof(provider='apple')):
            with self.assertRaisesRegex(Rejected, 'no_account_deletion_pending'):
                self.deletion.recover(*args)
        challenge, provider, identity, token = self.proof()
        expired = VerifiedIdentity(identity.issuer, identity.subject, self.now, identity.audience)
        with self.assertRaisesRegex(Rejected, 'invalid_identity_token'):
            self.deletion.recover(challenge, provider, expired, token)
        result = self.deletion.recover(challenge, provider, identity, token)
        with self.assertRaisesRegex(Rejected, 'invalid_account_challenge'):
            self.deletion.recover(challenge, provider, identity, token)
        fresh_challenge = self.sessions.challenge(provider)['challenge']
        with self.assertRaisesRegex(Rejected, 'identity_token_replayed'):
            self.deletion.recover(fresh_challenge, provider, identity, token)
        await self.deletion.delete(result['deletion_token'], recovery=True)

    async def test_recovery_survives_restart_and_cannot_delete_a_new_account(self):
        original = self.enroll()
        self.deletion.begin(original['refresh_token'])
        self.sessions = AccountSessions(self.admission, MemoryStore(self.memory.path))
        self.deletion = AccountDeletion(self.sessions, self.grants, self.apple)
        from unittest.mock import AsyncMock
        self.deletion.quiesce = AsyncMock()
        recovered = self.deletion.recover(*self.proof())
        await self.deletion.delete(recovered['deletion_token'], recovery=True)
        fresh = self.enroll()
        self.memory.put_source(fresh['owner'], source())
        with self.assertRaisesRegex(Rejected, 'no_account_deletion_pending'):
            self.deletion.recover(*self.proof())
        await self.deletion.delete(recovered['deletion_token'], recovery=True)
        self.assertEqual(self.memory.source(fresh['owner'], 'session-a'), source())
        self.admission.authorized(fresh['token'])

    async def test_apple_grant_and_receipt_persist_atomically(self):
        account = self.enroll(provider='apple')
        self.deletion.begin(account['refresh_token'])
        proof = self.proof(provider='apple')
        with patch.object(self.grants, 'save_apple', side_effect=RuntimeError('fixture disk failure')):
            with self.assertRaises(RuntimeError):
                self.deletion.recover(*proof, grant={'refresh_token': 'new-grant'})
        self.assertEqual(self.admission.db.execute('SELECT count(*) FROM deletion_recovery').fetchone()[0], 0)
        self.sessions.nonce(proof[0], 'apple')  # proof consumption rolled back too
        recovered = self.deletion.recover(*proof, grant={'refresh_token': 'new-grant'})
        await self.deletion.delete(recovered['deletion_token'], recovery=True)
        self.apple.revoke.assert_called_once_with('phone', 'new-grant')

    async def test_signed_google_and_apple_recovery_over_real_sockets(self):
        self.now = int(time.time())
        verifier = AccountTokenVerifier(google_audience='backend', google_presenters=['phone'], apple_audiences=['phone'])
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        for provider in verifier.keys:
            verifier.keys[provider] = Mock()
            verifier.keys[provider].get_signing_key_from_jwt.return_value = SimpleNamespace(key=key.public_key())
        service = AccountService(self.sessions, verifier, apple_oauth=self.apple, grants=self.grants, deletion=self.deletion)
        relay = Relay('unused', admission=self.admission, accounts=service)
        async with serve(relay.handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
            url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/account'
            async def request(**fields):
                async with connect(url) as socket:
                    await socket.send(json.dumps(dict(version=1, **fields)))
                    return json.loads(await socket.recv())
            for provider in ('google', 'apple'):
                account = self.enroll(provider=provider)
                self.memory.put_source(account['owner'], source())
                self.deletion.begin(account['refresh_token'])
                challenge = await request(operation='challenge', provider=provider)
                claims = dict(iss=GOOGLE if provider == 'google' else APPLE, sub='fictional-a',
                              aud='backend' if provider == 'google' else 'phone', iat=self.now, exp=self.now+300,
                              nonce=challenge['nonce'])
                token = jwt.encode(claims, key, algorithm='RS256', headers={'kid': 'fixture'})
                fields = dict(operation='recover_deletion', provider=provider, challenge=challenge['challenge'],
                              identity_token=token, confirmation='delete_account')
                if provider == 'apple':
                    fields['authorization_code'] = 'new-apple-code'
                    bad = jwt.encode(dict(claims, sub='other'), key, algorithm='RS256', headers={'kid': 'fixture'})
                    self.apple.redeem.return_value = dict(identity_token=bad, refresh_token='wrong-grant')
                    self.assertEqual((await request(**fields))['message'], 'invalid_identity_token')
                    self.apple.redeem.return_value = dict(identity_token=token, refresh_token='new-apple-grant')
                self.assertEqual((await request(**fields, owner='client-chosen'))['message'], 'invalid_account_request')
                proof = await request(**fields)
                self.assertEqual(proof['status'], 'pending')
                self.assertEqual(proof['owner'], account['owner'])
                self.assertNotIn('token', proof)
                self.assertEqual((await request(**fields))['message'], 'invalid_account_challenge')
                deleted = await request(operation='resume_deletion', deletion_token=proof['deletion_token'])
                self.assertEqual(deleted['status'], 'deleted')
                self.assertIsNone(self.memory.source(account['owner'], 'session-a'))
                self.assertEqual((await request(operation='resume_deletion', deletion_token=proof['deletion_token']))['status'], 'deleted')
            self.apple.revoke.assert_called_once_with('phone', 'new-apple-grant')


if __name__ == '__main__': unittest.main()
