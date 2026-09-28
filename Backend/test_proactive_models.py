import json
from pathlib import Path
import tempfile
import unittest
from admission import Rejected
from memory_store import MemoryStore
from memory_models import JEV
from test_memory import source, candidate
from proactive_context import prepare
from proactive_models import draft_request,parse_draft,judge_request,allow_draft


class ProactiveModelsTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.store=MemoryStore(Path(folder.name)/'memory.sqlite',clock=lambda:300.)
        self.owner=self.store.owner_for('fixture-owner')
        self.store.put_source(self.owner,source('past',text='Alex wakes at three every morning.'))
        self.live=dict(source('now',text='We are discussing Alex waking at three and sleep.'),completed=False)
        self.context=prepare(self.store,self.owner,self.live)
        self.state=self.context['state']

    def test_local_discovery_preserves_subject_and_excludes_live(self):
        self.assertEqual(self.state['sources'][0]['text'],'Alex wakes at three every morning.')
        self.assertTrue(all(s['session_id'] != 'now' for s in self.state['sources']))
        self.assertEqual(self.state['current']['speaker_identity'],'unidentified_recording_speakers')
        self.assertIsNone(prepare(self.store,self.store.owner_for('other'),self.live))

    def test_output_must_be_supported_ids_or_empty_silence(self):
        valid=dict(decision='contribute',text='An earlier note mentions Alex waking at three.',evidence_ids=['m1'])
        self.assertEqual(parse_draft(valid,self.state),valid)
        self.assertEqual(parse_draft(dict(decision='silence',text='',evidence_ids=[]),self.state)['decision'],'silence')
        for bad in [dict(valid,evidence_ids=['m99']),dict(valid,evidence_ids=[]),dict(valid,text='[[m1]]'),dict(valid,decision='silence'),dict(valid,text='x'*601)]:
            with self.assertRaises(Rejected):parse_draft(bad,self.state)

    def test_one_batched_gate_uncertain_stays_silent(self):
        req=judge_request(self.state)
        response=dict(model=JEV,answers={k:dict(type='choice',choice=v,confidence=.9,
            probabilities={name:float(name==v) for name in req['questions'][k]['criteria']})
            for k,v in [('connection','useful'),('novelty','new')]})
        self.assertTrue(allow_draft(response,req))
        response['answers']['novelty']['confidence']=.2
        self.assertFalse(allow_draft(response,req))
        response['answers']['novelty']['probabilities']={}
        with self.assertRaises(Rejected):allow_draft(response,req)

    def test_explicit_silence_schema_and_bounded_payload(self):
        req=draft_request(self.state)
        self.assertEqual(req['tools'],[]);self.assertFalse(req['store'])
        self.assertIn('silence',req['text']['format']['schema']['properties']['decision']['enum'])
        with self.assertRaises(Rejected):draft_request(dict(self.state,previous=['x'*12001]))

    def test_known_corrections_travel_with_old_evidence(self):
        self.store.commit_claims(self.store.claim_job(self.owner),[candidate('Alex wakes at three.')])
        old=self.store.search(self.owner)[0]['id']
        self.store.put_source(self.owner,source('correction',text='Alex now sleeps through the night instead.'))
        self.store.commit_claims(self.store.claim_job(self.owner),[candidate('Alex sleeps through the night.',relation='supersedes',target=old)])
        state=prepare(self.store,self.owner,self.live)['state']
        self.assertIn('correction',{s['session_id'] for s in state['sources']})

    def test_frozen_cases_have_expected_outcomes_not_sent_to_model(self):
        cases=json.loads((Path(__file__).parent/'fixtures/proactive/cases.json').read_text())
        self.assertEqual(len(cases),7)
        for case in cases:
            req=draft_request(dict(current=case['live'],sources=[dict(id='m1',text=case['past'])],previous=[]))
            self.assertNotIn('rubric',json.loads(req['input']))
            self.assertNotIn('expected',json.loads(req['input']))
