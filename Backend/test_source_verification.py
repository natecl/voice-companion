"""Offline candidate integration; constructed verifier responses are not live QA."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from admission import Rejected
import memory_source_verification as verifier
from memory_evidence_writer import EvidenceWriter
from memory_store import MemoryStore
from evaluate_independent_support import screen_cases, build
from test_memory_learning import answers

ROOT = Path(__file__).parent / 'fixtures'


class ContractTests(unittest.TestCase):
    def test_support_contract_matches_prior_paid_screen(self):
        cases, expected = screen_cases()
        request, bound = verifier.support_request(cases)
        self.assertEqual(request, build(cases)[0])
        self.assertLessEqual(bound, verifier.RESERVATION)
        saved = json.loads((ROOT/'independent-support/sol-screen.json').read_text())
        parsed = verifier.parse_support(saved['response']['data'], cases)
        self.assertEqual(len(parsed), 17)
        for key, value in parsed.items():
            self.assertEqual(value['verdict']=='supported', expected[key]=='supported')

    def test_citations_must_match_persisted_proposal_evidence(self):
        source = dict(passages=[dict(id='p1',text='Maya.',speakers=[]),
                                dict(id='p2',text='Enjoys swimming.',speakers=[])])
        proposal = dict(text='Maya enjoys swimming.',evidence=[dict(passage='p1',quote='Maya.')])
        data = dict(case_0=dict(verdict='supported',passages=['p1','p2']))
        self.assertFalse(verifier.support_decisions(data,source,[proposal])['support_0']['accepted'])
        data['case_0']['passages']=['invented']
        with self.assertRaisesRegex(Rejected,'citations'):
            verifier.support_decisions(data,source,[proposal])
        data['case_0']=dict(verdict='supported',passages=[])
        with self.assertRaisesRegex(Rejected,'citations'):
            verifier.support_decisions(data,source,[proposal])

    def test_metadata_retains_thresholds_and_checks_expression(self):
        row=json.loads((ROOT/'atomic-preference/atomic-v1.json').read_text())[0]
        source,proposals=row['case']['source'],row['case']['proposals']
        request=verifier.metadata_request(source,proposals)
        self.assertFalse(any(key.startswith('support_') for key in request['questions']))
        for key,value in request['questions'].items():
            self.assertEqual(value,row['request']['questions'][key])
        data=copy.deepcopy(row['response']['data'])
        data['answers']={k:v for k,v in data['answers'].items() if k in request['questions']}
        decisions=verifier.metadata_decisions(data,request,proposals)
        self.assertTrue(all(d['accepted'] for d in decisions.values()))
        value=data['answers']['modality_0']
        value['probabilities']={k:(.89 if k=='stated' else .11 if k=='tentative' else 0.) for k in value['probabilities']}
        self.assertFalse(verifier.metadata_decisions(data,request,proposals)['modality_0']['accepted'])
        proposals=copy.deepcopy(proposals[:1]);proposals[0]['time']['expression']='morning'
        request=verifier.metadata_request(source,proposals)
        data=answers(request,dict(modality_0='stated',time_0='current',expression_0='unsupported'))
        self.assertFalse(verifier.metadata_decisions(data,request,proposals)['time_0']['accepted'])


class WriterTests(unittest.IsolatedAsyncioTestCase):
    async def run_candidate(self, verdict='supported', delete_during_verification=False):
        recorded=json.loads((ROOT/'subject-continuity/calls.json').read_text())
        source=json.loads(recorded[0]['request']['input']);source.pop('origin',None)
        outer=self
        class Models:
            async def extract(self,request):
                name=request['text']['format']['name']
                if name=='memory_evidence_v2':
                    outer.assertEqual(request,recorded[0]['request'])
                    return copy.deepcopy(recorded[0]['response'])
                if name=='recording_identity':
                    outer.assertEqual(request,recorded[2]['request'])
                    return copy.deepcopy(recorded[2]['response'])
                if name=='identity_resolution':
                    pairs=json.loads(request['input'])
                    return dict(data={k:dict(label='same',incoming_quote=p['incoming']['excerpts'][0],
                        previous_quote=p['previous']['evidence'][0]['text']) for k,p in pairs.items()},usage={})
                outer.assertEqual(name,'independent_support_screen')
                cases=json.loads(request['input'])
                # Deliberate injected outcomes test application behavior, not model accuracy.
                return dict(data={k:dict(verdict=verdict,passages=['p1','p2'] if k=='case_0' else ['p1','p3']) for k in cases},usage={})
            async def judge(self,request):
                labels={k:('addition' if 'addition' in q['criteria'] else 'stated' if k.startswith('modality_') else 'current')
                    for k,q in request['questions'].items()}
                if delete_during_verification:store.delete_source(owner,source['session_id'])
                return dict(data=answers(request,labels),usage={})
        class Budget:
            def reserve(self,*args):pass
            def finish(self,*args):pass
        with tempfile.TemporaryDirectory() as folder:
            store=MemoryStore(Path(folder)/'memory.sqlite');owner=store.owner_for('test')
            store.put_source(owner,source)
            writer=EvidenceWriter(store,Models(),Budget(),independent_source_verification=True)
            if delete_during_verification:
                with self.assertRaisesRegex(Rejected,'stale_job'):
                    await writer.process_next(owner)
                self.assertEqual(store.search(owner,historical=True),[])
                return
            await writer.process_next(owner)
            rows=store.search(owner,historical=True)
            self.assertEqual(len(rows),2 if verdict=='supported' else 0)
            if verdict=='supported':
                self.assertTrue(any('morning' in r['text'] for r in rows))
                self.assertTrue(all(r['state']=='active' for r in rows))
                with store.connect() as db:
                    self.assertFalse(any(r[0] for r in db.execute('SELECT profile_link FROM claim')))
                reopened=MemoryStore(Path(folder)/'memory.sqlite')
                self.assertEqual(len(reopened.search(owner,historical=True)),2)
    async def test_supported_fact_commits_and_survives_reopen(self):
        await self.run_candidate()
    async def test_contradicted_fact_cannot_commit(self):
        await self.run_candidate('contradicted')
    async def test_uncertain_fact_cannot_commit(self):
        await self.run_candidate('uncertain')
    async def test_deleted_source_cannot_be_learned_later(self):
        await self.run_candidate(delete_during_verification=True)

    async def test_resumed_chunk_cannot_silently_reuse_old_verifier(self):
        import memory_evidence_chunks
        recorded=json.loads((ROOT/'subject-continuity/calls.json').read_text())
        source=json.loads(recorded[0]['request']['input']);source.pop('origin',None)
        source['passages'] += [dict(id=f'extra_{i}',start=float(20+i),duration=1.,speakers=[],
            text='We discussed the order of items. '*20) for i in range(24)]
        class NoCalls:
            async def extract(self,request):raise AssertionError('Unexpected paid extraction')
            async def judge(self,request):raise AssertionError('Unexpected paid judgment')
        with tempfile.TemporaryDirectory() as folder:
            store=MemoryStore(Path(folder)/'memory.sqlite');owner=store.owner_for('test')
            store.put_source(owner,source);job=store.claim_job(owner)
            chunks=store.chunk_plan(job,planner=memory_evidence_chunks)
            # Persist the previous contract's completed evidence, then simulate interruption.
            store.complete_chunk(job,chunks[0]['id'],[dict(proposal=recorded[0]['response']['data']['memories'][0],
                checks=dict(support=dict(label='supported',accepted=False,rubric='evidence-judgments-v17')))])
            store.finish_failed(job,'learning_interrupted');store.resume_chunk_job(owner,job['id'])
            writer=EvidenceWriter(store,NoCalls(),None,chunking=True,independent_source_verification=True)
            with self.assertRaisesRegex(Rejected,'verification_contract_changed'):
                await writer.process_next(owner)
            self.assertEqual(store.search(owner,historical=True),[])
