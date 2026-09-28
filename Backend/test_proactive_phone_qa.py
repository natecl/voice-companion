import json,sqlite3,tempfile,unittest
from pathlib import Path
from proactive_phone_qa import PhoneQA,APPROVAL
from admission import Rejected
from memory_store import MemoryStore
from test_memory import source
from service_policy import extend_proactive_phone_policy,proactive_phone_funded,PRIVATE_DICTATION_POLICIES,PRIVATE_DICTATION_APPROVAL,PROACTIVE_PHONE_POLICIES

class PhoneQATests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.now=100
        (self.root/'proactive-phone-qa.json').write_text(json.dumps(dict(approval=APPROVAL,owner='owner',starts=100,expires=200)))
        with sqlite3.connect(self.root/'proactive-phone-qa.sqlite') as db:db.execute('CREATE TABLE capture(id TEXT PRIMARY KEY)')
        folder=self.root/'proactive-20260928-025';folder.mkdir()
        with sqlite3.connect(folder/'usage.sqlite') as db:
            db.execute('CREATE TABLE attempts(id TEXT PRIMARY KEY,hash TEXT,reserved INTEGER,state TEXT,usage TEXT)')
            for i in range(7):db.execute('INSERT INTO attempts VALUES(?,?,?,?,NULL)',(str(i),'old',10000,'completed'))
        self.qa=PhoneQA(self.root,clock=lambda:self.now)
    def test_two_captures_owner_expiry_and_reopen(self):
        with self.assertRaises(Rejected):self.qa.enroll('other','a')
        self.qa.enroll('owner','a');self.qa.enroll('owner','a');self.qa.enroll('owner','b')
        with self.assertRaises(Rejected):self.qa.enroll('owner','c')
        self.assertEqual(self.qa.sources('owner'),{'a','b'})
        self.now=200
        self.assertEqual(self.qa.sources('owner'),set())
        self.assertTrue(self.qa.contains('owner','a'))
        with self.assertRaises(Rejected):self.qa.enroll('owner','a')
    def test_remaining_five_calls_no_retry_or_refund(self):
        self.qa.reserve('one','gpt-6-luna');self.qa.finish('one')
        with self.assertRaises(Rejected):self.qa.reserve('one','gpt-6-luna')
        for i in range(4):self.qa.reserve('new'+str(i),'gpt-6-luna')
        with self.assertRaises(Rejected):self.qa.reserve('six','gpt-6-luna')
        with self.assertRaises(Rejected):self.qa.reserve('jev','jev-1.13.0')
    def test_test_sources_are_saved_without_learning_jobs(self):
        store=MemoryStore(self.root/'memory');owner=store.owner_for('credential')
        store.put_source(owner,source(),learn=False)
        with store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM source').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM job').fetchone()[0],0)
        store.put_source(owner,source('normal'))
        with store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM job').fetchone()[0],1)
    def test_funding_is_explicit_idempotent_preserves_requests(self):
        db=sqlite3.connect(':memory:')
        db.executescript('CREATE TABLE budget(id INTEGER,cap INTEGER);INSERT INTO budget VALUES(1,5050000);CREATE TABLE policy(category TEXT,cap INTEGER,reservation INTEGER,daily INTEGER);CREATE TABLE request(id TEXT,state TEXT);CREATE TABLE qa_budget_extension(id TEXT PRIMARY KEY,amount INTEGER);')
        db.executemany('INSERT INTO policy VALUES(?,?,?,?)',[(k,*v) for k,v in PRIVATE_DICTATION_POLICIES.items()])
        db.execute('INSERT INTO qa_budget_extension VALUES(?,50000)',(PRIVATE_DICTATION_APPROVAL,))
        db.execute("INSERT INTO request VALUES('old','completed')")
        extend_proactive_phone_policy(db);extend_proactive_phone_policy(db)
        self.assertTrue(proactive_phone_funded(db,(5140000,),PROACTIVE_PHONE_POLICIES))
        self.assertEqual(db.execute('SELECT * FROM request').fetchall(),[('old','completed')])

    def test_real_socket_uses_registered_prior_and_preserves_grant(self):
        import asyncio
        from websockets.asyncio.client import connect
        from websockets.asyncio.server import serve
        from admission import Admission
        from proactive_socket import ProactiveSocketService
        from proactive_service import ProactiveService
        from test_proactive_service import Models
        from companion_chat import CompanionChat
        async def exercise():
            admission=Admission(self.root/'admission',total_microusd=1,limits={'qa':(1,1,1)})
            try:
                credential,token=admission.enroll()
                store=MemoryStore(self.root/'memory');owner=store.owner_for(credential)
                self.qa.config['owner']=owner
                self.qa.enroll(owner,'prior')
                store.put_source(owner,source('prior',text='Alex wakes at three each morning.'),learn=False)
                models=Models()
                service=ProactiveService(store,models,self.qa,phone_qa=self.qa)
                handler=ProactiveSocketService(admission,service)
                async with serve(handler.handle,'127.0.0.1',0) as server:
                    url=f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}'
                    async with connect(url,additional_headers={'Authorization':'Bearer '+token}) as socket:
                        await socket.send(json.dumps(dict(operation='open',capture='live')))
                        self.assertEqual(json.loads(await socket.recv())['type'],'ready')
                        live=dict(source('live',text='Discussing Alex waking at three with the doctor.'),completed=False)
                        await socket.send(json.dumps(dict(operation='observe',live=live)))
                        event=json.loads(await asyncio.wait_for(socket.recv(),2))
                        self.assertEqual(event['type'],'contribution')
                        self.assertEqual(len(CompanionChat(store).page(owner)['turns']),1)
                with sqlite3.connect(self.qa.usage) as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM attempts').fetchone()[0],8)
                print('Phone QA socket: registered prior -> synthetic contribution -> ordinary saved turn; one reservation')
            finally:admission.close()
        asyncio.run(exercise())
