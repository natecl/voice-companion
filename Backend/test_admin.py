import json
from pathlib import Path
import tempfile
import unittest
from admission import Admission, Rejected
from admin import export_credential


class AdminTests(unittest.TestCase):
    def test_export_is_private_no_overwrite_and_revocable(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / 'client.json'
            store = Admission(Path(directory) / 'ledger.sqlite', total_microusd=100,
                              limits={'stt': (100, 20, 6)})
            try:
                identifier = export_credential(store, 'wss://example.com/stt', output, 7)
                config = json.loads(output.read_text())
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)
                self.assertEqual(store.authorized(config['token']), identifier)
                with self.assertRaises(FileExistsError):
                    export_credential(store, config['url'], output, 7)
                self.assertEqual(store.db.execute('SELECT count(*) FROM credential').fetchone()[0], 1)
                store.revoke(identifier)
                with self.assertRaises(Rejected):
                    store.authorized(config['token'])
                self.assertEqual(store.usage(), [])
            finally:
                store.close()
