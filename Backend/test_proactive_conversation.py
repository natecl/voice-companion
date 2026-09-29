"""Runs the multi-step policy/retrieval/durable-chat contract without provider traffic."""
import sys
import json
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/evaluations'))
from proactive_conversation_replay import run

class ConversationReplayTests(unittest.IsolatedAsyncioTestCase):
    async def test_long_conversation_keeps_controls_and_previous_context(self):
        result=await run()
        self.assertEqual(result['saved_messages'],2)
        self.assertEqual(result['model_requests'],5)
        self.assertEqual(result['paid_calls'],0)
        self.assertEqual([step['result'] for step in result['steps']],
            ['contribution','not_scheduled','silence','silence','contribution','silence','not_scheduled'])

    async def test_five_real_decisions_replay_with_exact_predeclared_context(self):
        root=Path(__file__).parent/'fixtures/proactive/conversation-evaluation'
        rows=json.loads((root/'replay.json').read_text())['requests']
        for row in rows:
            with self.subTest(case=row['case']):
                response=json.loads((root/(row['case']+'.json')).read_text())
                self.assertEqual(response['data']['decision'],row['expected_model_decision'])
                # Teacher-forced prefix: earlier messages remain the predeclared synthetic
                # context. Stop after this real response to avoid claiming a closed loop.
                result=await run(dict(case=row['case'],request=row['request'],response=response))
                self.assertEqual(result['steps'][-1]['case'],row['case'])
                self.assertEqual(result['steps'][-1]['result'],
                    'contribution' if row['expected_model_decision']=='contribute' else 'silence')
