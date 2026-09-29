"""Candidate contract checks and synthetic end-to-end delivery; no model-quality claim."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from admission import Rejected
from companion_chat import CompanionChat
from memory_store import MemoryStore
from proactive_models import draft_request, parse_draft
from proactive_service import ProactiveService
from test_proactive_service import Budget
from test_proactive_personal import recording

ROOT = Path(__file__).parent
PAST = ('For the Cedar pilot, the team agreed to test the basic recording flow with five people before adding features. '
        'Those tests had not happened as of this note. Calendar integration should wait until afterward.')
FACTS = [dict(evidence_id='m1', quote=quote) for quote in [
    'the team agreed to test the basic recording flow with five people before adding features.',
    'Those tests had not happened as of this note.',
    'Calendar integration should wait until afterward.']]
# Handwritten fixture, intentionally not described as model output.
DATA = dict(decision='contribute', facts=FACTS, messages=[
    dict(fact_index=2, text="I'd hold off on calendar integration until after those tests."),
    dict(fact_index=0, text='The team agreed to test the basic recording flow with five people before adding features.'),
    dict(fact_index=1, text="Those tests hadn't happened when that was recorded.")])

class DeliveryContractTests(unittest.TestCase):
    def setUp(self):
        self.state=dict(current={}, sources=[dict(id='m1',text=PAST)], previous=[])
    def parse(self, data):
        return parse_draft(data,self.state,structured_delivery=True)

    def test_one_call_contract_and_lossless_message_order(self):
        request=draft_request(self.state,structured_delivery=True)
        self.assertEqual(request['model'],'gpt-6-luna')
        self.assertEqual(request['max_output_tokens'],600)
        self.assertEqual(request['tools'],[])
        self.assertEqual(list(request['text']['format']['schema']['properties']),['decision','facts','messages'])
        normalized=self.parse(DATA)
        self.assertEqual(normalized['text'].split('\n\n'),[m['text'] for m in DATA['messages']])
        self.assertEqual(normalized['evidence_ids'],['m1'])
        self.assertNotIn('facts',normalized)
        self.assertEqual(self.parse(dict(decision='silence',facts=[],messages=[]))['text'],'')
        with self.assertRaises(ValueError):draft_request(self.state,grouped_messages=True,structured_delivery=True)

    def test_invalid_grounding_coverage_and_message_boundaries_are_rejected(self):
        mutations=[
            lambda d:d['facts'][0].update(evidence_id='m99'),
            lambda d:d['facts'][0].update(quote='An invented agreement.'),
            lambda d:d['facts'][0].update(quote=' '),
            lambda d:d['facts'].append(copy.deepcopy(d['facts'][0])),
            lambda d:d['messages'].pop(),
            lambda d:d['messages'][1].update(fact_index=2),
            lambda d:d['messages'][0].update(fact_index=-1),
            lambda d:d['messages'][0].update(fact_index=True),
            lambda d:d['messages'][0].update(fact_index=3),
            lambda d:d['messages'][0].update(fact_index=[0,1]),
            lambda d:d['messages'][0].update(text='one\n\ntwo'),
            lambda d:d['messages'][0].update(text='x'*601),
            lambda d:d['messages'][0].update(text='[[m1]]'),
            lambda d:d['messages'][0].update(text=''),
            lambda d:d.update(decision='silence'),
            lambda d:d.update(facts=[]),
            lambda d:d.update(extra='unexpected'),
        ]
        for mutate in mutations:
            data=copy.deepcopy(DATA);mutate(data)
            with self.subTest(data=data),self.assertRaises(Rejected):self.parse(data)

    def test_one_optional_suggestion_and_multiple_sources(self):
        data=copy.deepcopy(DATA)
        data['messages'].insert(0,dict(fact_index=None,text='Could that be the next step?'))
        self.assertEqual(len(self.parse(data)['text'].split('\n\n')),4)
        data['messages'].insert(0,dict(fact_index=None,text='Another suggestion.'))
        with self.assertRaises(Rejected):self.parse(data)
        self.state['sources'].append(dict(id='m2',text='Calendar integration should wait until afterward.'))
        data=copy.deepcopy(DATA);data['facts'][2]['evidence_id']='m2'
        self.assertEqual(self.parse(data)['evidence_ids'],['m1','m2'])

    def test_coverage_is_not_a_semantic_correctness_claim(self):
        data=copy.deepcopy(DATA)
        data['messages'][1]['text']='The team agreed to test with six people.'
        # Literal quote/index validity does not prove paraphrase entailment.
        self.assertIn('six people',self.parse(data)['text'])

class DeliveryServiceTests(unittest.IsolatedAsyncioTestCase):
    async def test_synthetic_delivery_reopen_duplicate_and_rejection_without_retry(self):
        for invalid in (False, True):
            with self.subTest(invalid=invalid),tempfile.TemporaryDirectory() as directory:
                path=Path(directory)/'memory.sqlite';store=MemoryStore(path,clock=lambda:300.)
                owner=store.owner_for('fictional-structured-delivery')
                store.put_source(owner,recording('cedar',PAST))
                live=recording('capture','Should we add calendar integration to the Cedar pilot now?',completed=False)
                data=copy.deepcopy(DATA)
                if invalid:data['messages'].pop()
                calls=[]
                class FixtureModel:
                    async def extract(inner,request):
                        calls.append(request)
                        self.assertEqual(request['text']['format']['name'],'proactive_delivery_v1')
                        return dict(data=data,usage={})
                budget=Budget()
                service=ProactiveService(store,FixtureModel(),budget,structured_delivery=True)
                result=await service.evaluate(owner,live,lambda:True)
                self.assertEqual(result['type'],'unavailable' if invalid else 'contribution')
                turns=CompanionChat(MemoryStore(path)).page(owner)['turns']
                self.assertEqual(len(turns),0 if invalid else 1)
                if not invalid:
                    self.assertEqual(turns[0]['answer'].split('\n\n'),[m['text'] for m in data['messages']])
                    self.assertNotIn('facts',turns[0]['answer'])
                    store.delete_source(owner,'cedar')
                    self.assertEqual(CompanionChat(store).page(owner)['turns'][0]['answer'],result['text'])
                self.assertEqual((await service.evaluate(owner,live,lambda:True))['type'],'existing')
                self.assertEqual(len(calls),1);self.assertEqual(len(budget.attempts),1)
