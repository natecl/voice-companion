"""Real store/writer execution with deterministic model fixtures; no provider calls."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from admission import Rejected
import memory_evidence
import memory_evidence_chunks as chunks
from memory_evidence_writer import EvidenceWriter
from memory_store import MemoryStore
from test_memory import source
from test_memory_evidence_writer import proposal
from test_memory_learning import answers

FIRST='My daughter Maya enjoys swimming.'
CHANGE='My daughter Maya now enjoys tennis instead of swimming.'


def long_source():
    data=source('long')
    texts=[FIRST]+[f'Agenda section {i}: '+('We discussed the order of items. '*20) for i in range(24)]+[CHANGE]
    data['passages']=[dict(id=f'p{i}',text=t,start=float(i),duration=1.,speakers=[]) for i,t in enumerate(texts)]
    return data


class EvidenceChunkTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/'memory.sqlite'
        self.store=MemoryStore(self.path,personal_learning=True)
        self.owner=self.store.owner_for('owner');self.calls=[];self.attempts=set();outer=self
        class Models:
            async def extract(self,request):
                outer.calls.append(request)
                view=json.loads(request['input']);found=[]
                for passage in view['passages']:
                    for text in (FIRST,CHANGE):
                        if passage['text'].count(text)==1:
                            p=proposal(text,'correction' if text==CHANGE else 'none')
                            p['scope']='named';p['evidence']=[dict(passage=passage['id'],quote=text)];found.append(p)
                return dict(data=dict(memories=found),usage={})
            async def judge(self,request):
                outer.calls.append(request);labels={}
                for k,q in request['questions'].items():
                    if 'split' in q['criteria']:labels[k]='uncertain'
                    elif 'named' in q['criteria']:labels[k]='named'
                    elif 'supported' in q['criteria']:labels[k]='supported'
                    elif 'same' in q['criteria']:labels[k]='same'
                    elif 'current_change' in q['criteria']:labels[k]='current_change'
                    else:labels[k]='replacement'
                return dict(data=answers(request,labels),usage={})
        class Budget:
            def reserve(self,key,model):
                if key in outer.attempts:raise Rejected('paid_retry_requires_review')
                outer.attempts.add(key)
            def finish(self,*args):pass
        self.writer=EvidenceWriter(self.store,Models(),Budget(),luna_identity=False,chunking=True)

    async def test_long_correction_commits_once_with_original_sources(self):
        data=long_source();self.store.put_source(self.owner,data)
        result=await self.writer.process_next(self.owner)
        self.assertEqual(result['accepted'],2)
        rows=self.store.search(self.owner,historical=True)
        self.assertEqual(sorted(r['state'] for r in rows),['active','superseded'])
        self.assertEqual(len({r['entity_id'] for r in rows}),1)
        self.assertEqual({r['sources'][0]['passage'] for r in rows},{'p0','p25'})
        self.assertEqual(self.store.source(self.owner,'long'),data)
        count=len(self.calls);self.assertIsNone(await self.writer.process_next(self.owner));self.assertEqual(count,len(self.calls))
        self.store.delete_source(self.owner,'long');self.assertEqual(self.store.search(self.owner,historical=True),[])

    async def test_semantic_plan_runs_through_writer_and_persists(self):
        self.writer.semantic_boundaries=True
        self.store.put_source(self.owner,long_source());await self.writer.process_next(self.owner)
        self.assertTrue(any('boundaries' in r.get('state',{}) for r in self.calls))
        with self.store.connect() as db:
            plans=[json.loads(r[0]) for r in db.execute('SELECT plan FROM memory_chunk')]
        self.assertTrue(all(p['strategy']=='jev_boundary_overlap' for p in plans))
        self.assertEqual(len(self.store.search(self.owner)),1)

    async def test_completed_chunk_resume_reuses_results_and_never_partially_commits(self):
        self.store.put_source(self.owner,long_source());complete=self.store.complete_chunk
        def interrupted(*args):complete(*args);raise asyncio.CancelledError()
        self.store.complete_chunk=interrupted
        with self.assertRaises(asyncio.CancelledError):await self.writer.process_next(self.owner)
        self.assertEqual(self.store.search(self.owner,historical=True),[])
        before=list(self.calls)
        with self.store.connect() as db:job=db.execute('SELECT id FROM job').fetchone()[0]
        store=MemoryStore(self.path,personal_learning=True);store.resume_chunk_job(self.owner,job)
        self.writer.store=store;await self.writer.process_next(self.owner)
        for request in before:self.assertEqual(self.calls.count(request),1)
        self.assertEqual(len(store.search(self.owner,historical=True)),2)

    async def test_source_deletion_and_revision_during_processing_reject_late_results(self):
        for action in ['delete','revise']:
            with self.subTest(action=action):
                data=long_source();data['session_id']=action;self.store.put_source(self.owner,data)
                original=self.writer.models.extract
                async def changed(request):
                    if action=='delete':self.store.delete_source(self.owner,action)
                    else:self.store.put_source(self.owner,dict(data,revision=2))
                    return await original(request)
                self.writer.models.extract=changed
                with self.assertRaisesRegex(Rejected,'stale_job'):await self.writer.process_next(self.owner)
                self.writer.models.extract=original
                self.assertEqual(self.store.search(self.owner,historical=True),[])

    def test_lossless_mapping_and_overlap_repeated_quote_offsets(self):
        data=long_source();planned=chunks.plan(data);chunks.validate_plan(data,planned)
        self.assertGreater(len(planned),1)
        data=dict(source(),origin='personal_text');data['passages'][0]['text']=FIRST+' '+FIRST
        start=len(FIRST)+1
        view=dict(data,passages=[dict(data['passages'][0],id='fragment-0',text=FIRST)])
        chunk=dict(source=view,ranges=[dict(fragment='fragment-0',passage='p1',start=start,end=start+len(FIRST),primary=True)])
        raw=proposal(FIRST);raw['evidence'][0]['passage']='fragment-0'
        p=memory_evidence.parse(dict(memories=[raw]),view)[0]
        mapped=chunks.original_proposal(data,chunk,p)
        self.assertEqual(mapped['spans'][0]['start'],start)
        chunk['ranges'][0]['primary']=False;self.assertIsNone(chunks.original_proposal(data,chunk,p))
        chunk['ranges'][0]['primary']=True;chunk['ranges'][0]['start']+=1
        with self.assertRaisesRegex(Rejected,'invalid_evidence_quote'):chunks.original_proposal(data,chunk,p)

    async def test_legacy_chunk_contract_cannot_be_reused(self):
        self.store.put_source(self.owner,long_source());job=self.store.claim_job(self.owner)
        self.store.chunk_plan(job)
        with self.assertRaisesRegex(Rejected,'chunk_contract_changed'):
            self.store.chunk_plan(job,planner=chunks)

    def test_prior_long_passage_uses_original_span_context(self):
        from memory_judgments import pair_evidence
        p=proposal(FIRST);p['spans']=[dict(passage='p1',start=4000,end=4000+len(FIRST))]
        previous=dict(text=FIRST,proposal=p,evidence=[dict(passage=dict(id='p1',text='x'*4000+FIRST+'z'*4000,speakers=[]))])
        pair=dict(incoming=dict(source=long_source(),proposal=p),previous=previous)
        result=pair_evidence(pair,'identity')
        self.assertEqual(result['previous']['evidence'][0]['text'],'x'*200+FIRST+'z'*200)

    async def test_uncertain_paid_call_is_not_automatically_retried(self):
        self.store.put_source(self.owner,long_source());original=self.writer.models.extract
        async def interrupted(request):raise asyncio.CancelledError()
        self.writer.models.extract=interrupted
        with self.assertRaises(asyncio.CancelledError):await self.writer.process_next(self.owner)
        with self.store.connect() as db:job=db.execute('SELECT id FROM job').fetchone()[0]
        self.store.resume_chunk_job(self.owner,job);self.writer.models.extract=original
        with self.assertRaisesRegex(Rejected,'paid_retry_requires_review'):await self.writer.process_next(self.owner)
        self.assertEqual(self.calls,[])
        self.assertEqual(self.store.search(self.owner,historical=True),[])

    async def test_overlap_only_fact_is_not_written_twice(self):
        data=long_source();plan=chunks.plan(data)
        overlap=plan[1]['ranges'][0]
        p=next(p for p in data['passages'] if p['id']==overlap['passage'])
        p['text']=p['text'][:-len(FIRST)]+FIRST
        self.store.put_source(self.owner,data)
        await self.writer.process_next(self.owner)
        with self.store.connect() as db:
            results=[json.loads(r[0]) for r in db.execute('SELECT claims FROM memory_chunk')]
        # Each occurrence can appear at most once; overlap itself adds no new evidence.
        spans=[json.dumps(e['proposal']['spans'],sort_keys=True) for result in results for e in result]
        self.assertEqual(len(spans),len(set(spans)))

    async def test_repeated_quote_original_offsets_survive_atomic_commit(self):
        data=dict(source('repeated',text=FIRST+' '+FIRST),origin='personal_text')
        self.store.put_source(self.owner,data);job=self.store.claim_job(self.owner)
        raw=proposal(FIRST);start=len(FIRST)+1
        p=memory_evidence.parse(dict(memories=[raw]),data,exact_spans=[dict(passage='p1',start=start,end=start+len(FIRST))])[0]
        from memory_atomic import commit
        ids=commit(self.store,job,[dict(proposal=p,action='new',rubric='fixture',judgments={},identity_verified=True,profile_verified=True)])
        with self.store.connect() as db:
            saved=json.loads(db.execute('SELECT proposal FROM memory_fact_evidence WHERE claim=?',(ids[0],)).fetchone()[0])
        self.assertEqual(saved['spans'][0]['start'],start)

    def test_recording_schema_cannot_propose_account_ownership(self):
        request=memory_evidence.extraction_request(source())
        variants=request['text']['format']['schema']['properties']['memories']['items']['anyOf']
        self.assertEqual([v['properties']['scope']['enum'] for v in variants],[['named'],['unresolved']])
        self.assertEqual([v['properties']['mention']['properties']['name']['type'] for v in variants],['string','null'])
        self.assertEqual(json.loads(request['input'])['origin'],'recording')
        personal=memory_evidence.extraction_request(dict(source(),origin='personal_text'))
        self.assertIn('author',personal['text']['format']['schema']['properties']['memories']['items']['properties']['scope']['enum'])
        failed=json.loads((Path(__file__).parent/'fixtures/memory_evidence_chunks/failed/provider-calls.json').read_text())[-1]
        with self.assertRaisesRegex(Rejected,'unsupported_author_identity'):
            memory_evidence.parse(failed['response']['data'],json.loads(failed['request']['input']))

    async def test_single_long_passage_preserves_correction_spans_and_bounded_pairs(self):
        data=long_source();data['passages']=[dict(data['passages'][0],id='p1',text='\n'.join(p['text'] for p in data['passages']))]
        self.store.put_source(self.owner,data);await self.writer.process_next(self.owner)
        rows=self.store.search(self.owner,historical=True)
        self.assertEqual(sorted(r['state'] for r in rows),['active','superseded'])
        with self.store.connect() as db:
            evidence=[json.loads(r[0]) for r in db.execute('SELECT proposal FROM memory_fact_evidence')]
        for p in evidence:
            for span,ref in zip(p['spans'],p['evidence']):
                self.assertEqual(data['passages'][0]['text'][span['start']:span['end']],ref['quote'])
        pairs=[r for r in self.calls if 'pairs' in r.get('state',{})]
        self.assertTrue(pairs)
        for request in pairs:self.assertLess(len(json.dumps(request).encode()),16000)

    def test_verification_keeps_cited_context_without_unrelated_passages(self):
        from memory_judgments import verify_proposals
        data=long_source();p=proposal(FIRST);p['scope']='named';p['evidence'][0]['passage']='p0'
        request=verify_proposals(data,[p])
        self.assertEqual(request['state']['source']['passages'],[data['passages'][0]])
        self.assertEqual(request['state']['source']['session_id'],data['session_id'])
        self.assertIn(FIRST,request['questions']['support_0']['instructions']['cited_transcript'])

    async def test_exact_provider_replay_of_final_semantic_writer(self):
        import copy
        directory=Path(__file__).parent/'fixtures/memory_evidence_chunks/recorded'
        artifact=json.loads((directory/'result.json').read_text())
        calls=json.loads((directory/'provider-calls.json').read_text());index=0
        async def consume(role,request):
            nonlocal index
            expected=calls[index];index+=1
            self.assertEqual(expected['role'],role);self.assertEqual(expected['request'],request)
            return copy.deepcopy(expected['response'])
        async def extract(request):return await consume('extract',request)
        async def judge(request):return await consume('judge',request)
        self.writer.models.extract=extract;self.writer.models.judge=judge
        self.writer.luna_identity=True;self.writer.semantic_boundaries=True
        self.store.put_source(self.owner,artifact['source']);await self.writer.process_next(self.owner)
        self.assertEqual(index,len(calls))
        rows=self.store.search(self.owner,historical=True)
        self.assertEqual(sorted(r['state'] for r in rows),['active','superseded'])
        self.assertEqual(len({r['entity_id'] for r in rows}),1)
        self.assertTrue(all(r['subject']!='user' and not r['profile_link'] for r in rows))
        self.assertEqual(self.store.search(self.owner,unresolved_only=True),[])
