import tempfile
import unittest
from pathlib import Path

from admission import Admission, Rejected
from account_tokens import VerifiedIdentity, GOOGLE
from account_sessions import AccountSessions, ACCESS_SECONDS, REFRESH_SECONDS
from memory_store import MemoryStore


class AccountSessionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.now = 100000
        self.admission = Admission(Path(self.directory.name)/'admission.sqlite', total_microusd=100,
                                   limits={'stt': (100, 20, 3)}, clock=lambda: self.now)
        self.addCleanup(self.admission.close)
        self.memory = MemoryStore(Path(self.directory.name)/'memory.sqlite')
        self.sessions = AccountSessions(self.admission, self.memory)

    def enroll(self, subject='synthetic-a', token='signed-fixture-a'):
        challenge = self.sessions.challenge('google')
        identity = VerifiedIdentity(GOOGLE, subject, self.now+300)
        return self.sessions.exchange(challenge['challenge'], 'google', identity, token)

    def test_rotation_preserves_owner_expires_old_access_and_does_not_extend_family(self):
        first = self.enroll()
        self.now += ACCESS_SECONDS
        with self.assertRaises(Rejected): self.admission.authorized(first['token'])
        second = self.sessions.refresh(first['refresh_token'])
        self.assertEqual(first['owner'], second['owner'])
        self.assertEqual(first['refresh_expires'], second['refresh_expires'])
        self.assertEqual(self.memory.owner_for(self.admission.authorized(second['token'])), first['owner'])
        self.assertEqual(self.admission.usage(), [])
        self.now += REFRESH_SECONDS
        with self.assertRaises(Rejected): self.sessions.refresh(second['refresh_token'])

    def test_rotation_preserves_inflight_access_only_until_original_expiry(self):
        first = self.enroll()
        self.now += ACCESS_SECONDS - 600
        second = self.sessions.refresh(first['refresh_token'])
        self.admission.authorized(first['token'])
        self.now += 600
        with self.assertRaises(Rejected): self.admission.authorized(first['token'])
        self.admission.authorized(second['token'])

    def test_refresh_replay_revokes_entire_family_but_not_other_login(self):
        first = self.enroll()
        separate = self.enroll(token='signed-fixture-b')
        second = self.sessions.refresh(first['refresh_token'])
        with self.assertRaisesRegex(Rejected, 'refresh_replayed'):
            self.sessions.refresh(first['refresh_token'])
        with self.assertRaises(Rejected): self.admission.authorized(second['token'])
        with self.assertRaises(Rejected): self.sessions.refresh(second['refresh_token'])
        self.admission.authorized(separate['token'])

    def test_signout_is_idempotent_and_old_refresh_can_revoke_rotated_session(self):
        first = self.enroll()
        second = self.sessions.refresh(first['refresh_token'])
        for _ in range(2): self.sessions.sign_out(first['refresh_token'])
        with self.assertRaises(Rejected): self.admission.authorized(first['token'])
        with self.assertRaises(Rejected): self.admission.authorized(second['token'])
        with self.assertRaises(Rejected): self.sessions.refresh(second['refresh_token'])

    def test_identity_token_and_challenge_replay(self):
        challenge = self.sessions.challenge('google')
        identity = VerifiedIdentity(GOOGLE, 'synthetic-a', self.now+300)
        self.sessions.exchange(challenge['challenge'], 'google', identity, 'same-token')
        with self.assertRaisesRegex(Rejected, 'invalid_account_challenge'):
            self.sessions.exchange(challenge['challenge'], 'google', identity, 'other-token')
        next_challenge = self.sessions.challenge('google')
        with self.assertRaisesRegex(Rejected, 'identity_token_replayed'):
            self.sessions.exchange(next_challenge['challenge'], 'google', identity, 'same-token')

    def test_invalid_challenge_and_owner_failure_never_issue_access(self):
        challenge = self.sessions.challenge('apple')
        with self.assertRaises(Rejected): self.sessions.nonce(challenge['challenge'], 'google')
        self.now += 300
        with self.assertRaises(Rejected): self.sessions.nonce(challenge['challenge'], 'apple')
        from unittest.mock import patch
        with patch.object(self.memory, 'owner_for_identity', side_effect=RuntimeError('disk failed')):
            with self.assertRaises(RuntimeError): self.enroll()
        self.assertEqual(self.admission.active_credentials(), [])
        self.assertEqual(self.admission.db.execute('SELECT count(*) FROM account_exchange').fetchone()[0], 0)

    def test_simultaneous_refresh_has_one_winner_then_revokes_on_reuse(self):
        import concurrent.futures
        import threading
        first = self.enroll()
        barrier = threading.Barrier(2)
        def rotate():
            ledger = Admission(Path(self.directory.name)/'admission.sqlite', total_microusd=100,
                               limits={'stt': (100, 20, 3)}, clock=lambda: self.now)
            try:
                sessions = AccountSessions(ledger, self.memory)
                barrier.wait(timeout=5)
                try: return sessions.refresh(first['refresh_token'])
                except Rejected as error: return str(error)
            finally: ledger.close()
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda _: rotate(), range(2)))
        self.assertEqual(results.count('refresh_replayed'), 1)
        winner = next(value for value in results if isinstance(value, dict))
        with self.assertRaises(Rejected): self.admission.authorized(winner['token'])

    def test_restart_keeps_sessions_and_stores_no_raw_tokens(self):
        session = self.enroll()
        self.sessions = AccountSessions(self.admission, MemoryStore(self.memory.path))
        new = self.sessions.refresh(session['refresh_token'])
        self.assertEqual(new['owner'], session['owner'])
        contents = (Path(self.directory.name)/'admission.sqlite').read_bytes()
        for value in (session['token'], session['refresh_token'], 'signed-fixture-a'):
            self.assertNotIn(value.encode(), contents)


if __name__ == '__main__': unittest.main()
