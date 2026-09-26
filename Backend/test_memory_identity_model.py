import json
import unittest
from pathlib import Path
from admission import Rejected
from memory_identity_model import evidence_request,decisions

class IdentityModelTests(unittest.TestCase):
    def request(self):
        return evidence_request({'pair':dict(incoming=dict(claim='My other sister Bea likes tennis.',excerpts=['My other sister Bea likes tennis.']),
            previous=dict(claim='My sister Bea likes swimming.',evidence=[dict(text='My sister Bea likes swimming.')]))})

    def test_no_invented_quote_can_authorize_identity(self):
        req=self.request()
        with self.assertRaisesRegex(Rejected,'invalid_identity_quote'):
            decisions({'pair':dict(label='same',incoming_quote='They are the same person.',previous_quote='My sister Bea')},req)

    def test_missing_answer_or_confidence_field_is_rejected(self):
        with self.assertRaisesRegex(Rejected,'invalid_identity_decision'):decisions({},self.request())
        with self.assertRaisesRegex(Rejected,'invalid_identity_decision'):
            decisions({'pair':dict(label='same',confidence=1.,incoming_quote='Bea',previous_quote='Bea')},self.request())

    def test_uncertainty_is_not_an_accepted_match(self):
        result=decisions({'pair':dict(label='uncertain',incoming_quote=None,previous_quote=None)},self.request())
        self.assertFalse(result['pair']['accepted'])
        self.assertNotIn('probabilities',result['pair'])

    def test_historical_v1_payload_remains_parseable(self):
        record=json.loads((Path(__file__).parent/'fixtures/memory_identity_model/recorded.json').read_text())
        self.assertEqual(record['request']['model'],'gpt-6-luna') # Historical v1 request; the role-overlap oracle is superseded in v2.
        results=decisions(record['response']['data'],record['request'])
        self.assertEqual(set(results),set(record['cases']['expected']))

    def test_missing_subject_target_is_rejected_before_inference(self):
        root=Path(__file__).parent/'fixtures/memory_identity_model/low/result.json'
        record=json.loads(root.read_text())
        for key in ['quoted_subject','unspecified_target']:
            with self.assertRaisesRegex(Rejected,'memory_identity_missing_target'):
                evidence_request({key:record['cases']['pairs'][key]})

    def test_final_identity_contract(self):
        record=json.loads((Path(__file__).parent/'fixtures/memory_identity_model/targeted/result.json').read_text())
        self.assertEqual(evidence_request(record['cases']['pairs']),record['request'])
        results=decisions(record['response']['data'],record['request'])
        for key,label in record['cases']['expected'].items():
            if label=='no_same':self.assertNotEqual(results[key]['label'],'same',key)
            else:self.assertEqual(results[key]['label'],label,key)

    def test_large_candidate_set_splits_without_truncating_evidence(self):
        from memory_writer import bounded_batches
        pair=json.loads(self.request()['input'])['pair']
        pair['incoming']['excerpts']=['x'*1500]
        entries=[(f'pair_{i}',pair) for i in range(20)]
        batches=bounded_batches(entries,lambda a,b:evidence_request(dict(entries[a:b])), 'memory_identity_too_large')
        self.assertGreater(len(batches),1)
        self.assertEqual(sum(end-start for start,end,_ in batches),20)
        self.assertEqual([k for _,_,r in batches for k in json.loads(r['input'])],[k for k,_ in entries])
