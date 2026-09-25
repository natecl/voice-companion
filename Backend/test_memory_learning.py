import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from admission import Admission, Rejected
from memory_store import MemoryStore
from memory_budget import MemoryBudget, reserve_global_allocation, ALLOCATION
from memory_models import MemoryModels, JEV, parse_judgments, judgment_request
from memory_writer import MemoryWriter, MemoryWorker
from test_memory import source


def memory(text='Maya prefers morning meetings.', name='Maya', **kw):
    return dict(text=text,subject_name=name,kind='preference',basis='stated',source_ids=['p1'],expires_at=None,**kw)


def answers(request, overrides=None):
    result = {}
    for k, q in request['questions'].items():
        value = 'supported' if k.startswith('support') else 'named' if k.startswith('attribution') else 'stated' if k.startswith('modality') else 'none' if k.startswith('expiry') else 'new'
        value = (overrides or {}).get(k,value)
        result[k] = dict(type='choice', choice=value, confidence=.99,
                        probabilities={option:1. if option==value else 0. for option in q['criteria']})
    return {'model':JEV,'answers':result,'usage':{'input_tokens':100,'output_tokens':0}}


class LearningTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.ledger = Admission(self.directory/'usage.sqlite', total_microusd=5_000_000,
                                limits={'jev':(500_000,500,64)})
        self.ledger.enroll(); self.addCleanup(self.ledger.close)
        receipt = reserve_global_allocation(self.directory/'usage.sqlite')
        self.budget = MemoryBudget(self.directory/'subledger.sqlite',receipt)
        self.store = MemoryStore(self.directory/'memory.sqlite',clock=lambda:150.)
        self.owner = self.store.owner_for('credential')
        self.extractions = 0; self.judgments = 0
        self.candidates = [memory()]; self.overrides = {}

    def writer(self):
        async def extract(request):
            self.extractions += 1
            return {'data':{'memories':self.candidates},'usage':{'input_tokens':100,'output_tokens':100}}
        async def judge(request):
            self.judgments += 1
            return {'data':answers(request,self.overrides),'usage':{'input_tokens':100,'output_tokens':0}}
        return MemoryWriter(self.store,MemoryModels('unused','unused',luna_call=extract,jev_call=judge),self.budget)

    async def test_automatic_write_duplicate_correction_and_cached_outputs(self):
        self.store.put_source(self.owner,source(text='Maya prefers morning meetings.'))
        writer = self.writer()
        result = await writer.process_next(self.owner)
        self.assertEqual(result['accepted'],1)
        self.assertEqual((self.extractions,self.judgments),(1,1))
        self.assertIsNone(await writer.process_next(self.owner))
        self.store.put_source(self.owner,source('session-b',text='Maya prefers morning meetings.'))
        self.overrides = {'relation_0':'duplicate_0'}
        await writer.process_next(self.owner)
        self.assertEqual(len(self.store.search(self.owner)),1)
        self.assertEqual(len(self.store.search(self.owner)[0]['sources']),2)
        self.candidates = [memory('Maya now prefers afternoon meetings.')]
        self.overrides = {'relation_0':'update_0'}
        update = source('session-c',text='Maya now prefers afternoon meetings.'); update['captured_at']=140.
        self.store.put_source(self.owner,update)
        await writer.process_next(self.owner)
        self.assertIn('afternoon',self.store.search(self.owner)[0]['text'])
        self.assertEqual(len(self.store.search(self.owner,historical=True)),2)
        self.store.delete_source(self.owner,'session-c')
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM job_result WHERE job IN (SELECT id FROM job WHERE session='session-c')").fetchone()[0],0)

    async def test_support_and_unknown_identity_are_not_user_facts(self):
        self.candidates = [memory('The user is a surgeon.',name='user'),memory('An unidentified speaker prefers mornings.',name=None)]
        self.overrides = {'support_0':'unsupported','attribution_1':'unknown'}
        self.store.put_source(self.owner,source(text='Imagine I am a surgeon. I prefer mornings.'))
        result = await self.writer().process_next(self.owner)
        self.assertEqual(result['accepted'],1)
        self.assertIsNone(self.store.search(self.owner)[0]['subject'])
        self.assertEqual(self.store.profile(self.owner),[])

    async def test_filler_and_empty_sources_minimize_calls(self):
        empty=source();empty['passages']=[]
        self.store.put_source(self.owner,empty)
        await self.writer().process_next(self.owner)
        self.assertEqual(self.extractions,0)
        self.candidates=[]
        self.store.put_source(self.owner,source('filler',text='Uh huh.'))
        await self.writer().process_next(self.owner)
        self.assertEqual((self.extractions,self.judgments),(1,0))

    async def test_malformed_output_fails_without_retry_or_partial_write(self):
        self.candidates=[memory()];self.candidates[0]['source_ids']=['invented']
        self.store.put_source(self.owner,source())
        writer=self.writer()
        with self.assertRaises(Rejected): await writer.process_next(self.owner)
        self.assertIsNone(await writer.process_next(self.owner))
        self.assertEqual(self.extractions,1)
        self.assertEqual(self.store.search(self.owner),[])

    async def test_source_deleted_while_provider_runs_cannot_repopulate_cache(self):
        async def extract(request):
            self.store.delete_source(self.owner,'session-a')
            return {'data':{'memories':[memory()]},'usage':{}}
        self.store.put_source(self.owner,source())
        writer=MemoryWriter(self.store,MemoryModels('','',luna_call=extract),self.budget)
        with self.assertRaisesRegex(Rejected,'stale_job'): await writer.process_next(self.owner)
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM job_result').fetchone()[0],0)
        self.assertEqual(self.store.search(self.owner),[])

    async def test_explicit_corrected_expiry_does_not_depend_on_extractor_field(self):
        text='Project Cedar room expires at 2026-09-27T17:00:00+00:00 instead of 2026-09-26T17:00:00+00:00.'
        self.candidates=[memory(text,name='Project Cedar')]
        self.overrides={'expiry_0':'date_0'}
        self.store.put_source(self.owner,source(text=text))
        await self.writer().process_next(self.owner)
        from datetime import datetime
        self.assertEqual(self.store.search(self.owner)[0]['valid_until'],datetime.fromisoformat('2026-09-27T17:00:00+00:00').timestamp())

    async def test_background_upload_learns_without_another_client_action(self):
        from websockets.asyncio.server import serve
        from websockets.asyncio.client import connect
        from memory_service import MemoryService
        credential,token=self.ledger.enroll()
        owner=self.store.owner_for(credential)
        service=MemoryService(self.ledger,self.store)
        worker=asyncio.create_task(MemoryWorker(self.writer(),self.ledger).run())
        try:
            async with serve(service.handle,'127.0.0.1',0) as server:
                port=server.sockets[0].getsockname()[1]
                async with connect(f'ws://127.0.0.1:{port}',additional_headers={'Authorization':'Bearer '+token}) as socket:
                    await socket.send(json.dumps(dict(version=1,owner=owner,operation='upsert',source=source(text='Maya prefers morning meetings.'))))
                    self.assertEqual(json.loads(await socket.recv())['type'],'memory_ack')
                async with asyncio.timeout(3):
                    while not self.store.search(owner):await asyncio.sleep(.02)
                self.assertEqual(self.store.search(owner)[0]['text'],'Maya prefers morning meetings.')
                self.assertEqual((self.extractions,self.judgments),(1,1))
        finally:
            worker.cancel()
            try:await worker
            except asyncio.CancelledError:pass

    async def test_worker_does_not_spend_for_revoked_enrollment(self):
        credential,token=self.ledger.enroll()
        owner=self.store.owner_for(credential)
        self.store.put_source(owner,source())
        self.ledger.revoke(credential)
        self.assertEqual(self.store.pending_owners(self.ledger.active_credentials()),[])

    async def test_similar_names_remain_distinct_and_incomplete_source_is_usable(self):
        self.candidates=[memory('Sam Lee prefers mornings.',name='Sam Lee')]
        self.store.put_source(self.owner,source(text='Sam Lee prefers mornings.'))
        writer=self.writer()
        await writer.process_next(self.owner)
        self.candidates=[memory('Sam Li prefers afternoons.',name='Sam Li')]
        second=source('second',text='Sam Li prefers afternoons.');second['completed']=False
        self.store.put_source(self.owner,second)
        await writer.process_next(self.owner)
        claims=self.store.search(self.owner)
        self.assertEqual(len(claims),2)
        self.assertEqual(len({m['subject'] for m in claims}),2)
        self.assertTrue(all(m['replaces'] is None for m in claims))

    async def test_past_expiry_has_unknown_start_and_remains_historical(self):
        self.candidates=[memory('Maya room pass expired at 1970-01-01T00:02:00Z.')]
        self.overrides={'expiry_0':'date_0'}
        self.store.put_source(self.owner,source(text=self.candidates[0]['text']))
        # Capture happened after expiry. No fabricated interval or automatic resurrection.
        original=source(text=self.candidates[0]['text']);original['revision']=2;original['captured_at']=140.
        self.store.put_source(self.owner,original)
        await self.writer().process_next(self.owner)
        self.assertEqual(self.store.search(self.owner),[])
        old=self.store.search(self.owner,historical=True)[0]
        self.assertIsNone(old['valid_from'])
        self.assertEqual(old['state'],'expired')

    async def test_worker_stops_after_provider_failure_without_retry(self):
        credential,_=self.ledger.enroll();owner=self.store.owner_for(credential)
        self.store.put_source(owner,source())
        self.candidates=[memory()];self.candidates[0]['source_ids']=['missing']
        await asyncio.wait_for(MemoryWorker(self.writer(),self.ledger).run(),2)
        self.assertEqual((self.extractions,self.judgments),(1,0))
        self.assertEqual(self.store.search(owner),[])

    async def test_replay_real_provider_responses_through_lifecycle(self):
        from datetime import datetime
        root=Path(__file__).resolve().parents[1]
        cached={c['session']:c['responses'] for c in json.loads((root/'Fixtures/memory-provider-responses.json').read_text())}
        cases=[c for c in json.loads((root/'Fixtures/memory-learning-cases.json').read_text()) if c['suite']=='heldout-v3']
        now=[datetime.fromisoformat('2026-09-25T12:00:00+00:00').timestamp()]
        self.store.clock=lambda:now[0]
        async def extract(request):return cached[json.loads(request['input'])['session_id']]['extract']
        async def judge(request):return cached[request['state']['source']['session_id']]['judge']
        writer=MemoryWriter(self.store,MemoryModels('','',luna_call=extract,jev_call=judge),self.budget)
        for c in cases:
            now[0]+=60
            data=source(c['id'],text=c['text']);data['captured_at']=now[0]
            self.store.put_source(self.owner,data)
            result=await writer.process_next(self.owner)
            self.assertGreaterEqual(result['accepted'],c['accepted_min'])
            self.assertLessEqual(result['accepted'],c.get('accepted_max',8))
            claims=self.store.search(self.owner,historical=True)
            relevant=[m for m in claims if any(p['session']==c['id'] for p in m['sources'])]
            if c.get('unknown'):self.assertTrue(all(m['subject'] is None for m in relevant))
            if c.get('expiry'):self.assertTrue(any(m['valid_until']==datetime.fromisoformat(c['expiry']).timestamp() for m in relevant))
            if c.get('supersedes'):self.assertTrue(any(m['replaces'] for m in relevant))
            if c.get('duplicate'):self.assertTrue(any(len(m['sources'])==2 for m in relevant))
        now[0]=datetime.fromisoformat('2026-10-01T12:00:00+00:00').timestamp()
        self.store.maintain()
        self.assertEqual(len(self.store.search(self.owner)),2)
        self.assertEqual(len(self.store.search(self.owner,historical=True)),4)
        # New process/store view preserves results; reprocessing incurs no additional calls.
        reopened=MemoryStore(self.store.path,clock=lambda:now[0])
        self.assertIsNone(reopened.claim_job(self.owner))
        self.assertEqual(len(reopened.search(self.owner)),2)

    def test_budget_is_idempotent_bounded_and_preserves_global_history(self):
        receipt=reserve_global_allocation(self.directory/'usage.sqlite')
        self.assertEqual(receipt['global_reserved_microusd'],ALLOCATION)
        for i in range(50):self.budget.reserve(str(i),'fixture')
        with self.assertRaisesRegex(Rejected,'memory_budget_limit'): self.budget.reserve('51','fixture')
        with self.assertRaisesRegex(Rejected,'paid_retry'):self.budget.reserve('0','fixture')
        self.assertEqual(self.budget.report()[0]['reserved_microusd'],ALLOCATION)

    def test_invalid_probabilities_are_rejected(self):
        req=judgment_request(source(),[memory()],[[]]);response=answers(req)
        response['answers']['support_0']['probabilities']['supported']=float('nan')
        with self.assertRaises(Rejected):parse_judgments(response,req)


if __name__=='__main__':unittest.main()
