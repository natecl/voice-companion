import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from admission import Admission
from account_sessions import AccountSessions
from account_tokens import GOOGLE, VerifiedIdentity
from memory_store import MemoryStore
from provider_grants import ProviderGrants
from cryptography.fernet import Fernet
from maintenance import database_lease
from migration_operator import prepare, apply


class MigrationOperatorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        memory = MemoryStore(self.root/'memory.sqlite')
        admission = Admission(self.root/'usage.sqlite', total_microusd=100, limits={'ask':(100,20,3)})
        legacy, _ = admission.enroll()
        source = memory.owner_for(legacy)
        sessions = AccountSessions(admission, memory)
        ProviderGrants(admission, Fernet.generate_key())
        challenge = sessions.challenge('google')
        enrolled = sessions.exchange(challenge['challenge'], 'google', VerifiedIdentity(GOOGLE,'private-google-subject',int(admission.clock())+300), 'fixture-proof')
        admission.close()
        self.identity = dict(source_owner=source, google_owner=enrolled['owner'], google_subject='private-google-subject')
        self.plan = self.root/'plan.json'

    def test_actual_cli_backup_prepare_apply_and_replay_refusal(self):
        identity = self.root/'identity.json'; identity.write_text(json.dumps(self.identity))
        command = [sys.executable, str(Path(__file__).with_name('migration_operator.py'))]
        before = {}
        for path in self.root.glob('*.sqlite'):
            with sqlite3.connect(path) as db: before[path.name] = list(db.iterdump())
        prep = subprocess.run(command+['prepare','--directory',str(self.root),'--identity-file',str(identity),'--plan',str(self.plan)], capture_output=True,text=True,check=True)
        self.assertNotIn('private-google-subject',prep.stdout)
        self.assertEqual(json.loads(prep.stdout)['databases_backed_up'],2)
        manifest=json.loads(self.plan.read_text())
        for name, expected in before.items():
            with sqlite3.connect(Path(manifest['backup'])/name) as db:
                self.assertEqual(list(db.iterdump()), expected)
                self.assertEqual(db.execute('PRAGMA integrity_check').fetchall(), [('ok',)])
            self.assertEqual((Path(manifest['backup'])/name).stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.plan.stat().st_mode & 0o777,0o600)
        result=subprocess.run(command+['apply','--plan',str(self.plan)],capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(result.stdout)['status'],'applied')
        with sqlite3.connect(self.root/'memory.sqlite') as db:
            self.assertEqual(db.execute('SELECT owner FROM account_identity').fetchone()[0],self.identity['source_owner'])
        with self.assertRaisesRegex(ValueError,'Databases changed'): apply(self.plan)

    def test_changed_ledger_and_missing_backup_refuse_apply(self):
        prepare(self.root,self.identity,self.plan)
        manifest=json.loads(self.plan.read_text()); backup=Path(manifest['backup'])/'usage.sqlite'
        original=backup.read_bytes(); backup.write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'Backup changed'): apply(self.plan)
        backup.write_bytes(original)
        with sqlite3.connect(self.root/'usage.sqlite') as db: db.execute('CREATE TABLE changed(value TEXT)')
        with self.assertRaisesRegex(ValueError,'Databases changed'): apply(self.plan)

    def test_runtime_lease_blocks_preparation_and_plan_is_not_overwritten(self):
        with database_lease(self.root):
            with self.assertRaises(BlockingIOError): prepare(self.root,self.identity,self.plan)
        self.assertFalse((self.root/'backups').exists())
        prepare(self.root,self.identity,self.plan)
        with self.assertRaisesRegex(ValueError,'overwrite'): prepare(self.root,self.identity,self.plan)


if __name__ == '__main__': unittest.main()
