"""Actual hosted startup/routing with no source jobs and no paid provider requests."""
import asyncio
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.request import urlopen
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus
from websockets.asyncio.server import serve
from admission import Admission
from companion_chat import CompanionChat
from companion_service import CompanionService
from hosted import rework_settings, validate_rework_allocations
from memory_store import MemoryStore
from memory_budget import MemoryBudget, reserve_global_allocation
import profile_budget
from relay import Relay
from service_policy import STT, ASK, RETIRED_JEV, ROLLOUT_POLICIES

FLAGS={name:'1' for name in ('VOICE_ENABLE_MEMORY_REWORK','VOICE_ENABLE_COMPANION','VOICE_ENABLE_MEMORY',
    'VOICE_ENABLE_PERSONAL_LEARNING','VOICE_ENABLE_MEMORY_LEARNING','VOICE_ENABLE_MEMORY_RECALL','VOICE_ENABLE_ASK')}

class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    def test_invalid_combinations_fail_closed(self):
        self.assertEqual(rework_settings({}),(False,False,False))
        self.assertEqual(rework_settings(FLAGS),(True,True,False))
        for env in ({'VOICE_ENABLE_COMPANION':'1'},dict(FLAGS,VOICE_ENABLE_MEMORY='0'),
                    dict(FLAGS,VOICE_ENABLE_MEMORY_REWORK='yes'),dict(FLAGS,VOICE_ENABLE_SEMANTIC_INDEX='1')):
            with self.assertRaises(ValueError):rework_settings(env)

    async def test_route_requires_enablement_and_authorization_without_stt(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger=Admission(Path(folder)/'usage.sqlite',total_microusd=30000,limits={'ask':(30000,3000,20)})
            _,token=ledger.enroll();memory=MemoryStore(Path(folder)/'memory.sqlite')
            class Provider:
                async def stream(self,data):
                    yield dict(type='delta',text='Hello');yield dict(type='completed')
            handler=CompanionService(ledger,memory,Provider())
            for enabled in (False,True):
                relay=Relay('never-used',admission=ledger,companion=handler if enabled else None)
                async with serve(relay.handle,'127.0.0.1',0,process_request=relay.authorize) as server:
                    url=f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/companion'
                    if not enabled:
                        with self.assertRaises(InvalidStatus) as error:
                            async with connect(url,additional_headers={'Authorization':'Bearer '+token}):pass
                        self.assertEqual(error.exception.response.status_code,404)
                        continue
                    with self.assertRaises(InvalidStatus) as error:
                        async with connect(url):pass
                    self.assertEqual(error.exception.response.status_code,401)
                    async with connect(url,additional_headers={'Authorization':'Bearer '+token}) as ws:
                        await ws.send(json.dumps(dict(operation='ask',question_id='one',question='Hello',memory=False,attachment=None,live=None)))
                        events=[json.loads(raw) async for raw in ws]
                    self.assertTrue(events[-1]['saved']);self.assertEqual(relay.sessions,0)
            self.assertEqual(ledger.usage(),[('ask',1,3000)])
            ledger.close()

    async def test_actual_rework_process_recovers_chat_and_serves_history_without_spend(self):
        with tempfile.TemporaryDirectory() as folder:
            directory=Path(folder);global_path=directory/'usage.sqlite';budget_path=directory/'memory-budget.sqlite'
            admission=Admission(global_path,total_microusd=5_000_000,limits={'stt':STT,'ask':ASK,'jev':RETIRED_JEV})
            credential,token=admission.enroll()
            receipt=reserve_global_allocation(global_path)
            (directory/'memory-allocation.json').write_text(json.dumps(receipt));MemoryBudget(budget_path,receipt)
            profile_budget.provision(global_path,budget_path)
            profile_budget.provision_rework_allowance(global_path,budget_path)
            profile_budget.provision_consolidation_allowance(global_path,budget_path)
            profile_budget.provision_multisource_allowance(global_path,budget_path)
            profile_budget.provision_rollout_allowance(global_path,budget_path)
            validate_rework_allocations(admission,rollout=True)
            before=admission.usage();admission.close()
            cache=os.environ.get('VOICE_TEST_EMBEDDING_CACHE')
            from local_embeddings import CONTRACT
            memory=MemoryStore(directory/'memory.sqlite',embedding_model=CONTRACT if cache else None)
            owner=memory.owner_for(credential)
            if cache:
                from test_memory import source
                memory.put_source(owner,source('index-fixture',text='Maya enjoys swimming.'))
                # Isolate local indexing: this synthetic QA source must never run paid learning.
                with memory.connect() as db:db.execute("UPDATE job SET state='failed' WHERE session='index-fixture'")
            CompanionChat(memory).start(owner,'interrupted','Unfinished question')
            with socket.socket() as sock:
                sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            env={k:v for k,v in os.environ.items() if not k.startswith('VOICE_ENABLE_')}
            env.update(FLAGS,VOICE_ENABLE_ROLLOUT_QA='1',VOICE_DATA_DIR=folder,XAI_API_KEY='unused',OPENAI_API_KEY='unused',TYPESAFE_API_KEY='unused',PORT=str(port))
            if cache:env.update(VOICE_ENABLE_SEMANTIC_INDEX='1',VOICE_EMBEDDING_CACHE=cache,HF_HUB_OFFLINE='1')
            process=subprocess.Popen([sys.executable,str(Path(__file__).with_name('hosted.py'))],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
            try:
                for _ in range(150):
                    try:
                        with urlopen(f'http://127.0.0.1:{port}/health',timeout=.2) as response:
                            self.assertEqual(response.status,200);break
                    except OSError:
                        if process.poll() is not None:self.fail(process.stderr.read().decode())
                        await asyncio.sleep(.02)
                else:self.fail('Hosted startup did not become healthy')
                async with connect(f'ws://127.0.0.1:{port}/companion',additional_headers={'Authorization':'Bearer '+token}) as ws:
                    await ws.send(json.dumps(dict(operation='history',before=None)))
                    history=json.loads(await ws.recv())
                self.assertEqual(history['turns'][0]['state'],'failed')
                self.assertEqual(history['turns'][0]['question'],'Unfinished question')
                for _ in range(150):
                    with urlopen(f'http://127.0.0.1:{port}/health/indexing') as response:index_state=json.load(response)
                    if not cache or index_state.get('completed')==1:break
                    if index_state['state']=='halted':self.fail(str(index_state))
                    await asyncio.sleep(.02)
                self.assertEqual(index_state['state'],'idle' if cache else 'disabled')
                if cache:
                    self.assertEqual(index_state['completed'],1)
                    with memory.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM memory_embedding').fetchone()[0],1)
                with urlopen(f'http://127.0.0.1:{port}/health/learning') as response:
                    self.assertEqual(json.load(response)['state'],'idle')
                admission=Admission(global_path,total_microusd=5_000_000,limits=ROLLOUT_POLICIES)
                self.assertEqual(admission.usage(),before);admission.close()
                self.assertEqual(profile_budget.ProfileBudget(budget_path,include_rework_allowance=True,
                    include_consolidation_allowance=True,include_multisource_allowance=True).report(),[])
            finally:
                process.terminate();process.wait(timeout=5);process.stderr.close()
