import json
from pathlib import Path
import tempfile
import unittest
from admission import Rejected
from memory_candidates import related
from memory_judgments import verify_proposals,pair_questions,decisions
from memory_store import MemoryStore
from test_memory import source,candidate
from test_memory_learning import answers


def proposal():
    return dict(text='Maya now enjoys tennis instead of swimming.',kind='preference',basis='stated',
        mention=dict(name='Maya',relationship='daughter',qualifiers=[],speaker_label=None),scope='related_to_author',
        change=dict(kind='correction',previous_text='Maya enjoys swimming.'),
        time=dict(status='current',expression='now'),evidence=[dict(passage='p1',quote='Maya now enjoys tennis instead of swimming.')])


class CandidateTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.store=MemoryStore(Path(folder.name)/'memory.sqlite');self.owner=self.store.owner_for('one')

    def write(self,index,text,owner=None):
        owner=owner or self.owner
        self.store.put_source(owner,source(str(index),text=text))
        c=candidate(text);c['kind']='preference'
        c['mention']=dict(name='Maya' if 'Maya' in text else None,relationship=None,qualifiers=[],speaker_label=None)
        self.store.commit_claims(self.store.claim_job(owner),[c])

    def test_older_target_survives_fifty_one_unrelated_new_claims(self):
        self.write('old','Maya enjoys swimming.')
        for i in range(51):self.write(i,f'Household item {i} is in the cupboard.')
        result=related(self.store,self.owner,proposal())
        self.assertEqual(result['matched_count'],1)
        old=result['candidates'][0]
        self.assertEqual(old['text'],'Maya enjoys swimming.')
        self.assertEqual(old['evidence'][0]['passage']['text'],old['text'])
        self.assertFalse(result['semantic_complete'])

    def test_other_owner_and_deleted_evidence_are_excluded(self):
        self.write('own','Maya enjoys swimming.')
        self.write('foreign','Maya enjoys tennis.',self.store.owner_for('two'))
        self.assertEqual(related(self.store,self.owner,proposal())['matched_count'],1)
        self.store.delete_source(self.owner,'own')
        self.assertEqual(related(self.store,self.owner,proposal())['candidates'],[])

    def test_limit_reports_omissions_and_does_not_establish_identity(self):
        for i in range(5):self.write(i,f'Maya enjoys swimming activity {i}.')
        result=related(self.store,self.owner,proposal(),limit=2)
        self.assertTrue(result['truncated']);self.assertEqual(result['matched_count'],5)
        self.assertTrue(all(c['identity_status']=='unresolved' for c in result['candidates']))


class JudgmentTests(unittest.TestCase):
    def test_separate_source_aspects_and_role_thresholds(self):
        request=verify_proposals(source(),[proposal()])
        self.assertEqual(set(request['questions']),{'support_0','subject_0','modality_0','time_0'})
        data=answers(request,{key:'supported' for key in request['questions']})
        result=decisions(data,request)
        self.assertTrue(all(x['accepted'] for x in result.values()))
        for key in request['questions']:
            self.assertIn('independently',request['questions'][key]['instructions']['rule'])
        data['answers']['subject_0'].update(choice='supported',probabilities={'supported':.92,'unsupported':.04,'uncertain':.04},confidence=1.)
        self.assertFalse(decisions(data,request)['subject_0']['accepted'])

    def test_pair_keys_are_in_instructions_and_roles_do_not_share_answers(self):
        pair=dict(incoming=proposal(),previous=dict(text='Maya enjoys swimming.'))
        for role in ('identity','relation'):
            request=pair_questions({'old_target':pair},role=role)
            self.assertIn('old_target',request['questions']['old_target']['instructions'])
            data=answers(request,{'old_target':'uncertain'})
            self.assertFalse(decisions(data,request,role)['old_target']['accepted'])

    def test_oversized_evidence_rejected_without_truncation(self):
        with self.assertRaisesRegex(Rejected,'memory_judgment_too_large'):
            verify_proposals(source(text='x'*29000),[proposal()])

    def test_recorded_live_judgments_meet_frozen_positive_and_negative_gates(self):
        from evaluate_memory_judgments import check
        directory=Path(__file__).parent/'fixtures/memory_judgments/recorded'
        for name in ['source-subject','unknown-owner','identity','lifecycle']:
            record=json.loads((directory/(name+'.json')).read_text())
            case=record['case']
            self.assertTrue(all(check(case,decisions(record['response']['data'],case['request'],case['role'])).values()),name)
