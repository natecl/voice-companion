"""Offline tests of isolated QA lifetime configuration and safe failure receipts."""
import importlib.util
from pathlib import Path
import tempfile
import sys
import unittest
from unittest.mock import patch

import account_sessions
from account_tokens import GOOGLE, VerifiedIdentity
from admission import Admission, Rejected
from memory_store import MemoryStore

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/qa'))

spec = importlib.util.spec_from_file_location(
    'real_account_qa_server', Path(__file__).resolve().parents[1] / 'scripts/qa/real-account-server.py')
qa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qa)


class RealAccountQALifetimeTests(unittest.TestCase):
    def test_default_legacy_resume_saved_resume_and_explicit_override(self):
        self.assertEqual(qa.selected_access_seconds(None), 3600)
        self.assertEqual(qa.selected_access_seconds(None, {}), 3600)
        self.assertEqual(qa.selected_access_seconds(None, {'access_lifetime_seconds': 660}), 660)
        self.assertEqual(qa.selected_access_seconds(900, {'access_lifetime_seconds': 660}), 900)

    def test_invalid_requested_or_persisted_lifetime_rejected(self):
        for value in (659, 3601, 0, True, 660.0, '660'):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    qa.selected_access_seconds(value)
                with self.assertRaises(ValueError):
                    qa.selected_access_seconds(None, {'access_lifetime_seconds': value})

    def test_failure_reason_never_leaks_unknown_exception_text(self):
        for reason in ('provider_authorization_revoked', 'identity_provider_unavailable', 'invalid_identity_token'):
            self.assertEqual(qa.provider_failure_reason(Rejected(reason)), reason)
        for error in (RuntimeError('secret-token'), Rejected('secret-token'),
                      RuntimeError('provider_authorization_revoked')):
            self.assertEqual(qa.provider_failure_reason(error), 'other')

    def test_override_changes_new_issuance_without_rewriting_existing_session(self):
        with tempfile.TemporaryDirectory() as directory:
            now = 100000
            admission = Admission(Path(directory) / 'usage.sqlite', total_microusd=100,
                                  limits={'stt': (100, 20, 3)}, clock=lambda: now)
            self.addCleanup(admission.close)
            memory = MemoryStore(Path(directory) / 'memory.sqlite')
            sessions = account_sessions.AccountSessions(admission, memory)
            challenge = sessions.challenge('google')
            original = sessions.exchange(challenge['challenge'], 'google',
                                         VerifiedIdentity(GOOGLE, 'fictional-qa', now + 300), 'fixture-proof')
            credential = admission.authorized(original['token'])
            original_expiry = admission.db.execute('SELECT expires FROM credential WHERE id=?', (credential,)).fetchone()[0]
            with patch.object(account_sessions, 'ACCESS_SECONDS', qa.selected_access_seconds(660)):
                rotated = sessions.refresh(original['refresh_token'])
            self.assertEqual(rotated['expires'], now + 660)
            self.assertEqual(original['expires'], now + 3600)
            self.assertEqual(rotated['owner'], original['owner'])
            self.assertEqual(rotated['refresh_expires'], original['refresh_expires'])
            self.assertEqual(admission.db.execute('SELECT expires FROM credential WHERE id=?', (credential,)).fetchone()[0], original_expiry)
            self.assertEqual(admission.usage(), [])
            self.assertEqual(account_sessions.ACCESS_SECONDS, 3600)


if __name__ == '__main__':
    unittest.main()
