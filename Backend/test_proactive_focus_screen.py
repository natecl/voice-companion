"""Exact current-focus candidate receipts through SDK parsing, retrieval and durable delivery."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from openai.types.responses import Response
from companion_chat import CompanionChat
from memory_models import MemoryModels
from memory_store import MemoryStore
from proactive_service import ProactiveService
from test_proactive_service import Budget
from test_proactive_personal import recording

ROOT=Path(__file__).parent/'fixtures/proactive/focus-evaluation'

class FocusScreen(unittest.IsolatedAsyncioTestCase):
    async def test_actual_outputs_replay_without_network(self):
        for row in json.loads((ROOT/'requests.json').read_text()):
            with self.subTest(case=row['case']),tempfile.TemporaryDirectory() as directory:
                receipt=json.loads((ROOT/(row['case']+'.json')).read_text())
                state=json.loads(row['request']['input'])
                self.assertEqual(row['request']['instructions'],(Path(__file__).parent/'prompts/proactive-current-focus-candidate.md').read_text())
                path=Path(directory)/'memory.sqlite';store=MemoryStore(path,clock=lambda:300.)
                owner=store.owner_for('fictional-usefulness-replay')
                for source in state['sources']:store.put_source(owner,recording(source['session_id'],source['text']))
                live=dict(recording('capture','',completed=False),passages=state['current']['passages'])
                calls=[]
                class Client:
                    def __init__(inner,**kwargs):inner.responses=inner
                    async def __aenter__(inner):return inner
                    async def __aexit__(inner,*args):pass
                    async def create(inner,**request):
                        self.assertEqual(request,row['request']);calls.append(request)
                        return Response.model_validate(receipt['raw'])
                budget=Budget();service=ProactiveService(store,MemoryModels('fixture',''),budget)
                with patch('openai.AsyncOpenAI',Client), patch('proactive_models.PROMPT', row['request']['instructions']):
                    result=await service.evaluate(owner,live,lambda:True)
                    self.assertEqual(result['type'],receipt['observed_result'])
                    self.assertEqual((await service.evaluate(owner,live,lambda:True))['type'],'existing')
                self.assertEqual(len(calls),1);self.assertEqual(len(budget.attempts),1)
                turns=CompanionChat(MemoryStore(path)).page(owner)['turns']
                if result['type']=='contribution':self.assertEqual([t['answer'] for t in turns],[receipt['data']['text']])
                else:self.assertEqual(turns,[])

    def test_original_failure_remains_explicit(self):
        saved=json.loads((ROOT/'club-topic-only.json').read_text())
        current=json.loads(saved['request']['input'])['current']['passages'][0]['text']
        self.assertIn('Orion',current)
        self.assertEqual(saved['data']['decision'],'contribute')
        self.assertIn('$80',saved['data']['text'])
        self.assertFalse(json.loads((ROOT/'summary.json').read_text())['original_bug_fixed'])
