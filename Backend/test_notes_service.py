import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from websockets.asyncio.server import serve
from websockets.asyncio.client import connect
from admission import Admission, Rejected
from memory_store import MemoryStore
from memory_service import MemoryService
from notes_service import NotesService, NotesWorker
from notes_generation import NotesGenerator
from recording_notes import RecordingNotes
from relay import Relay
from test_memory import source
from test_recording_notes import notes

class Budget:
    def __init__(self):self.calls=[]
    def reserve(self,attempt,model):self.calls.append(attempt)
    def finish(self,*args):pass

class NotesIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory=tempfile.TemporaryDirectory();self.addCleanup(self.directory.cleanup)
        root=Path(self.directory.name)
        self.admission=Admission(root/'usage.sqlite',total_microusd=30000,limits={'ask':(30000,3000,10)})
        self.addCleanup(self.admission.close)
        credential,self.token=self.admission.enroll()
        self.credential=credential
        self.store=MemoryStore(root/'memory.sqlite');self.owner=self.store.owner_for(credential)
        self.notes=RecordingNotes(self.store);self.budget=Budget();self.provider_failure=False
        async def provider(req):
            if self.provider_failure:raise RuntimeError('synthetic network error')
            return {'data':notes(),'usage':{}}
        self.worker=NotesWorker(NotesGenerator(self.store,provider,self.budget),self.admission)
        self.service=NotesService(self.admission,self.store)
        relay=Relay('',admission=self.admission,memory=MemoryService(self.admission,self.store,generate_notes=True),notes=self.service)
        self.server=await serve(relay.handle,'127.0.0.1',0,process_request=relay.authorize)
        self.addAsyncCleanup(self.stop)
        self.url=f'ws://127.0.0.1:{self.server.sockets[0].getsockname()[1]}'

    async def stop(self):self.server.close();await self.server.wait_closed()
    async def send(self,path,data,token=None):
        async with connect(self.url+path,additional_headers={'Authorization':'Bearer '+(token or self.token)}) as socket:
            await socket.send(json.dumps(data));return json.loads(await socket.recv())
    async def sync(self,data):
        return await self.send('/memory',dict(version=1,owner=self.owner,operation='upsert',source=data))
    async def read(self,operation='read',revision=1):
        return await self.send('/notes',dict(operation=operation,session_id='session-a',revision=revision))

    async def test_socket_sync_generate_reopen_reference_and_delete(self):
        self.assertEqual((await self.sync(source()))['status'],'stored')
        self.assertEqual((await self.read())['result']['state'],'pending')
        self.assertTrue(await self.worker.step())
        ready=await self.read();self.assertEqual(ready['result']['notes'],notes())
        self.assertEqual(ready['result']['notes']['overview']['passages'],['p1'])
        self.assertEqual(self.store.source(self.owner,'session-a')['passages'][0]['id'],'p1')
        await self.sync(source());await self.read();self.assertFalse(await self.worker.step())
        self.assertEqual(len(self.budget.calls),1)
        reopened=RecordingNotes(MemoryStore(self.store.path))
        self.assertEqual(reopened.read(self.owner,'session-a')['notes'],notes())
        await self.send('/memory',dict(version=1,owner=self.owner,operation='delete',session_id='session-a'))
        self.assertEqual((await self.read())['message'],'source_unavailable')

    async def test_failed_attempt_needs_explicit_retry_and_new_reservation(self):
        await self.sync(source());self.provider_failure=True;await self.worker.step()
        self.assertEqual((await self.read())['result']['state'],'failed')
        await self.sync(source());self.assertFalse(await self.worker.step())
        self.provider_failure=False
        self.assertEqual((await self.read('retry'))['result']['state'],'pending')
        await self.worker.step();self.assertEqual((await self.read())['result']['state'],'ready')
        self.assertEqual(len(set(self.budget.calls)),2)
        self.assertEqual((await self.read('retry'))['message'],'notes_not_retryable')

    async def test_no_backfill_cross_owner_or_stale_revision(self):
        self.store.put_source(self.owner,source());await self.sync(source())
        self.assertIsNone((await self.read())['result']);self.assertFalse(await self.worker.step())
        await self.sync(source(revision=2))
        self.assertEqual((await self.read())['message'],'stale_notes')
        _,other=self.admission.enroll()
        result=await self.send('/notes',dict(operation='read',session_id='session-a',revision=2),other)
        self.assertEqual(result['message'],'source_unavailable')
        await self.worker.step();self.assertEqual((await self.read(revision=2))['result']['state'],'ready')

    async def test_empty_and_personal_sources_never_spend_and_capture_has_priority(self):
        empty=source();empty['passages']=[]
        await self.sync(empty)
        self.assertEqual((await self.read())['result']['error'],'empty_transcript')
        self.assertEqual((await self.read('retry'))['message'],'notes_not_retryable')
        self.assertFalse(await self.worker.step())
        await self.sync(source(revision=2))
        self.worker.busy=lambda:True;self.assertFalse(await self.worker.step())
        self.assertEqual(self.budget.calls,[])
        self.store.put_source(self.owner,dict(source(session='personal'),origin='personal_text'),generate_notes=True)
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM recording_notes WHERE session='personal'").fetchone()[0],0)
        self.worker.busy=lambda:False
        self.admission.revoke(self.credential)
        self.assertFalse(await self.worker.step())
        self.assertEqual(self.budget.calls,[])
