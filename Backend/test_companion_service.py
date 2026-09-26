import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import tempfile
import unittest
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from admission import Admission
from companion_service import CompanionService
from companion_chat import CompanionChat
from memory_store import MemoryStore
from test_memory import source


def question(key='q1',**changes):
    return dict(operation='ask',question_id=key,question='What does Maya enjoy?',memory=True,attachment=None,live=None)|changes

class Provider:
    def __init__(self):self.calls=[];self.stall=False;self.bad=False;self.closed=asyncio.Event()
    async def stream(self,data):
        self.calls.append(data)
        try:
            yield dict(type='delta',text='Swimming [[p999]]' if self.bad else ('Swimming [[p1]]' if data['sources'] else 'Hello.'))
            if self.stall:await asyncio.Future()
            yield dict(type='completed')
        finally:self.closed.set()

class CompanionServiceTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def service(self):
        with tempfile.TemporaryDirectory() as d:
            admission=Admission(Path(d)/'usage.sqlite',total_microusd=30000,limits={'ask':(30000,3000,20)})
            credential,token=admission.enroll();memory=MemoryStore(Path(d)/'memory.sqlite');owner=memory.owner_for(credential)
            provider=Provider();handler=CompanionService(admission,memory,provider)
            try:
                async with serve(handler.handle,'127.0.0.1',0,max_size=64000) as server:
                    yield admission,token,memory,owner,provider,f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}'
            finally:admission.close()

    async def call(self,url,token,data):
        async with connect(url,additional_headers={'Authorization':'Bearer '+token}) as ws:
            await ws.send(json.dumps(data));return [json.loads(item) async for item in ws]

    async def test_live_save_replay_followup_and_history(self):
        async with self.service() as (a,token,m,owner,p,url):
            live=source('recording',text='Maya enjoys swimming.');live['completed']=False
            req=question(live=live)
            self.assertTrue((await self.call(url,token,req))[-1]['saved'])
            self.assertEqual((await self.call(url,token,req))[-1]['type'],'existing')
            self.assertEqual(len(p.calls),1);self.assertEqual(a.usage(),[('ask',1,3000)])
            self.assertEqual((await self.call(url,token,question(memory=False,live=live)))[-1]['message'],'question_id_conflict')
            m.put_source(owner,source('recording',text='Maya enjoys swimming. And painting.'))
            self.assertTrue((await self.call(url,token,question('q2',question='What about her hobby?')))[-1]['saved'])
            self.assertEqual(p.calls[-1]['history'][0]['user'],'What does Maya enjoy?')
            history=(await self.call(url,token,dict(operation='history',before=None)))[0]
            self.assertEqual(len(history['turns']),2)
            m.delete_source(owner,'recording')
            self.assertTrue(all(t['answer'] is None for t in (await self.call(url,token,dict(operation='history',before=None)))[0]['turns']))

    async def test_empty_chat_invalid_input_and_owner_isolation(self):
        async with self.service() as (a,token,m,owner,p,url):
            self.assertEqual((await self.call(url,token,{'operation':'ask','history':[]}))[-1]['type'],'error')
            self.assertEqual(len(p.calls),0)
            self.assertTrue((await self.call(url,token,question()))[-1]['saved'])
            _,other=a.enroll()
            self.assertEqual((await self.call(url,other,dict(operation='history',before=None)))[0]['turns'],[])
            async with connect(url,additional_headers={'Authorization':'Bearer invalid'}) as ws:
                self.assertEqual(json.loads(await ws.recv())['message'],'unauthorized')
            self.assertEqual(len(p.calls),1)

    async def test_disconnect_cleans_snapshot_and_never_retries(self):
        async with self.service() as (a,token,m,owner,p,url):
            p.stall=True;live=source('recording');live['completed']=False;req=question(live=live)
            async with connect(url,additional_headers={'Authorization':'Bearer '+token}) as ws:
                await ws.send(json.dumps(req))
                while json.loads(await ws.recv())['type']!='delta':pass
            await asyncio.wait_for(p.closed.wait(),2)
            # A second connection is serialized after the handler finishes its bounded cleanup.
            for _ in range(20):
                state=CompanionChat(m).page(owner)['turns'][0]['state']
                if state!='pending':break
                await asyncio.sleep(.01)
            self.assertEqual(state,'failed')
            self.assertEqual((await self.call(url,token,req))[-1]['turn']['state'],'failed')
            self.assertEqual(len(p.calls),1)
            with m.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM companion_snapshot').fetchone()[0],0)

    async def test_deletion_and_revocation_interrupt_stalled_answer(self):
        for revoke in (False,True):
            async with self.service() as (a,token,m,owner,p,url):
                p.stall=True;live=source('recording');live['completed']=False
                async with connect(url,additional_headers={'Authorization':'Bearer '+token}) as ws:
                    await ws.send(json.dumps(question(live=live)))
                    while json.loads(await ws.recv())['type']!='delta':pass
                    if revoke:a.revoke(a.authorized(token))
                    else:m.delete_source(owner,'recording')
                    event=json.loads(await asyncio.wait_for(ws.recv(),2))
                    self.assertEqual(event['message'],'unauthorized' if revoke else 'memory_context_changed')
                await asyncio.wait_for(p.closed.wait(),2)

    async def test_invalid_citation_is_not_saved_and_recovery_never_infers(self):
        async with self.service() as (a,token,m,owner,p,url):
            p.bad=True
            self.assertEqual((await self.call(url,token,question()))[-1]['message'],'invalid_references')
            self.assertEqual(CompanionChat(m).page(owner)['turns'][0]['state'],'failed')
            CompanionChat(m).start(owner,'interrupted','Another question')
            self.assertEqual(CompanionChat(m).recover_interrupted(),1)
            self.assertEqual(CompanionChat(m).recover_interrupted(),0)
            self.assertEqual(len(p.calls),1)

    async def test_disabled_memory_skips_retrieval_and_provider_failure_has_no_saved_answer(self):
        async with self.service() as (a,token,m,owner,p,url):
            self.assertTrue((await self.call(url,token,question(memory=False)))[-1]['saved'])
            self.assertEqual(p.calls[0]['memory_status'],'disabled')
            self.assertEqual(p.calls[0]['history'],[])
