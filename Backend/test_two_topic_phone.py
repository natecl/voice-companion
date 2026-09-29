import json,os,sqlite3,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from admission import Admission,Rejected
from memory_store import MemoryStore
from proactive_phone_qa import PhoneQA,CEDAR_APPROVAL,TWO_TOPIC_APPROVAL
from service_policy import CEDAR_PHONE_POLICIES,open_ledger
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/evaluations'))
from provision_two_topic_phone import provision,SEEDS

class TwoTopicSetupTests(unittest.TestCase):
    def test_provision_retrieval_limits_and_startup_preserve_history(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            admission=Admission(root/'usage.sqlite',total_microusd=5185000,limits=CEDAR_PHONE_POLICIES)
            credential,_=admission.enroll();admission.close()
            store=MemoryStore(root/'memory.sqlite');owner=store.owner_for(credential)
            with sqlite3.connect(root/'usage.sqlite') as db:
                db.execute('CREATE TABLE qa_budget_extension(id TEXT PRIMARY KEY,amount INTEGER)')
                db.execute('INSERT INTO qa_budget_extension VALUES(?,45000)',(CEDAR_APPROVAL,))
                db.execute('CREATE TABLE IF NOT EXISTS allocation_request(id TEXT PRIMARY KEY)')
            with sqlite3.connect(root/'notes-budget.sqlite') as db:
                db.execute('CREATE TABLE notes_allocation(id TEXT PRIMARY KEY,amount INTEGER,calls INTEGER)')
            (root/'proactive-phone-qa.json').write_text(json.dumps(dict(approval=CEDAR_APPROVAL,owner=owner,starts=1,expires=2)))
            with sqlite3.connect(root/'cedar-phone-qa.sqlite') as db:
                db.execute('CREATE TABLE capture(id TEXT PRIMARY KEY)');db.execute("INSERT INTO capture VALUES('historical')")
            receipt=provision(root);qa=PhoneQA(root)
            self.assertEqual(receipt['proactive_calls'],8)
            self.assertEqual(qa.sources(owner),set(SEEDS))
            self.assertTrue(qa.contains(owner,'historical'))
            qa.enroll(owner,'live')
            with self.assertRaises(Rejected):qa.enroll(owner,'extra')
            with self.assertRaises(Rejected):qa.enroll('other','live')
            for i in range(8):qa.reserve(str(i),'gpt-6-luna');qa.finish(str(i),{})
            with self.assertRaises(Rejected):qa.reserve('ninth','gpt-6-luna')
            with self.assertRaises(ValueError):provision(root)
            with patch.dict(os.environ,VOICE_DATA_DIR=str(root),VOICE_ENABLE_ASK='1'):
                reopened=open_ledger(migrate=True);reopened.close()
            with store.connect() as db:
                self.assertEqual(db.execute('SELECT count(*) FROM source').fetchone()[0],2)
                self.assertEqual(db.execute('SELECT count(*) FROM job').fetchone()[0],0)
            from proactive_context import prepare
            from proactive_replay import recording
            for key,text in SEEDS.items():
                context=prepare(store,owner,recording('live',text,completed=False),allowed_sources=qa.sources(owner))
                self.assertTrue(context)
                self.assertIn(key,{s['session_id'] for s in context['state']['sources']})
            expired=PhoneQA(root,clock=lambda:receipt['expires']+1)
            self.assertFalse(expired.active(owner))
            self.assertTrue(expired.contains(owner,'historical'))
            self.assertTrue(expired.contains(owner,'live'))
