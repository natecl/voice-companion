import os,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from admission import Admission,Rejected
from service_policy import PREFERENCE_POLICIES,DICTATION_POLICIES,redistribute_dictation_policy,open_ledger

class DictationBudgetTests(unittest.TestCase):
    def test_explicit_reallocation_preserves_charges_reopens_and_bounds_recording(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'usage.sqlite'
            store=Admission(path,total_microusd=5000000,limits=PREFERENCE_POLICIES)
            token=store.enroll()[1]
            owner=store.authorized(token)
            for category,amount in [('stt',1200000),('ask',2923868),('jev',833000)]:
                store.db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)',(category,owner,category,0,amount,'completed'))
            before=store.db.execute('SELECT * FROM request ORDER BY id').fetchall()
            with store.transaction():redistribute_dictation_policy(store.db)
            with store.transaction():redistribute_dictation_policy(store.db)
            self.assertEqual(before,store.db.execute('SELECT * FROM request ORDER BY id').fetchall())
            self.assertEqual(store.db.execute('SELECT count(*) FROM budget_redistribution').fetchone()[0],1)
            store.close()
            with patch.dict(os.environ,{'VOICE_DATA_DIR':directory,'VOICE_ENABLE_ASK':'1'}):
                reopened=open_ledger(migrate=True)
                request=reopened.reserve(token,'stt');reopened.finish(request,completed=True)
                with self.assertRaises(Rejected):reopened.reserve(token,'stt')
                answer=reopened.reserve(token,'ask');reopened.finish(answer,completed=True)
                self.assertEqual(reopened.db.execute('SELECT cap FROM budget').fetchone()[0],5000000)
                self.assertEqual(reopened.db.execute('SELECT sum(reserved) FROM request').fetchone()[0],4979868)
                reopened.close()

    def test_insufficient_donor_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            store=Admission(Path(directory)/'usage.sqlite',total_microusd=5000000,limits=PREFERENCE_POLICIES)
            owner,token=store.enroll()
            store.db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)',('old',owner,'ask',0,2940000,'completed'))
            with self.assertRaises(ValueError):
                with store.transaction():redistribute_dictation_policy(store.db)
            self.assertEqual(dict((r[0],tuple(r[1:])) for r in store.db.execute('SELECT * FROM policy')),PREFERENCE_POLICIES)
            store.close()

    def test_private_extension_is_explicit_idempotent_and_reopens(self):
        from service_policy import extend_private_dictation_policy,PRIVATE_DICTATION_POLICIES
        with tempfile.TemporaryDirectory() as directory:
            store=Admission(Path(directory)/'usage.sqlite',total_microusd=5000000,limits=DICTATION_POLICIES)
            owner,token=store.enroll()
            store.db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)',('old',owner,'stt',0,1220000,'completed'))
            before=store.db.execute('SELECT * FROM request').fetchall()
            for _ in range(2):
                with store.transaction():extend_private_dictation_policy(store.db)
            self.assertEqual(before,store.db.execute('SELECT * FROM request').fetchall())
            store.close()
            with patch.dict(os.environ,{'VOICE_DATA_DIR':directory,'VOICE_ENABLE_ASK':'1'}):
                reopened=open_ledger(migrate=True)
                req=reopened.reserve(token,'stt');reopened.finish(req,completed=True)
                with self.assertRaises(Rejected):reopened.reserve(token,'stt')
                self.assertEqual(reopened.db.execute('SELECT cap FROM budget').fetchone()[0],5050000)
                reopened.close()
