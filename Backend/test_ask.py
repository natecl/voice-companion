import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import tempfile
import unittest
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from admission import Admission, Rejected
from ask import AskService, validate_request, references
from relay import Relay
from service_policy import add_ask_policy, STT, ASK

QUESTION = {'question':'What time?', 'passages':[{'id':'p1','start':0,'text':'We meet at noon.'}]}

class FakeLuna:
    def __init__(self):
        self.calls = 0
        self.closed = asyncio.Event()
        self.stall = False
        self.bad = False
    async def stream(self, data):
        self.calls += 1
        try:
            yield {'type':'delta','text':'Noon [[p9]].' if self.bad else 'Noon [[p1]].'}
            if self.stall: await asyncio.Future()
            yield {'type':'completed','input_tokens':100,'output_tokens':10}
        finally:
            self.closed.set()

class AskTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def service(self):
        with tempfile.TemporaryDirectory() as d:
            store=Admission(Path(d)/'ledger',total_microusd=6000,limits={'ask':(6000,3000,20)})
            owner,token=store.enroll()
            provider=FakeLuna()
            relay=Relay('unused',admission=store,ask=AskService(store,provider))
            try:
                async with serve(relay.handle,'127.0.0.1',0,process_request=relay.authorize) as server:
                    yield store,owner,token,provider,f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/ask'
            finally: store.close()

    async def call(self,url,token,data=QUESTION):
        result=[]
        async with connect(url,additional_headers={'Authorization':'Bearer '+token}) as ws:
            await ws.send(json.dumps(data))
            async for message in ws: result.append(json.loads(message))
        return result

    async def test_repeated_answers_and_budget_denial(self):
        async with self.service() as (store,owner,token,provider,url):
            for _ in range(2):
                result=await self.call(url,token)
                self.assertEqual(result[-1],{'type':'done','references':['p1']})
            self.assertEqual((await self.call(url,token))[-1]['message'],'budget_limit')
            self.assertEqual(provider.calls,2)
            self.assertTrue(provider.closed.is_set())

    async def test_invalid_request_never_calls_provider(self):
        async with self.service() as (store,owner,token,provider,url):
            for bad in ({'question':'no passages'}, {**QUESTION,'question':'x'*13000}):
                self.assertEqual((await self.call(url,token,bad))[-1]['type'],'error')
            self.assertEqual(provider.calls,0)
            self.assertEqual(store.usage(),[])

    async def test_disconnect_cancels_upstream_and_keeps_reservation(self):
        async with self.service() as (store,owner,token,provider,url):
            provider.stall=True
            async with connect(url,additional_headers={'Authorization':'Bearer '+token}) as ws:
                await ws.send(json.dumps(QUESTION)); await ws.recv(); await ws.recv()
            await asyncio.wait_for(provider.closed.wait(),2)
            self.assertEqual(store.usage(),[('ask',1,3000)])

    async def test_revocation_during_answer_cancels_generation(self):
        async with self.service() as (store,owner,token,provider,url):
            provider.stall=True
            async with connect(url,additional_headers={'Authorization':'Bearer '+token}) as ws:
                await ws.send(json.dumps(QUESTION)); await ws.recv(); await ws.recv()
                store.revoke(owner)
                event=json.loads(await asyncio.wait_for(ws.recv(),2))
                self.assertEqual(event['message'],'unauthorized')
            self.assertTrue(provider.closed.is_set())

    async def test_unknown_reference_never_marked_complete(self):
        async with self.service() as (store,owner,token,provider,url):
            provider.bad=True
            self.assertEqual((await self.call(url,token))[-1]['message'],'invalid_references')
            self.assertEqual(store.db.execute('SELECT state FROM request').fetchone()[0],'failed')

    def test_validation_and_migration_preserve_accounting(self):
        with self.assertRaises(Rejected): references('Wrong [[p2]]',QUESTION['passages'])
        self.assertEqual(validate_request(json.dumps(QUESTION)),QUESTION)
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'ledger'
            store=Admission(path,total_microusd=5_000_000,limits={'stt':STT})
            _,token=store.enroll(); req=store.reserve(token,'stt'); store.finish(req,completed=True); store.close()
            add_ask_policy(path); add_ask_policy(path)
            store=Admission(path,total_microusd=5_000_000,limits={'stt':STT,'ask':ASK})
            self.assertEqual(store.usage(),[('stt',1,20000)])
            store.authorized(token); store.close()

class RetiredAccountingTests(unittest.TestCase):
    def test_direct_baseline_preserves_retired_experiment_charges(self):
        import os
        from unittest.mock import patch
        from service_policy import open_ledger, RETIRED_JEV
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'usage.sqlite'
            store=Admission(path,total_microusd=5_000_000,limits={'stt':STT,'ask':ASK,'jev':RETIRED_JEV})
            _,token=store.enroll();request=store.reserve(token,'jev');store.finish(request,completed=False);store.close()
            with patch.dict(os.environ,{'VOICE_DATA_DIR':d,'VOICE_ENABLE_ASK':'1'}):
                store=open_ledger(migrate=True)
                self.assertEqual(store.usage(),[('jev',1,500)])
                store.authorized(token)
                request=store.reserve(token,'ask');store.finish(request,completed=True)
                self.assertEqual(store.usage(),[('ask',1,3000),('jev',1,500)])
                store.close()
