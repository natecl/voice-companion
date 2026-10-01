"""Google Ellis-session refresh, revocation and final-revocation contract.

Fictional Google subjects, a fake clock, a fake Google revoker and temporary
SQLite only. Google app-session refresh never contacts Google: it checks local
refresh secrets, family state and local owner revocation. Apple refresh, by
contrast, validates its stored provider grant on every refresh.
"""
import asyncio
import concurrent.futures
import contextlib
import json
import secrets
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, Mock

from cryptography.fernet import Fernet
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve

from account_deletion import AccountDeletion
from account_service import AccountService
from account_sessions import AccountSessions
from account_tokens import GOOGLE, APPLE, VerifiedIdentity
from admission import Admission, Rejected
from memory_store import MemoryStore
from provider_grants import ProviderGrants
from relay import Relay

ADA, BRAM = 'fictional-google-ada', 'fictional-google-bram'
LIMITS = {'stt': (100, 20, 5)}


class FakeGoogleRevoker:
    """Records every revocation attempt; queued outcomes are raised in order."""
    def __init__(self):
        self.calls, self.outcomes = [], []
        self.arrived, self.release = threading.Event(), None

    def revoke(self, grant):
        self.calls.append(grant)
        self.arrived.set()
        if self.release is not None and not self.release.wait(5):
            raise TimeoutError()
        if self.outcomes:
            raise self.outcomes.pop(0)


class GoogleRefreshContractTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name)
        self.now = 200000
        self.admission = self.ledger()
        self.memory = MemoryStore(self.path / 'memory.sqlite')
        self.sessions = AccountSessions(self.admission, self.memory)
        self.key = Fernet.generate_key()
        self.grants = ProviderGrants(self.admission, self.key)
        self.apple, self.google = Mock(), FakeGoogleRevoker()
        self.deletion = AccountDeletion(self.sessions, self.grants, self.apple, self.google)
        self.deletion.quiesce = AsyncMock()
        self.sequence = 0

    def ledger(self):
        admission = Admission(self.path / 'usage.sqlite', total_microusd=100, limits=LIMITS, clock=lambda: self.now)
        self.addCleanup(admission.close)
        return admission

    def restart(self):
        """Reopen both SQLite files through new service objects."""
        self.admission, self.memory = self.ledger(), MemoryStore(self.memory.path)
        self.sessions = AccountSessions(self.admission, self.memory)
        self.grants = ProviderGrants(self.admission, self.key)
        self.deletion = AccountDeletion(self.sessions, self.grants, self.apple, self.google)
        self.deletion.quiesce = AsyncMock()

    def enroll(self, subject=ADA, provider='google'):
        self.sequence += 1
        identity = VerifiedIdentity(GOOGLE if provider == 'google' else APPLE, subject, self.now + 300, 'phone')
        challenge = self.sessions.challenge(provider)['challenge']
        return self.sessions.exchange(challenge, provider, identity, f'fictional-proof-{self.sequence}')

    def active(self, session):
        try:
            self.admission.authorized(session['token'])
            return True
        except Rejected:
            return False

    def count(self, table):
        return self.admission.db.execute(f'SELECT count(*) FROM {table}').fetchone()[0]

    def snapshot(self):
        return [self.admission.db.execute(f'SELECT * FROM {t} ORDER BY 1').fetchall()
                for t in ('credential', 'account_session')]

    def active_for_owner(self, owner):
        return self.admission.db.execute(
            'SELECT count(*) FROM credential c JOIN account_session s ON s.credential=c.id '
            'WHERE s.owner=? AND c.revoked=0 AND c.expires>?', (owner, self.now)).fetchone()[0]

    def active_in_family_of(self, session):
        return self.admission.db.execute(
            'SELECT count(*) FROM credential c JOIN account_session s ON s.credential=c.id '
            'WHERE c.revoked=0 AND s.family=(SELECT s2.family FROM account_session s2 '
            'JOIN credential c2 ON c2.id=s2.credential WHERE c2.digest=?)',
            (self.admission.digest(session['token']),)).fetchone()[0]

    def assertRejected(self, reason, operation, *args):
        with self.assertRaises(Rejected) as raised:
            operation(*args)
        self.assertEqual(str(raised.exception), reason)

    def race(self, setup, first, second, rounds):
        """Start two operations together on separate SQLite connections."""
        outcomes = []
        for _ in range(rounds):
            state, barrier = setup(), threading.Barrier(2)
            def run(operation):
                ledger = Admission(self.path / 'usage.sqlite', total_microusd=100, limits=LIMITS, clock=lambda: self.now)
                try:
                    sessions = AccountSessions(ledger, self.memory)
                    deletion = AccountDeletion(sessions, ProviderGrants(ledger, self.key), self.apple, self.google)
                    barrier.wait(timeout=5)
                    try:
                        return operation(sessions, deletion, state)
                    except Rejected as error:
                        return str(error)
                finally:
                    ledger.close()
            with concurrent.futures.ThreadPoolExecutor(2) as pool:
                outcomes.append((state, list(pool.map(run, (first, second), timeout=10))))
        return outcomes

    def test_invalid_malformed_and_unknown_secrets_change_nothing(self):
        ada, bram = self.enroll(), self.enroll(BRAM)
        challenge = self.sessions.challenge('google')['challenge']
        before = self.snapshot()
        candidates = (None, 42, [], {}, '', 'x' * 31, 'x' * 257, secrets.token_urlsafe(48),
                      ada['token'], bram['token'], challenge, ada['refresh_token'] + 'x', ada['refresh_token'][:-1])
        for value in candidates:
            self.assertRejected('unauthorized', self.sessions.refresh, value)
            self.assertRejected('unauthorized', self.sessions.refresh_owner, value)
        self.sessions.sign_out(secrets.token_urlsafe(48))
        self.assertEqual(before, self.snapshot())
        self.assertTrue(self.active(ada) and self.active(bram))
        self.assertEqual(self.sessions.refresh(ada['refresh_token'])['owner'], ada['owner'])
        self.assertEqual(self.admission.usage(), [])

    def test_expiry_boundary_rejects_latest_secret_without_issuance_or_revocation(self):
        ada = self.enroll()
        self.now = ada['refresh_expires'] - 1
        latest = self.sessions.refresh(ada['refresh_token'])
        self.assertEqual(latest['refresh_expires'], ada['refresh_expires'])
        self.now = ada['refresh_expires']
        before = self.snapshot()
        self.assertRejected('unauthorized', self.sessions.refresh, latest['refresh_token'])
        self.assertRejected('unauthorized', self.sessions.refresh_owner, latest['refresh_token'])
        self.assertEqual(before, self.snapshot())
        # Expiry ends rotation only; the newest access keeps its own one-hour bound.
        self.assertTrue(self.active(latest))
        self.now = latest['expires']
        self.assertFalse(self.active(latest))

    def test_replay_after_family_deadline_still_revokes_latest_access(self):
        ada = self.enroll()
        self.now = ada['refresh_expires'] - 60
        latest, laptop, bram = self.sessions.refresh(ada['refresh_token']), self.enroll(), self.enroll(BRAM)
        self.now = ada['refresh_expires'] + 1
        self.assertTrue(self.active(latest))
        credentials = self.count('credential')
        self.assertRejected('refresh_replayed', self.sessions.refresh, ada['refresh_token'])
        self.assertFalse(self.active(latest))
        self.assertRejected('unauthorized', self.sessions.refresh, latest['refresh_token'])
        self.assertEqual(self.count('credential'), credentials)
        self.assertEqual(laptop['owner'], ada['owner'])
        self.assertTrue(self.active(laptop) and self.active(bram))
        self.assertEqual(self.sessions.refresh(laptop['refresh_token'])['owner'], ada['owner'])

    def test_replay_after_family_deadline_through_owner_lookup_and_deletion_request_revokes(self):
        ada = self.enroll()
        self.now = ada['refresh_expires'] - 60
        latest = self.sessions.refresh(ada['refresh_token'])
        self.now = ada['refresh_expires'] + 1
        self.assertRejected('refresh_replayed', self.sessions.refresh_owner, ada['refresh_token'])
        self.assertFalse(self.active(latest))
        self.assertRejected('refresh_replayed', self.deletion.begin, ada['refresh_token'])
        self.assertEqual(self.count('account_deletion'), 0)

    def test_replay_revokes_only_that_family_and_is_terminal(self):
        phone, laptop, bram = self.enroll(), self.enroll(), self.enroll(BRAM)
        self.assertEqual(phone['owner'], laptop['owner'])
        rotated = self.sessions.refresh(phone['refresh_token'])
        credentials = self.count('credential')
        for _ in range(2):
            self.assertRejected('refresh_replayed', self.sessions.refresh, phone['refresh_token'])
        self.assertEqual(self.count('credential'), credentials)
        self.assertFalse(self.active(rotated))
        self.assertRejected('unauthorized', self.sessions.refresh, rotated['refresh_token'])
        self.restart()
        self.assertRejected('unauthorized', self.sessions.refresh, rotated['refresh_token'])
        self.assertEqual(self.sessions.refresh(laptop['refresh_token'])['owner'], phone['owner'])
        self.assertEqual(self.sessions.refresh(bram['refresh_token'])['owner'], bram['owner'])

    def test_lost_rotation_response_retry_never_issues_a_second_session(self):
        ada = self.enroll()
        lost = self.sessions.refresh(ada['refresh_token'])
        credentials = self.count('credential')
        self.assertRejected('refresh_replayed', self.sessions.refresh, ada['refresh_token'])
        self.assertEqual(self.count('credential'), credentials)
        self.assertFalse(self.active(lost))
        self.assertRejected('unauthorized', self.sessions.refresh, lost['refresh_token'])
        self.assertEqual(self.active_for_owner(ada['owner']), 0)

    def test_refresh_after_sign_out_is_terminal_and_preserves_other_families(self):
        phone, laptop, bram = self.enroll(), self.enroll(), self.enroll(BRAM)
        rotated = self.sessions.refresh(phone['refresh_token'])
        self.sessions.sign_out(rotated['refresh_token'])
        credentials = self.count('credential')
        self.assertRejected('unauthorized', self.sessions.refresh, rotated['refresh_token'])
        self.assertRejected('refresh_replayed', self.sessions.refresh, phone['refresh_token'])
        self.restart()
        self.assertRejected('unauthorized', self.sessions.refresh, rotated['refresh_token'])
        self.assertEqual(self.count('credential'), credentials)
        self.assertFalse(self.active(phone) or self.active(rotated))
        self.assertTrue(self.active(laptop) and self.active(bram))
        self.sessions.refresh(laptop['refresh_token'])
        self.sessions.refresh(bram['refresh_token'])

    def test_local_owner_revocation_covers_every_device_of_only_that_owner(self):
        phone, laptop, bram = self.enroll(), self.enroll(), self.enroll(BRAM)
        rotated = self.sessions.refresh(laptop['refresh_token'])
        self.grants.revoke_local_owner(phone['owner'])
        credentials = self.count('credential')
        self.assertEqual(self.active_for_owner(phone['owner']), 0)
        self.assertRejected('unauthorized', self.sessions.refresh, phone['refresh_token'])
        self.assertRejected('unauthorized', self.sessions.refresh, rotated['refresh_token'])
        self.assertRejected('refresh_replayed', self.sessions.refresh, laptop['refresh_token'])
        self.assertEqual(self.count('credential'), credentials)
        self.assertTrue(self.active(bram))
        self.assertEqual(self.sessions.refresh(bram['refresh_token'])['owner'], bram['owner'])
        # Local revocation is not an identity reservation: only fresh provider
        # proof issues a new family, and it keeps the stable owner.
        self.assertEqual(self.enroll()['owner'], phone['owner'])

    def test_concurrent_rotation_and_sign_out_leave_no_active_family_credential(self):
        bram = self.enroll(BRAM)
        rotate = lambda sessions, _, ada: sessions.refresh(ada['refresh_token'])
        sign_out = lambda sessions, _, ada: sessions.sign_out(ada['refresh_token'])
        for ada, (rotation, signed_out) in self.race(self.enroll, rotate, sign_out, rounds=8):
            self.assertIsNone(signed_out)
            self.assertTrue(rotation == 'unauthorized' or isinstance(rotation, dict), rotation)
            self.assertEqual(self.active_in_family_of(ada), 0)
            if isinstance(rotation, dict):
                self.assertFalse(self.active(rotation))
        self.assertTrue(self.active(bram))

    def test_concurrent_rotation_and_local_owner_revocation_leave_no_owner_credential(self):
        bram = self.enroll(BRAM)
        rotate = lambda sessions, _, ada: sessions.refresh(ada['refresh_token'])
        revoke = lambda _, deletion, ada: deletion.grants.revoke_local_owner(ada['owner'])
        for ada, (rotation, revoked) in self.race(self.enroll, rotate, revoke, rounds=8):
            self.assertIsNone(revoked)
            self.assertTrue(rotation == 'unauthorized' or isinstance(rotation, dict), rotation)
            self.assertEqual(self.active_for_owner(ada['owner']), 0)
            if isinstance(rotation, dict):
                self.assertRejected('unauthorized', self.sessions.refresh, rotation['refresh_token'])
        self.assertTrue(self.active(bram))

    def test_deletion_begin_racing_other_device_rotation_revokes_every_owner_credential(self):
        bram = self.enroll(BRAM)
        def devices():
            subject = f'fictional-google-race-{self.sequence}'
            return self.enroll(subject), self.enroll(subject)
        begin = lambda _, deletion, pair: deletion.begin(pair[0]['refresh_token'])
        rotate = lambda sessions, _, pair: sessions.refresh(pair[1]['refresh_token'])
        for (phone, _), (begun, rotation) in self.race(devices, begin, rotate, rounds=6):
            self.assertEqual(begun, (phone['owner'], 'pending'))
            self.assertTrue(rotation == 'unauthorized' or isinstance(rotation, dict), rotation)
            self.assertEqual(self.active_for_owner(phone['owner']), 0)
            if isinstance(rotation, dict):
                self.assertFalse(self.active(rotation))
                self.assertRejected('unauthorized', self.sessions.refresh, rotation['refresh_token'])
        self.assertTrue(self.active(bram))
        self.assertEqual(self.google.calls, [])

    async def test_final_google_revocation_outcomes_are_durable_and_never_auto_retried(self):
        phone, laptop, bram = self.enroll(), self.enroll(), self.enroll(BRAM)
        rotated = self.sessions.refresh(laptop['refresh_token'])
        self.assertEqual(await self.deletion.delete(phone['refresh_token']), {'status': 'awaiting_google_revocation'})
        credentials = self.count('credential')
        for token in (phone['refresh_token'], rotated['refresh_token']):
            self.assertRejected('unauthorized', self.sessions.refresh, token)
        self.assertRejected('refresh_replayed', self.sessions.refresh, laptop['refresh_token'])
        self.assertRejected('account_deletion_pending', self.enroll)
        self.assertEqual(self.count('credential'), credentials)
        for failure in ('identity_provider_unavailable', 'google_authorization_revoked'):
            self.google.outcomes.append(Rejected(failure))
            calls = len(self.google.calls)
            with self.assertRaises(Rejected) as raised:
                await self.deletion.finish_google(phone['refresh_token'], 'fictional-google-grant')
            self.assertEqual(str(raised.exception), failure)
            self.assertEqual(len(self.google.calls), calls + 1)
            self.assertEqual(self.admission.db.execute('SELECT state FROM account_deletion WHERE owner=?',
                                                       (phone['owner'],)).fetchone(), ('pending',))
            self.assertRejected('account_deletion_pending', self.enroll)
        # Restart keeps the reservation; an explicit retry is the only new call.
        self.restart()
        self.assertEqual(await self.deletion.finish_google(phone['refresh_token'], 'fictional-google-grant'),
                         {'status': 'deleted'})
        self.assertEqual(len(self.google.calls), 3)
        self.assertEqual(await self.deletion.finish_google(phone['refresh_token'], 'lost-response-retry'),
                         {'status': 'deleted'})
        self.assertEqual(len(self.google.calls), 3)
        self.assertEqual(self.count('credential'), credentials)
        fresh = self.enroll()
        self.assertNotEqual(fresh['owner'], phone['owner'])
        for token in (phone['refresh_token'], rotated['refresh_token']):
            self.assertRejected('unauthorized', self.sessions.refresh, token)
        self.assertTrue(self.active(fresh) and self.active(bram))
        self.assertEqual(self.sessions.refresh(fresh['refresh_token'])['owner'], fresh['owner'])
        self.apple.revoke.assert_not_called()

    async def test_refresh_during_held_google_revocation_cannot_issue_or_complete_early(self):
        phone, laptop, bram = self.enroll(), self.enroll(), self.enroll(BRAM)
        rotated = self.sessions.refresh(laptop['refresh_token'])
        await self.deletion.delete(phone['refresh_token'])
        self.google.release = threading.Event()
        finishing = asyncio.create_task(self.deletion.finish_google(phone['refresh_token'], 'fictional-google-grant'))
        self.assertTrue(await asyncio.to_thread(self.google.arrived.wait, 2))
        credentials = self.count('credential')
        for token in (phone['refresh_token'], rotated['refresh_token']):
            self.assertRejected('unauthorized', self.sessions.refresh, token)
            self.assertRejected('unauthorized', self.sessions.refresh_owner, token)
        self.assertRejected('refresh_replayed', self.sessions.refresh, laptop['refresh_token'])
        self.assertRejected('account_deletion_pending', self.enroll)
        self.assertEqual(self.admission.db.execute('SELECT state FROM account_deletion WHERE owner=?',
                                                   (phone['owner'],)).fetchone(), ('pending',))
        self.assertFalse(finishing.done())
        self.google.release.set()
        self.assertEqual(await finishing, {'status': 'deleted'})
        self.assertEqual(self.count('credential'), credentials)
        self.assertRejected('unauthorized', self.sessions.refresh, rotated['refresh_token'])
        self.assertEqual(len(self.google.calls), 1)
        self.assertTrue(self.active(bram))

    @contextlib.asynccontextmanager
    async def account_endpoint(self, verifier):
        service = AccountService(self.sessions, verifier, apple_oauth=self.apple, grants=self.grants, deletion=self.deletion)
        relay = Relay('unused', admission=self.admission, accounts=service)
        async with serve(relay.handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
            url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/account'
            async def request(**fields):
                async with connect(url) as socket:
                    await socket.send(json.dumps(dict(version=1, **fields)))
                    return json.loads(await socket.recv())
            yield request

    async def test_socket_replay_after_family_deadline_revokes_through_service(self):
        ada = self.enroll()
        self.now = ada['refresh_expires'] - 60
        verifier = Mock()
        async with self.account_endpoint(verifier) as request:
            latest = await request(operation='refresh', refresh_token=ada['refresh_token'])
            self.now = ada['refresh_expires'] + 1
            self.assertTrue(self.active(latest))
            replay = await request(operation='refresh', refresh_token=ada['refresh_token'])
            self.assertEqual(replay, dict(type='error', message='refresh_replayed'))
            self.assertFalse(self.active(latest))
            revoked_and_expired = await request(operation='refresh', refresh_token=latest['refresh_token'])
            self.assertEqual(revoked_and_expired, dict(type='error', message='unauthorized'))
        verifier.verify.assert_not_called()
        self.apple.validate_refresh.assert_not_called()
        self.assertEqual(self.google.calls, [])

    async def test_socket_google_refresh_makes_no_provider_call_unlike_apple(self):
        ada, bram, apple_user = self.enroll(), self.enroll(BRAM), self.enroll('fictional-apple-cy', 'apple')
        self.grants.save_apple(apple_user['owner'], 'phone', 'fictional-apple-grant')
        verifier = Mock()
        async with self.account_endpoint(verifier) as request:
            for malformed in (None, 7, ['x'], '', 'x' * 300, ada['token']):
                self.assertEqual((await request(operation='refresh', refresh_token=malformed))['message'], 'unauthorized')
            self.assertEqual((await request(operation='refresh', refresh_token=ada['refresh_token'],
                                            owner=bram['owner']))['message'], 'invalid_account_request')
            rotated = await request(operation='refresh', refresh_token=ada['refresh_token'])
            self.assertEqual((rotated['type'], rotated['owner']), ('account_result', ada['owner']))
            self.assertEqual((await request(operation='refresh', refresh_token=ada['refresh_token']))['message'], 'refresh_replayed')
            self.assertEqual((await request(operation='refresh', refresh_token=rotated['refresh_token']))['message'], 'unauthorized')
            self.assertEqual(self.apple.validate_refresh.call_count, 0)
            self.apple.validate_refresh.side_effect = Rejected('identity_provider_unavailable')
            unavailable = await request(operation='refresh', refresh_token=apple_user['refresh_token'])
            self.assertEqual(unavailable['message'], 'identity_provider_unavailable')
            self.assertTrue(self.active(apple_user))
            self.apple.validate_refresh.side_effect = Rejected('provider_authorization_revoked')
            revoked = await request(operation='refresh', refresh_token=apple_user['refresh_token'])
            self.assertEqual(revoked['message'], 'provider_authorization_revoked')
            self.assertFalse(self.active(apple_user))
            google = await request(operation='refresh', refresh_token=bram['refresh_token'])
            self.assertEqual(google['owner'], bram['owner'])
            await request(operation='sign_out', refresh_token=google['refresh_token'])
            self.assertEqual((await request(operation='refresh', refresh_token=google['refresh_token']))['message'], 'unauthorized')
        self.assertEqual(self.apple.validate_refresh.call_count, 2)
        verifier.verify.assert_not_called()
        self.assertEqual(self.google.calls, [])
        self.assertEqual(self.admission.usage(), [])


if __name__ == '__main__':
    unittest.main()
