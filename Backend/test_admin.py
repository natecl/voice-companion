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

    def test_memory_export_and_renewal_keep_same_owner(self):
        from memory_store import MemoryStore
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            ledger = Admission(directory/'usage.sqlite', total_microusd=100, limits={'stt': (100,20,6)})
            try:
                memory = MemoryStore(directory/'memory.sqlite')
                first = directory/'first.json'; second = directory/'second.json'
                old = export_credential(ledger, 'wss://example.com/stt', first, 7, memory=memory)
                owner = json.loads(first.read_text())['memoryOwnerID']
                new = export_credential(ledger, 'wss://example.com/stt', second, 7, memory=memory, owner=owner)
                self.assertNotEqual(old, new)
                self.assertEqual(json.loads(second.read_text())['memoryOwnerID'], owner)
                ledger.revoke(old)
                self.assertEqual(memory.owner_for(ledger.authorized(json.loads(second.read_text())['token'])), owner)
            finally:
                ledger.close()
