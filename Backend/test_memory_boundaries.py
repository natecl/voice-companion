import asyncio
import copy
import unittest
from admission import Rejected
from memory_chunks import semantic_plan, validate_plan
from test_memory import source
import test_memory_chunks
from test_memory_learning import answers


class BoundaryTests(unittest.IsolatedAsyncioTestCase):
    def data(self):
        data=source()
        data['passages']=[dict(id=f'p{i}',start=float(i),duration=1.,speakers=[i%2],text=f'Topic {i}. '+('A complete thought. '*35)) for i in range(24)]
        return data

    async def test_independent_boundary_selection_preserves_all_ranges(self):
        data=self.data();calls=[]
        async def evaluate(request):
            calls.append(request)
            result=answers(request,{key:'split' for key in request['questions']})
            return {'data':result}
        chunks=await semantic_plan(data,evaluate)
        validate_plan(data,chunks)
        self.assertTrue(calls)
        self.assertEqual(chunks[0]['boundary_reason'],'jev_split')
        for request in calls:
            for key,q in request['questions'].items():
                self.assertIn(key,q['instructions'])
        corrupted=copy.deepcopy(chunks);corrupted[0]['ranges'][0]['start']=1
        with self.assertRaises(Rejected):validate_plan(data,corrupted)

    async def test_uncertain_boundaries_keep_bounded_overlap(self):
        async def evaluate(request):
            return {'data':answers(request,{key:'uncertain' for key in request['questions']})}
        data=self.data();chunks=await semantic_plan(data,evaluate)
        validate_plan(data,chunks)
        self.assertEqual(chunks[0]['boundary_reason'],'hard_limit_overlap')
        self.assertEqual(chunks[-1]['boundary_reason'],'end')

    async def test_no_useful_whole_turn_boundary_makes_no_call(self):
        async def forbidden(request):raise AssertionError('Unnecessary boundary call')
        data=source(text='One long utterance. '*1200)
        chunks=await semantic_plan(data,forbidden)
        validate_plan(data,chunks)


class SemanticWriterTests(unittest.IsolatedAsyncioTestCase):
    setUp = test_memory_chunks.ChunkTests.setUp
    # Reuse the actual chunk writer setup, not the inherited test suite.
    async def test_semantic_writer_persists_plan_across_source_serialization(self):
        self.large=BoundaryTests().data()
        self.large['session_id']='large'
        self.store.put_source(self.owner,self.large)
        normal=self.writer.models.judge
        boundary_calls=[]
        async def judge(request):
            if 'boundaries' in request['state']:
                boundary_calls.append(request)
                return {'data':answers(request,{key:'split' for key in request['questions']}),'usage':{}}
            return await normal(request)
        self.writer.models.judge=judge
        self.writer.semantic_boundaries=True
        await self.writer.process_next(self.owner)
        self.assertTrue(boundary_calls)
        with self.store.connect() as db:
            import json
            plans=[json.loads(r[0]) for r in db.execute('SELECT plan FROM memory_chunk ORDER BY ordinal')]
        validate_plan(self.large,plans)
        self.assertTrue(all(p['strategy']=='jev_boundary_overlap' for p in plans))

    async def test_completed_boundary_calls_survive_interruption_before_plan_save(self):
        self.large=BoundaryTests().data()
        self.store.put_source(self.owner,self.large)
        self.writer.semantic_boundaries=True
        normal=self.writer.models.judge
        boundary_calls=[]
        async def judge(request):
            if 'boundaries' in request['state']:
                boundary_calls.append(request)
                return {'data':answers(request,{key:'split' for key in request['questions']}),'usage':{}}
            return await normal(request)
        self.writer.models.judge=judge
        replace=self.store.replace_chunk_plan
        def interrupted(*args):raise asyncio.CancelledError()
        self.store.replace_chunk_plan=interrupted
        with self.assertRaises(asyncio.CancelledError):await self.writer.process_next(self.owner)
        count=len(boundary_calls)
        self.assertGreater(count,0)
        with self.store.connect() as db:job=db.execute('SELECT id FROM job').fetchone()[0]
        self.store.resume_chunk_job(self.owner,job)
        self.store.replace_chunk_plan=replace
        await self.writer.process_next(self.owner)
        self.assertEqual(len(boundary_calls),count)

    async def test_deleted_source_cannot_receive_semantic_plan(self):
        data=BoundaryTests().data()
        self.store.put_source(self.owner,data)
        job=self.store.claim_job(self.owner)
        self.store.chunk_plan(job)
        async def evaluate(request):
            return {'data':answers(request,{key:'split' for key in request['questions']})}
        chunks=await semantic_plan(data,evaluate)
        self.store.delete_source(self.owner,data['session_id'])
        with self.assertRaisesRegex(Rejected,'stale_job'):self.store.replace_chunk_plan(job,chunks)
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM memory_chunk').fetchone()[0],0)


class RecordedBoundaryTests(unittest.TestCase):
    def test_real_provider_boundary_response_meets_frozen_gate(self):
        import json
        from pathlib import Path
        from memory_chunks import boundary_choices
        directory=Path(__file__).parent/'fixtures/memory_boundaries'
        recorded=json.loads((directory/'recorded/boundary-response.json').read_text())
        judgments=boundary_choices(recorded['response']['data'],recorded['request'])
        for case in json.loads((directory/'cases.json').read_text()):
            decision=judgments[case['id']]
            self.assertEqual(decision['choice']=='split' and decision['probabilities']['split']>=.80,case['split'],case['id'])
