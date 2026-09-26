import copy
import json
from pathlib import Path
import unittest
from admission import Rejected
from memory_recording_identity import request,decisions

class RecordingIdentityTests(unittest.TestCase):
    def record(self):return json.loads((Path(__file__).parent/'fixtures/memory_evidence_chunks/recording-identity/result.json').read_text())

    def test_frozen_positive_and_negative_provider_results(self):
        r=self.record();req=request([c['proposal'] for c in r['cases']]);self.assertEqual(req,r['request'])
        result=decisions(r['response']['data'],req)
        for i,c in enumerate(r['cases']):self.assertEqual(result[f'subject_{i}']['accepted'],c['accept'],c['id'])

    def test_owner_scope_is_rejected_before_a_provider_call(self):
        p=self.record()['cases'][0]['proposal'];p['scope']='related_to_author'
        with self.assertRaisesRegex(Rejected,'unsupported_author_identity'):request([p])

    def test_no_invented_evidence_or_missing_verdict(self):
        r=self.record();response=copy.deepcopy(r['response']['data'])
        response['subject_0']['quote']='Maya said something not in this source.'
        with self.assertRaisesRegex(Rejected,'invalid_recording_identity_quote'):decisions(response,r['request'])
        with self.assertRaisesRegex(Rejected,'invalid_recording_identity'):decisions({},r['request'])

    def test_uncertainty_never_establishes_subject(self):
        p=self.record()['cases'][0]['proposal'];req=request([p])
        result=decisions({'subject_0':dict(label='uncertain',quote=None)},req)
        self.assertFalse(result['subject_0']['accepted'])
        self.assertNotIn('probabilities',result['subject_0'])
