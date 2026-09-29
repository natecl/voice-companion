"""Actual contribution-first failures, replayed without network; never grade as accepted."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from openai.types.responses import Response
from companion_chat import CompanionChat
from memory_models import MemoryModels
from memory_store import MemoryStore
from proactive_models import draft_request
from proactive_service import ProactiveService
from test_proactive_personal import RecordedModel, recording
from test_proactive_service import Budget
from test_proactive_conversation import run

FIXTURES=Path(__file__).parent/'fixtures/proactive/contribution-first-evaluation'

class ContributionFirstReplayTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_outputs_and_transport_failure_have_no_live_fallback(self):
        for row in json.loads((FIXTURES/'requests.json').read_text()):
            with self.subTest(case=row['case']):
                saved=json.loads((FIXTURES/(row['case']+'.json')).read_text())
                state=json.loads(row['request']['input'])
                self.assertEqual(row['request'],draft_request(state,structured_delivery=True))
                name=row['case'].removeprefix('contribution-first-')
                if name in ('missing-prerequisite','acknowledged-after-cooldown'):
                    result=await run(dict(case=name,request=row['request'],response=saved),structured_delivery=True)
                    self.assertEqual(result['steps'][-1]['result'],'silence' if name.startswith('acknowledged') else 'contribution')
                    continue
                with tempfile.TemporaryDirectory() as directory:
                    path=Path(directory)/'memory.sqlite';store=MemoryStore(path,clock=lambda:300.)
                    owner=store.owner_for('fictional-contribution-first')
                    for source in state['sources']:store.put_source(owner,recording(source['session_id'],source['text']))
                    live=dict(recording('capture','',completed=False),passages=state['current']['passages'])
                    budget=Budget()
                    if 'error' in saved:
                        # Exercise the actual SDK output_text and MemoryModels parser;
                        # don't cherry-pick the final JSON block or retry the provider.
                        calls=[]
                        class Client:
                            def __init__(inner,**kwargs): inner.responses=inner
                            async def __aenter__(inner):return inner
                            async def __aexit__(inner,*args):pass
                            async def create(inner,**request):
                                self.assertEqual(request,row['request']);calls.append(request)
                                return Response.model_validate(saved['raw'])
                        service=ProactiveService(store,MemoryModels('fixture',''),budget,structured_delivery=True)
                        with patch('openai.AsyncOpenAI',Client):
                            result=await service.evaluate(owner,live,lambda:True)
                        self.assertEqual(result['type'],'unavailable')
                        self.assertEqual(CompanionChat(MemoryStore(path)).page(owner)['turns'],[])
                        self.assertEqual(len(calls),1)
                    else:
                        model=RecordedModel(row['request'],saved)
                        service=ProactiveService(store,model,budget,structured_delivery=True)
                        result=await service.evaluate(owner,live,lambda:True)
                        # This is the observed result, NOT the desired silence rubric.
                        self.assertEqual(result['type'],'contribution')
                        turns=CompanionChat(MemoryStore(path)).page(owner)['turns']
                        self.assertEqual(turns[0]['answer'].split('\n\n'),[m['text'] for m in saved['data']['messages']])
                        self.assertEqual(model.calls,1)
                    self.assertEqual((await service.evaluate(owner,live,lambda:True))['type'],'existing')
                    self.assertEqual(len(budget.attempts),1)

    def test_quality_regressions_remain_visible(self):
        def saved(case):return json.loads((FIXTURES/('contribution-first-'+case+'.json')).read_text())
        cedar=saved('missing-prerequisite')['data']
        self.assertEqual(len(cedar['messages']),1)
        self.assertNotIn('before adding features',cedar['messages'][0]['text'])
        self.assertEqual(saved('tests-completed')['data']['decision'],'contribute')
        self.assertEqual(saved('acknowledged-after-cooldown')['data']['decision'],'silence')
        self.assertEqual(saved('rescheduled-study-session')['error'],'invalid_extraction')
        self.assertFalse(json.loads((FIXTURES/'summary.json').read_text())['selected'])
