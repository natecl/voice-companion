import json
import unittest
from admission import Rejected
import memory_evidence as evidence
from test_memory import source


def candidate():
    return dict(text='Maya enjoys swimming.',kind='preference',basis='stated',
        mention=dict(name='Maya',relationship='daughter',qualifiers=['other'],speaker_label=0),scope='named',
        evidence=[dict(passage='p1',quote='My other daughter Maya enjoys swimming today.')],
        time=dict(status='current',expression='today'),change=dict(kind='none',previous_text=None))


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.source=source(text='My other daughter Maya enjoys swimming today.')
        self.source['passages'][0]['speakers']=[0]

    def parse(self,c):return evidence.parse(dict(memories=[c]),self.source)

    def test_exact_unicode_source_spans_and_descriptors(self):
        self.source['passages'][0]['text']='🎧 '+self.source['passages'][0]['text']
        result=self.parse(candidate())[0]
        span=result['spans'][0]
        self.assertEqual(span['start'],2)
        self.assertEqual(self.source['passages'][0]['text'][span['start']:span['end']],candidate()['evidence'][0]['quote'])
        self.assertEqual(result['mention']['qualifiers'],['other'])
        self.assertEqual(result['contract'],evidence.VERSION)

    def test_recording_never_establishes_account_owner(self):
        for scope in ['author','related_to_author']:
            c=candidate();c['scope']=scope
            with self.assertRaisesRegex(Rejected,'unsupported_author_identity'):self.parse(c)

    def test_personal_authorship_does_not_require_a_name(self):
        self.source['origin']='personal_text'
        c=candidate();c.update(scope='author',mention=dict(name=None,relationship=None,qualifiers=[],speaker_label=None))
        self.assertEqual(self.parse(c)[0]['scope'],'author') # Semantic entailment is independently verified later.

    def test_nonexistent_fabricated_ambiguous_and_foreign_refs_rejected(self):
        for ref in [dict(passage='missing',quote='today'),dict(passage='p1',quote='tomorrow'),dict(passage=[],quote='today')]:
            c=candidate();c['evidence']=[ref]
            with self.assertRaises(Rejected):self.parse(c)
        self.source['passages'][0]['text']+=' today'
        c=candidate();c['evidence']=[dict(passage='p1',quote='today')]
        with self.assertRaisesRegex(Rejected,'invalid_evidence_quote'):self.parse(c)

    def test_qualifiers_and_time_must_be_in_cited_evidence(self):
        c=candidate();c['mention']['qualifiers']=['older']
        with self.assertRaisesRegex(Rejected,'unsupported_qualifier'):self.parse(c)
        c=candidate();c['time']['expression']='tomorrow'
        with self.assertRaisesRegex(Rejected,'unsupported_time_expression'):self.parse(c)

    def test_ambiguous_speaker_is_not_assigned(self):
        self.source['passages'][0]['speakers']=[0,1]
        with self.assertRaisesRegex(Rejected,'invalid_mention_speaker'):self.parse(candidate())
        c=candidate();c['mention']['speaker_label']=None
        self.assertIsNone(self.parse(c)[0]['mention']['speaker_label'])

    def test_malformed_contracts_and_extra_fields_rejected(self):
        for field,value in [('basis','inferred'),('mention',None),('time',{}),('change',{}),('evidence',[]),('text','')]:
            c=candidate();c[field]=value
            with self.assertRaises(Rejected):self.parse(c)
        c=candidate();c['claim_id']='untrusted'
        with self.assertRaises(Rejected):self.parse(c)
        with self.assertRaises(Rejected):evidence.parse(dict(memories=[candidate()]*9),self.source)

    def test_strict_request_no_tools_and_no_silent_truncation(self):
        request=evidence.extraction_request(self.source)
        self.assertEqual(request['tools'],[])
        self.assertFalse(request['store'])
        self.assertEqual(request['truncation'],'disabled')
        self.assertTrue(request['text']['format']['strict'])
        with self.assertRaisesRegex(Rejected,'memory_extraction_too_large'):
            evidence.extraction_request(source(text='long '*5000))

    def test_old_contract_is_unchanged(self):
        from memory_models import extraction_request
        old=extraction_request(self.source)
        self.assertNotIn('mention',old['text']['format']['schema']['properties']['memories']['items']['properties'])

    def test_recorded_luna_scope_failure_cannot_become_user_fact(self):
        from pathlib import Path
        record=json.loads((Path(__file__).parent/'fixtures/memory_evidence/failed/ambiguous-scope.json').read_text())
        with self.assertRaisesRegex(Rejected,'invalid_evidence_extraction'):
            evidence.parse(record['response']['data'],record['source'])

    def test_recorded_final_contract_meets_source_metadata_gate(self):
        from pathlib import Path
        from evaluate_memory_evidence import checks
        directory=Path(__file__).parent/'fixtures/memory_evidence'
        for case in json.loads((directory/'cases.json').read_text()):
            with self.subTest(case=case['id']):
                record=json.loads((directory/'recorded'/(case['id']+'.json')).read_text())
                candidates=evidence.parse(record['response']['data'],record['source'])
                self.assertTrue(checks(case,candidates))
