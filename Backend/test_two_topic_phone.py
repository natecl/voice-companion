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

    def test_resume_preserves_spend_window_and_excludes_interrupted_source(self):
        from resume_two_topic_phone import provision as resume
        from service_policy import TWO_TOPIC_PHONE_POLICIES,TWO_TOPIC_RESUME_APPROVAL
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            admission=Admission(root/'usage.sqlite',total_microusd=5230000,limits=TWO_TOPIC_PHONE_POLICIES)
            credential,_=admission.enroll();admission.close()
            store=MemoryStore(root/'memory.sqlite');owner=store.owner_for(credential)
            with sqlite3.connect(root/'usage.sqlite') as db:
                db.execute('CREATE TABLE qa_budget_extension(id TEXT PRIMARY KEY,amount INTEGER)')
                db.execute('INSERT INTO qa_budget_extension VALUES(?,45000)',(TWO_TOPIC_APPROVAL,))
                db.execute('CREATE TABLE IF NOT EXISTS allocation_request(id TEXT PRIMARY KEY)')
            with sqlite3.connect(root/'notes-budget.sqlite') as db:
                db.execute('CREATE TABLE notes_allocation(id TEXT PRIMARY KEY,cap INTEGER,max_calls INTEGER)')
                db.execute('CREATE TABLE notes_attempt(id TEXT PRIMARY KEY,reserved INTEGER,state TEXT,usage TEXT)')
            import time
            now=time.time()
            config=dict(approval=TWO_TOPIC_APPROVAL,owner=owner,starts=now-100,expires=now+1000)
            (root/'proactive-phone-qa.json').write_text(json.dumps(config))
            with sqlite3.connect(root/'two-topic-phone-qa.sqlite') as db:
                db.execute('CREATE TABLE capture(id TEXT PRIMARY KEY)')
                db.executemany('INSERT INTO capture VALUES(?)',[(key,) for key in (*SEEDS,'interrupted')])
            (root/TWO_TOPIC_APPROVAL).mkdir()
            with sqlite3.connect(root/TWO_TOPIC_APPROVAL/'usage.sqlite') as db:
                db.execute('CREATE TABLE attempts(id TEXT PRIMARY KEY,hash TEXT,reserved INTEGER,state TEXT,usage TEXT)')
                db.execute("INSERT INTO attempts VALUES('old','phone-runtime',20000,'completed','{}')")
            receipt=resume(root);qa=PhoneQA(root)
            self.assertEqual(receipt['expires'],config['expires'])
            self.assertEqual(qa.sources(owner),set(SEEDS))
            self.assertTrue(qa.contains(owner,'interrupted'))
            qa.enroll(owner,'resumed')
            with self.assertRaises(Rejected):qa.enroll(owner,'extra')
            with self.assertRaises(Rejected):qa.enroll('other','resumed')
            for i in range(7):qa.reserve(str(i),'gpt-6-luna');qa.finish(str(i),{})
            with self.assertRaises(Rejected):qa.reserve('extra','gpt-6-luna')
            with self.assertRaises(ValueError):resume(root)
            with patch.dict(os.environ,VOICE_DATA_DIR=str(root),VOICE_ENABLE_ASK='1'):
                from notes_budget import NotesBudget
                reopened=open_ledger(migrate=True)
                budget=NotesBudget(root/'notes-budget.sqlite',reopened)
                budget.reserve('one','gpt-6-luna')
                with self.assertRaises(Rejected):budget.reserve('two','gpt-6-luna')
                self.assertEqual(reopened.db.execute('SELECT cap FROM budget').fetchone()[0],5275000)
                reopened.close()
            with sqlite3.connect(qa.usage) as db:
                self.assertEqual(db.execute("SELECT reserved,state FROM attempts WHERE id='old'").fetchone(),(20000,'completed'))
            self.assertFalse(PhoneQA(root,clock=lambda:config['expires']+1).active(owner))
