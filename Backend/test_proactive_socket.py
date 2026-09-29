import asyncio,json
from pathlib import Path
import tempfile
import unittest
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from admission import Admission
from memory_store import MemoryStore
from proactive_service import ProactiveService
from proactive_socket import ProactiveSocketService,request
from companion_chat import CompanionChat
from test_proactive_service import Models,Budget
from test_memory import source

class SocketTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.admission=Admission(Path(folder.name)/'usage',total_microusd=1,limits={'qa':(1,1,1)})
        self.addCleanup(self.admission.close)
        credential,self.token=self.admission.enroll()
        self.store=MemoryStore(Path(folder.name)/'memory');self.owner=self.store.owner_for(credential)
        self.store.put_source(self.owner,source('prior',text='Alex wakes at three each morning.'))
        self.live=dict(source('capture',text='Discussing Alex waking at three with the doctor.'),completed=False)
        self.models=Models();self.now=0.
        self.handler=ProactiveSocketService(self.admission,ProactiveService(self.store,self.models,Budget()),clock=lambda:self.now)
        self.server=await serve(self.handler.handle,'127.0.0.1',0)
        self.url=f'ws://127.0.0.1:{self.server.sockets[0].getsockname()[1]}'
    async def asyncTearDown(self):
        self.server.close();await self.server.wait_closed()
    async def open(self,token=None):
        socket=await connect(self.url,additional_headers={'Authorization':'Bearer '+(token or self.token)})
        await socket.send(json.dumps(dict(operation='open',capture='capture')))
        return socket,json.loads(await socket.recv())
    async def observe(self,socket):await socket.send(json.dumps(dict(operation='observe',live=self.live)))
    async def test_save_once_and_quiet_survives_reconnect(self):
        socket,event=await self.open();self.assertTrue(event['enabled'])
        await self.observe(socket)
        self.assertEqual(json.loads(await socket.recv())['type'],'contribution')
        await socket.send(json.dumps(dict(operation='quiet',capture='capture')))
        self.assertEqual(json.loads(await socket.recv())['type'],'quiet');await socket.close()
        await asyncio.sleep(.01)
        socket,event=await self.open();self.assertFalse(event['enabled'])
        self.live['revision']=2;self.now=80;await self.observe(socket)
        await socket.close()
        self.assertEqual(len(self.models.calls),1)
        self.assertEqual(len(CompanionChat(self.store).page(self.owner)['turns']),1)
    async def test_disconnect_cancels_provider_work_and_rejects_invalid_auth(self):
        self.models.stall=True
        socket,_=await self.open();await self.observe(socket)
        for _ in range(100):
            if self.models.calls:break
            await asyncio.sleep(.001)
        self.assertEqual(len(self.models.calls),1);await socket.close();await asyncio.sleep(.01)
        self.assertEqual(CompanionChat(self.store).page(self.owner)['turns'],[])
        socket=await connect(self.url,additional_headers={'Authorization':'Bearer bad'})
        self.assertEqual(json.loads(await socket.recv())['type'],'unavailable');await socket.close()
        self.assertEqual(len(self.models.calls),1)
    async def test_revision_rewind_is_rejected(self):
        socket,_=await self.open();self.live['revision']=2
        await self.observe(socket)
        self.assertEqual(json.loads(await socket.recv())['type'],'contribution')
        self.live['revision']=1;await self.observe(socket)
        self.assertEqual(json.loads(await socket.recv())['type'],'unavailable')
        await socket.close();self.assertEqual(len(self.models.calls),1)

    def test_payload_cannot_supply_owner_or_completed_recording(self):
        for payload in (dict(operation='open',capture='capture',owner='someone'),
                        dict(operation='observe',live=dict(self.live,completed=True))):
            with self.assertRaises(Exception):request(json.dumps(payload))

    async def test_expired_response_recovers_on_additive_speech(self):
        entered=asyncio.Event();release=asyncio.Event();returned=asyncio.Event()
        original=self.models.extract
        async def delayed(request):
            entered.set();await release.wait()
            result=await original(request);returned.set();return result
        self.models.extract=delayed
        socket,_=await self.open();await self.observe(socket)
        await asyncio.wait_for(entered.wait(),1)
        self.now=16;release.set()
        await asyncio.wait_for(returned.wait(),1)
        self.assertEqual(CompanionChat(self.store).page(self.owner)['turns'],[])
        self.now=21;self.live['revision']=2
        self.live['passages'][0]['text']+=' More discussion.'
        await self.observe(socket)
        event=json.loads(await asyncio.wait_for(socket.recv(),1))
        self.assertEqual(event['type'],'contribution')
        self.assertEqual(len(self.models.calls),2)
        reopened=CompanionChat(MemoryStore(self.store.path)).page(self.owner)['turns']
        self.assertEqual(len(reopened),1)
        await socket.close()

    async def test_quiet_cancels_stubborn_response_but_accepts_more_live_text(self):
        await self.check_pending_control('quiet')

    async def test_end_cancels_stubborn_response(self):
        await self.check_pending_control('stop')

    async def check_pending_control(self,operation):
        entered=asyncio.Event()
        original=self.models.extract
        async def stubborn(request):
            entered.set()
            try:await asyncio.Future()
            except asyncio.CancelledError:pass
            return await original(request)
        self.models.extract=stubborn
        socket,_=await self.open();await self.observe(socket)
        await asyncio.wait_for(entered.wait(),1)
        await socket.send(json.dumps(dict(operation=operation,capture='capture')))
        self.assertEqual(json.loads(await asyncio.wait_for(socket.recv(),1))['type'],'quiet')
        self.assertEqual(CompanionChat(MemoryStore(self.store.path)).page(self.owner)['turns'],[])
        self.assertEqual(len(self.models.calls),1)
        if operation=='quiet':
            self.now=30;self.live['revision']=2
            self.live['passages'][0]['text']+=' Capture continues with new text.'
            await self.observe(socket)
            policy=self.handler.policies[(self.owner,'capture')]
            for _ in range(100):
                if policy.latest_source['revision']==2:break
                await asyncio.sleep(.001)
            self.assertEqual(policy.latest_source['revision'],2)
            self.assertEqual(policy.capture,'capture')
            self.assertFalse(policy.enabled)
            self.assertEqual(len(self.models.calls),1)
        await socket.close()
