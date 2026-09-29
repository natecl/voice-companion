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

    async def test_grouped_live_candidates_replay_without_claiming_style_acceptance(self):
        root=Path(__file__).parent/'fixtures/proactive/conversational-evaluation'
        for row in json.loads((root/'requests.json').read_text()):
            with self.subTest(case=row['case']):
                response=json.loads((root/(row['case']+'.json')).read_text())
                result=await run(dict(case=row['case'],request=row['request'],response=response),grouped_messages=True)
                self.assertEqual(result['steps'][-1]['result'],
                    'silence' if row['case']=='acknowledged-after-cooldown' else 'contribution')
        # Keep the observed failure visible; two bubbles alone is not the desired tone.
        cedar=json.loads((root/'missing-prerequisite.json').read_text())['data']['messages']
        self.assertEqual(len(cedar),2)
        self.assertIn(';',cedar[0])
        self.assertIn('as of the note',cedar[0])

    async def test_v6_exact_live_responses_preserve_three_messages_and_silence(self):
        from unittest.mock import patch
        from proactive_models import draft_request
        root=Path(__file__).parent/'fixtures/proactive/conversational-v6-evaluation'
        prompt=(Path(__file__).parent/'prompts/proactive-v6-candidate.md').read_text()
        def candidate_request(state, *, grouped_messages=False):
            return dict(draft_request(state,grouped_messages=grouped_messages),instructions=prompt)
        for row in json.loads((root/'requests.json').read_text()):
            with self.subTest(case=row['case']):
                response=json.loads((root/(row['case']+'.json')).read_text())
                with patch('proactive_service.draft_request',candidate_request):
                    result=await run(dict(case=row['case'],request=row['request'],response=response),grouped_messages=True)
                self.assertEqual(result['steps'][-1]['result'],
                    'silence' if row['case']=='acknowledged-after-cooldown' else 'contribution')
        cedar=json.loads((root/'missing-prerequisite.json').read_text())['data']['messages']
        self.assertEqual(len(cedar),3)
        self.assertIn('five people before adding features',cedar[0])
        self.assertIn('had not happened',cedar[1])
        self.assertIn('Calendar integration',cedar[2])
        # Do not erase the residual style miss from the acceptance evidence.
        self.assertIn('as of the note',cedar[1])
