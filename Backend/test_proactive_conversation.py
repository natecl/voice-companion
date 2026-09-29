"""Runs the multi-step policy/retrieval/durable-chat contract without provider traffic."""
import sys
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
