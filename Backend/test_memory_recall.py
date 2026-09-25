import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from admission import Rejected
from memory_store import MemoryStore
from memory_recall import MemoryRecall, shortlist, relevance_request
from memory_models import JEV
from test_memory import source, candidate
from test_ask import QUESTION


class Budget:
    def __init__(self): self.calls = 0
    def reserve(self, *args): self.calls += 1
    def finish(self, *args): pass


class Judge:
    async def judge(self, request):
        label = 'historical' if 'previous' in request['state']['question'] else 'relevant'
        return {'usage':{}, 'data':{'model':JEV, 'answers':{
            key:{'type':'choice','choice':label,'confidence':1.,
                 'probabilities':{option:float(option == label) for option in request['questions'][key]['criteria']}}
            for key in request['questions']}}}


class RecallTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.store = MemoryStore(Path(self.temp.name)/'memory.sqlite', clock=lambda:150.)
        self.owner = self.store.owner_for('credential')
        self.budget = Budget()
        self.recall = MemoryRecall(self.store, Judge(), self.budget)

    async def test_owner_isolation_and_deletion_invalidate_manifest(self):
        self.store.put_source(self.owner, source())
        other = self.store.owner_for('other')
        self.store.put_source(other, source('private', text='Secret other owner'))
        manifest = await self.recall.prepare('credential', QUESTION)
        self.assertEqual(len(manifest['sources']), 1)
        self.assertEqual(manifest['sources'][0]['session_id'], 'session-a')
        self.store.delete_source(self.owner, 'session-a')
        with self.assertRaisesRegex(Rejected, 'memory_context_changed'):
            await self.recall.validate(manifest)

    async def test_expired_raw_passage_cannot_reenter_current_context(self):
        self.store.put_source(self.owner, source())
        job = self.store.claim_job(self.owner)
        self.store.commit_claims(job, [candidate(valid_until=120.)])
        current = await self.recall.prepare('credential', QUESTION)
        self.assertEqual(current['sources'], [])
        self.assertEqual(self.budget.calls, 1)
        history = await self.recall.prepare('credential', {**QUESTION, 'question':'What was the previous appointment?'})
        self.assertEqual(history['sources'][0]['lifecycle'][0]['state'], 'expired')

    async def test_current_session_is_not_duplicated_and_context_budget_preserved(self):
        self.store.put_source(self.owner, source())
        result = await self.recall.prepare('credential', {**QUESTION, 'session_id':'session-a'})
        self.assertEqual(result['sources'], [])
        self.assertEqual(self.budget.calls, 0)

    async def test_relevance_failure_does_not_retry(self):
        self.store.put_source(self.owner, source())
        class Broken:
            async def judge(self, request): raise RuntimeError('provider failed')
        self.recall.models = Broken()
        with self.assertRaises(RuntimeError): await self.recall.prepare('credential', QUESTION)
        self.assertEqual(self.budget.calls, 1)

class RecallAskTests(unittest.IsolatedAsyncioTestCase):
    async def exercise(self, *, delete_during_answer=False, outage=False):
        from admission import Admission
        from ask import AskService
        from websockets.asyncio.server import serve
        from websockets.asyncio.client import connect
        with tempfile.TemporaryDirectory() as directory:
            ledger = Admission(Path(directory)/'usage.sqlite', total_microusd=6000, limits={'ask':(6000,3000,20)})
            credential, token = ledger.enroll()
            store = MemoryStore(Path(directory)/'memory.sqlite', clock=lambda:150.)
            owner = store.owner_for(credential)
            store.put_source(owner, source(text='Maya prefers mornings.'))
            recall = MemoryRecall(store, Judge(), Budget())
            if outage:
                async def failed(*args): raise RuntimeError('unavailable')
                recall.prepare = failed
            received = []
            class Answer:
                async def stream(self, data):
                    received.append(data)
                    yield {'type':'delta', 'text':'Mornings [[m1]].' if data.get('past_sources') else 'Current only [[p1]].'}
                    if delete_during_answer:
                        store.delete_source(owner, 'session-a')
                    yield {'type':'completed','input_tokens':10,'output_tokens':10}
            try:
                async with serve(AskService(ledger, Answer(), recall).handle, '127.0.0.1', 0) as server:
                    url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}'
                    async with connect(url, additional_headers={'Authorization':'Bearer '+token}) as socket:
                        await socket.send(json.dumps({**QUESTION, 'question':'What does Maya prefer?', 'memory':True, 'session_id':'now'}))
                        events = []
                        while True:
                            event = json.loads(await socket.recv()); events.append(event)
                            if event['type'] in ('done','error'): break
                self.assertEqual(len(received), 1)
                return events
            finally:
                ledger.close()

    async def test_actual_socket_recall_context_and_citations(self):
        events = await self.exercise()
        context = next(e for e in events if e['type']=='context')
        self.assertEqual(context['sources'][0]['session_id'], 'session-a')
        self.assertEqual(events[-1], {'type':'done','references':['m1']})

    async def test_deleted_source_cannot_complete_answer(self):
        events = await self.exercise(delete_during_answer=True)
        self.assertEqual(events[-1]['message'], 'memory_context_changed')
        self.assertFalse(any(e['type']=='done' for e in events))

    async def test_outage_has_notice_and_single_current_context_answer(self):
        events = await self.exercise(outage=True)
        self.assertEqual(next(e for e in events if e['type']=='context')['memory_status'], 'unavailable')
        self.assertEqual(events[-1]['references'], ['p1'])
