"""Recorded six-call screen; mechanics pass, quality failures stay explicit."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from openai.types.responses import Response
from companion_chat import CompanionChat
from memory_models import MemoryModels
from memory_store import MemoryStore
from proactive_models import judge_request, allow_draft
from proactive_service import ProactiveService
from proactive_store import ProactiveStore
from proactive_writer import writer_request, parse_writer
from test_proactive_service import Budget
from test_proactive_personal import recording

ROOT=Path(__file__).parent/'fixtures/proactive/gate-writer-evaluation'

def receipt(name):return json.loads((ROOT/(name+'.json')).read_text())

class Screen(unittest.IsolatedAsyncioTestCase):
    async def test_exact_gate_and_writer_requests_through_storage(self):
        for name in ('missing-prerequisite','acknowledged-after-cooldown','tests-completed','venue-choice'):
            with self.subTest(case=name),tempfile.TemporaryDirectory() as directory:
                saved=receipt('gate-'+name);state=saved['request']['state']
                self.assertEqual(judge_request(state),saved['request'])
                path=Path(directory)/'memory.sqlite';store=MemoryStore(path,clock=lambda:300.)
                owner=store.owner_for('fictional-gate-writer-screen')
                for source in state['sources']:
                    store.put_source(owner,recording(source['session_id'],source['text']))
                live=dict(recording('capture','',completed=False),passages=state['current']['passages'])
                calls=[]
                async def judge(request):
                    self.assertEqual(request,saved['request']);calls.append('judge')
                    return dict(data=saved['raw'],usage=saved['raw']['usage'])
                async def extract(request):
                    row=receipt('writer-'+name)
                    self.assertEqual(request,row['request']);calls.append('writer')
                    return dict(data=row['data'],usage=row['raw']['usage'])
                models=MemoryModels('unused','unused',luna_call=extract,jev_call=judge)
                budget=Budget();service=ProactiveService(store,models,budget,route='jev_writer')
                # Preceding conversation is teacher-forced, not a new closed-loop claim.
                with patch.object(ProactiveStore,'previous',return_value=state['previous']):
                    result=await service.evaluate(owner,live,lambda:True)
                allowed=name=='missing-prerequisite'
                self.assertEqual(result['type'],'contribution' if allowed else 'silence')
                self.assertEqual(calls,['judge','writer'] if allowed else ['judge'])
                turns=CompanionChat(MemoryStore(path)).page(owner)['turns']
                self.assertEqual(len(turns),1 if allowed else 0)
                if allowed:
                    self.assertEqual(turns[0]['answer'].split('\n\n'),receipt('writer-'+name)['data']['messages'])
                self.assertEqual((await service.evaluate(owner,live,lambda:True))['type'],'existing')
                self.assertEqual(len(budget.attempts),len(calls))

    async def test_both_writer_receipts_use_actual_sdk_parser(self):
        for name in ('missing-prerequisite','venue-choice'):
            row=receipt('writer-'+name);state=json.loads(row['request']['input'])
            self.assertEqual(writer_request(state),row['request'])
            calls=[]
            class Client:
                def __init__(inner,**kwargs):inner.responses=inner
                async def __aenter__(inner):return inner
                async def __aexit__(inner,*args):pass
                async def create(inner,**request):
                    self.assertEqual(request,row['request']);calls.append(request)
                    return Response.model_validate(row['raw'])
            with patch('openai.AsyncOpenAI',Client):
                parsed=await MemoryModels('fixture','').extract(row['request'])
            self.assertEqual(parsed['data'],row['data'])
            self.assertEqual(parse_writer(parsed['data'],state)['decision'],'contribute')
            self.assertEqual(len(calls),1)

    def test_quality_failures_not_hidden_by_mechanical_success(self):
        venue=receipt('gate-venue-choice')
        self.assertFalse(allow_draft(venue['raw'],venue['request']))
        self.assertEqual(venue['raw']['answers']['novelty']['probabilities']['new'],.89)
        self.assertEqual([len(receipt('writer-'+name)['data']['messages']) for name in ('missing-prerequisite','venue-choice')],[1,1])
        self.assertNotIn('before adding features',receipt('writer-missing-prerequisite')['data']['messages'][0])
