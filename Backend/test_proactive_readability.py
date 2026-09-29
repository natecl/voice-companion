"""Recorded readability response through real retrieval/save/reopen, without network."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from companion_chat import CompanionChat
from memory_store import MemoryStore
from proactive_service import ProactiveService
from test_proactive_service import Budget
from test_proactive_personal import RecordedModel, seed_case, recording

class ReadabilityReplayTests(unittest.IsolatedAsyncioTestCase):
    async def test_cedar_response_preserves_full_text_after_reopen(self):
        root=Path(__file__).parent/'fixtures/proactive/readability-evaluation'
        row=json.loads((root/'requests.json').read_text())[0]
        case=json.loads((root/'cases.json').read_text())[0]
        saved=json.loads((root/'cedar-prerequisite.json').read_text())
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'memory.sqlite'
            store=MemoryStore(path,clock=lambda:300.)
            owner=store.owner_for('fictional-personal-evaluation')
            seed_case(store,owner,case)
            model=RecordedModel(row['request'],saved)
            with patch('proactive_models.PROMPT',row['request']['instructions']):
                result=await ProactiveService(store,model,Budget()).evaluate(
                    owner,recording('capture',case['live'],completed=False),lambda:True)
            self.assertEqual(result['type'],'contribution')
            self.assertEqual(model.calls,1)
            turns=CompanionChat(MemoryStore(path)).page(owner)['turns']
            self.assertEqual(len(turns),1)
            self.assertEqual(turns[0]['answer'],saved['data']['text'])
            self.assertIn('before adding features',turns[0]['answer'])
            # This is an observed presentation failure, not proof of grouped output.
            self.assertNotIn('\n\n',turns[0]['answer'])
