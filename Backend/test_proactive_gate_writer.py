"""Separate gate/writer behavior through the real service; synthetic model decisions."""
import json
import tempfile
import unittest
from pathlib import Path
from admission import Rejected
from companion_chat import CompanionChat
from memory_models import JEV, LUNA
from memory_store import MemoryStore
from proactive_service import ProactiveService
from proactive_writer import writer_request, parse_writer
from test_proactive_service import Budget, Models
from test_memory import source

class GateWriterTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        self.path=Path(directory.name)/'memory.sqlite'
        self.store=MemoryStore(self.path,clock=lambda:300.)
        self.owner=self.store.owner_for('fictional-gate-writer')
        self.store.put_source(self.owner,source('prior',text='The Cedar team agreed to test with five people before adding features.'))
        self.live=dict(source('capture',text='Should the Cedar team add calendar integration before the five-person test?'),completed=False)
        self.budget=Budget();self.active=True
        parent=self
        class Pair(Models):
            def __init__(inner):
                super().__init__();inner.after_gate=lambda:None;inner.writer_empty=False;inner.invalid=False;inner.gate_failed=False;inner.gate_uncertain=False
            async def judge(inner,request):
                if inner.gate_failed:
                    inner.calls.append(request);raise Rejected('invalid_judgment')
                response=await super().judge(request)
                if inner.gate_uncertain:
                    answer=response['data']['answers']['novelty']
                    answer['probabilities']={'new':.85,'covered':.10,'uncertain':.05}
                inner.after_gate()
                return response
            async def extract(inner,request):
                inner.calls.append(request)
                parent.assertNotIn('decision',request['text']['format']['schema']['properties'])
                parent.assertEqual(request['text']['format']['name'],'proactive_writer_v1')
                return dict(usage={},data=dict(messages=[] if inner.writer_empty else ['Have those five people tried it yet?', 'The team agreed to test before adding features.'],
                    evidence_ids=[] if inner.writer_empty else ['m99' if inner.invalid else 'm1']))
        self.models=Pair()
        self.service=ProactiveService(self.store,self.models,self.budget,route='jev_writer')

    async def evaluate(self):return await self.service.evaluate(self.owner,self.live,lambda:self.active)

    async def test_allow_writes_separate_messages_once_and_preserves_context(self):
        result=await self.evaluate();self.assertEqual(result['type'],'contribution')
        self.assertEqual([r['model'] for r in self.models.calls],[JEV,LUNA])
        self.assertEqual(self.models.calls[0]['state'],json.loads(self.models.calls[1]['input']))
        turns=CompanionChat(MemoryStore(self.path)).page(self.owner)['turns']
        self.assertEqual(len(turns),1);self.assertEqual(len(turns[0]['answer'].split('\n\n')),2)
        self.assertEqual((await self.evaluate())['type'],'existing')
        self.assertEqual(len(self.budget.attempts),2)

    async def test_gate_denial_stops_before_writer(self):
        self.models.silence=True
        self.assertEqual((await self.evaluate())['type'],'silence')
        self.assertEqual(len(self.models.calls),1)
        self.assertEqual(len(self.budget.attempts),1)

    async def test_frozen_uncertain_threshold_does_not_silently_change(self):
        self.models.gate_uncertain=True
        self.assertEqual((await self.evaluate())['type'],'silence')
        self.assertEqual(len(self.models.calls),1)

    async def test_gate_failure_has_no_writer_or_retry(self):
        self.models.gate_failed=True
        self.assertEqual((await self.evaluate())['type'],'unavailable')
        self.assertEqual((await self.evaluate())['type'],'existing')
        self.assertEqual(len(self.models.calls),1)

    async def test_writer_can_abstain_after_positive_gate(self):
        self.models.writer_empty=True
        self.assertEqual((await self.evaluate())['type'],'silence')
        self.assertEqual(len(self.models.calls),2)
        self.assertEqual(CompanionChat(self.store).page(self.owner)['turns'],[])

    async def test_quiet_between_gate_and_writer_stops_writer(self):
        self.models.after_gate=lambda:setattr(self,'active',False)
        self.assertEqual((await self.evaluate())['type'],'cancelled')
        self.assertEqual(len(self.models.calls),1)

    async def test_source_deletion_between_calls_stops_writer(self):
        self.models.after_gate=lambda:self.store.delete_source(self.owner,'prior')
        self.assertEqual((await self.evaluate())['type'],'unavailable')
        self.assertEqual(len(self.models.calls),1)
        self.assertEqual(CompanionChat(self.store).page(self.owner)['turns'],[])

    async def test_invalid_writer_is_not_saved_or_retried(self):
        self.models.invalid=True
        self.assertEqual((await self.evaluate())['type'],'unavailable')
        self.assertEqual((await self.evaluate())['type'],'existing')
        self.assertEqual(len(self.models.calls),2)
        self.assertEqual(CompanionChat(self.store).page(self.owner)['turns'],[])

    def test_writer_contract_preserves_existing_bounds(self):
        state=dict(current={},sources=[dict(id='m1',text='Original evidence')],previous=[])
        req=writer_request(state)
        self.assertEqual(req['max_output_tokens'],600)
        for data in [dict(messages=[],evidence_ids=['m1']),dict(messages=['hello'],evidence_ids=[]),
                     dict(messages=['a\nb'],evidence_ids=['m1']),dict(messages=['x'*601],evidence_ids=['m1'])]:
            with self.assertRaises(Rejected):parse_writer(data,state)
        with self.assertRaises(ValueError):ProactiveService(self.store,self.models,self.budget,route='jev_writer',structured_delivery=True)
