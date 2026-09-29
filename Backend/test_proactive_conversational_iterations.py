"""Exact live wording evidence: preserve failures; no provider traffic or tone-pass claim."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from companion_chat import CompanionChat
from memory_store import MemoryStore
from proactive_models import draft_request, parse_draft
from proactive_service import ProactiveService
from test_proactive_service import Budget
from test_proactive_personal import RecordedModel, recording
from test_proactive_conversation import run

ROOT = Path(__file__).parent
FIXTURES = ROOT / 'fixtures/proactive/conversational-iteration-evaluation'

class ConversationalIterationTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_responses_replay_exactly_and_reopen_without_network(self):
        for row in json.loads((FIXTURES / 'requests.json').read_text()):
            with self.subTest(case=row['case']):
                saved = json.loads((FIXTURES / (row['case'] + '.json')).read_text())
                state = json.loads(row['request']['input'])
                parsed = parse_draft(saved['data'], state, grouped_messages=True)
                self.assertEqual(parsed['decision'], row['expected'])
                prompt = (ROOT / f"prompts/proactive-v{row['version']}-candidate.md").read_text()
                self.assertEqual(row['request']['instructions'], prompt)
                def candidate_request(state, *, grouped_messages=False):
                    return dict(draft_request(state, grouped_messages=grouped_messages), instructions=prompt)
                with patch('proactive_service.draft_request', candidate_request):
                    if row['scenario'] != 'rescheduled-study-session':
                        result = await run(dict(case=row['scenario'], request=row['request'], response=saved),
                                           grouped_messages=True)
                        self.assertEqual(result['steps'][-1]['result'],
                                         'silence' if row['expected']=='silence' else 'contribution')
                    else:
                        with tempfile.TemporaryDirectory() as directory:
                            path = Path(directory) / 'memory.sqlite'
                            store = MemoryStore(path, clock=lambda:300.)
                            owner = store.owner_for('fictional-wording-screen')
                            source = state['sources'][0]
                            store.put_source(owner, recording(source['session_id'], source['text']))
                            live = dict(recording('capture', '', completed=False),
                                        passages=state['current']['passages'])
                            model = RecordedModel(row['request'], saved)
                            service = ProactiveService(store, model, Budget(), grouped_messages=True)
                            result = await service.evaluate(owner, live, lambda:True)
                            self.assertEqual(result['type'], 'contribution')
                            turns = CompanionChat(MemoryStore(path)).page(owner)['turns']
                            self.assertEqual([t['answer'] for t in turns], [parsed['text']])
                            self.assertEqual(turns[0]['answer'].split('\n\n'), saved['data']['messages'])
                            self.assertEqual((await service.evaluate(owner,live,lambda:True))['type'],'existing')
                            self.assertEqual(model.calls,1)

    def test_style_failure_is_not_relabelled_as_success(self):
        final = json.loads((FIXTURES/'v10-missing-prerequisite.json').read_text())['data']['messages']
        self.assertGreater(len(final[1]), 110)
        self.assertIn('and those tests', final[1])
        self.assertNotIn('before adding features', ' '.join(final))
        summary = json.loads((FIXTURES/'summary.json').read_text())
        self.assertEqual(summary['calls'],10)
        self.assertFalse(summary['selected'])
