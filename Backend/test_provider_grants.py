import tempfile
import unittest
from pathlib import Path

from cryptography.fernet import Fernet
from admission import Admission, Rejected
from provider_grants import ProviderGrants


class ProviderGrantsTests(unittest.TestCase):
    def test_encrypted_grants_are_owner_scoped_replaceable_and_survive_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'usage.sqlite'
            key = Fernet.generate_key()
            admission = Admission(path, total_microusd=100, limits={'stt': (100, 20, 3)})
            grants = ProviderGrants(admission, key)
            grants.save_apple('alice', 'phone', 'old-secret')
            grants.save_apple('alice', 'phone', 'alice-secret')
            grants.save_apple('bob', 'phone', 'bob-secret')
            self.assertEqual(grants.apple_for('alice'), [('phone', 'alice-secret')])
            self.assertEqual(grants.apple_for('unknown'), [])
            encrypted = admission.db.execute('SELECT ciphertext FROM apple_grant').fetchall()
            self.assertTrue(all(b'secret' not in row[0] for row in encrypted))
            admission.close()
            admission = Admission(path, total_microusd=100, limits={'stt': (100, 20, 3)})
            self.addCleanup(admission.close)
            self.assertEqual(ProviderGrants(admission, key).apple_for('bob'), [('phone', 'bob-secret')])
            with self.assertRaisesRegex(Rejected, '^identity_provider_unavailable$'):
                ProviderGrants(admission, Fernet.generate_key()).apple_for('alice')


if __name__ == '__main__':
    unittest.main()
