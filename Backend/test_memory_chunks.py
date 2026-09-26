"""Lossless planning and durable writer replay without provider inference."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from admission import Rejected
from memory_chunks import plan, request_size, TARGET_REQUEST_BYTES
from memory_store import MemoryStore, validate_source
from memory_writer import MemoryWriter
from test_memory import source
from test_memory_learning import memory, answers


class ChunkTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'memory.sqlite'
        self.store=MemoryStore(self.path)
        self.owner=self.store.owner_for('fixture')
        self.large=source('large',text='Maya prefers morning meetings. '*900)
        validate_source(self.large)
        self.calls=[]; self.attempts=set()
        outer=self
        class Models:
            async def extract(self,request):
                outer.calls.append('extract')
                view=json.loads(request['input'])
                return {'data':{'memories':[dict(memory(),source_ids=[view['passages'][0]['id']])]},'usage':{}}
            async def verify_support(self,request):
                outer.calls.append('support');return {'data':answers(request),'usage':{}}
            async def judge(self,request):
                outer.calls.append('judge');return {'data':answers(request),'usage':{}}
        class Budget:
            def reserve(self,key,model):
                if key in outer.attempts: raise Rejected('paid_retry_requires_review')
                outer.attempts.add(key)
            def finish(self,*args): pass
        self.writer=MemoryWriter(self.store,Models(),Budget(),chunking=True)

    def coverage(self, data):
        chunks=plan(data)
        self.assertGreater(len(chunks),1)
        self.assertEqual(chunks,plan(data))
        originals={p['id']:p['text'] for p in data['passages']}
        reconstructed={k:[] for k in originals}
        for chunk in chunks:
            self.assertLessEqual(request_size(chunk['source']),TARGET_REQUEST_BYTES)
            for passage,span in zip(chunk['source']['passages'],chunk['ranges']):
                self.assertEqual(passage['text'], originals[span['passage']][span['start']:span['end']])
                if span['primary']: reconstructed[span['passage']].append((span['start'],span['end'],passage['text']))
        for key, parts in reconstructed.items():
            cursor=0
            for start,end,text in parts:
                self.assertEqual(start,cursor);cursor=end
            self.assertEqual(cursor,len(originals[key]))
            self.assertEqual(''.join(p[2] for p in parts),originals[key])
        return chunks

    def test_lossless_unicode_escapes_turns_and_overlap(self):
        for text in ['Maya prefers morning meetings. '*900, '🎧 café 中文 \\ "\n'*600]:
            with self.subTest(text_kind=text[:5]):
                data=source(text=text);validate_source(data)
                chunks=self.coverage(data)
                self.assertTrue(any(not r['primary'] for c in chunks[1:] for r in c['ranges']))
        data=source()
        data['passages']=[dict(id=f'p{i}',start=float(i),duration=1.,speakers=[i%2],text='A full conversation turn. '*15) for i in range(80)]
        validate_source(data);self.coverage(data)

    def test_small_sources_keep_exact_legacy_path(self):
        self.assertEqual(plan(source()),[])

    async def test_large_source_runs_actual_writer_deduplicates_and_preserves_original_refs(self):
        self.store.put_source(self.owner,self.large)
        result=await self.writer.process_next(self.owner)
        self.assertEqual(result['accepted'],1)
        claims=self.store.search(self.owner)
        self.assertEqual(len(claims),1)
        self.assertEqual(claims[0]['sources'][0]['passage'],'p1')
        self.assertEqual(claims[0]['sources'][0]['session'],'large')
        self.assertEqual(len(self.calls),3*len(plan(self.large)))
        self.assertEqual(self.store.source(self.owner,'large'),self.large)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_chunk WHERE claims IS NULL').fetchone()[0],0)
        self.assertIsNone(await self.writer.process_next(self.owner))

    async def test_eight_large_candidates_are_batched_without_dropping_evidence(self):
        self.store.put_source(self.owner,self.large)
        async def extract(request):
            self.calls.append('extract')
            view=json.loads(request['input'])
            return {'data':{'memories':[dict(memory(('Maya preference '+str(i)+' ')*60),
                source_ids=[p['id'] for p in view['passages']]) for i in range(8)]},'usage':{}}
        original_support=self.writer.models.verify_support
        original_judge=self.writer.models.judge
        async def support(request):
            self.assertLessEqual(len(json.dumps(request,ensure_ascii=False).encode()),28000)
            return await original_support(request)
        async def judge(request):
            self.assertLessEqual(len(json.dumps(request,ensure_ascii=False).encode()),28000)
            return await original_judge(request)
        self.writer.models.extract=extract
        self.writer.models.verify_support=support
        self.writer.models.judge=judge
        result=await self.writer.process_next(self.owner)
        self.assertEqual(result['accepted'],8)
        self.assertEqual(len(self.store.search(self.owner)),8)
        self.assertGreater(self.calls.count('support'),self.calls.count('extract'))

    async def test_explicit_resume_reuses_completed_chunks_without_repeating_calls(self):
        self.store.put_source(self.owner,self.large)
        complete=self.store.complete_chunk
        def interrupt_after_checkpoint(*args):
            complete(*args)
            raise asyncio.CancelledError()
        self.store.complete_chunk=interrupt_after_checkpoint
        with self.assertRaises(asyncio.CancelledError): await self.writer.process_next(self.owner)
        self.assertEqual(len(self.calls),3)
        self.assertEqual(self.store.search(self.owner),[])
        with self.store.connect() as db:
            job=db.execute('SELECT id FROM job').fetchone()[0]
        reopened=MemoryStore(self.path)
        self.assertIsNone(reopened.claim_job(self.owner)) # No automatic paid recovery.
        reopened.resume_chunk_job(self.owner,job)
        self.writer.store=reopened
        await self.writer.process_next(self.owner)
        self.assertEqual(len(self.calls),3*len(plan(self.large)))
        self.assertEqual(len(reopened.search(self.owner)),1)
        with self.assertRaisesRegex(Rejected,'chunk_resume_not_eligible'): reopened.resume_chunk_job(self.owner,job)

    async def test_uncertain_paid_attempt_is_not_retried_on_explicit_resume(self):
        self.store.put_source(self.owner,self.large)
        original=self.writer.models.extract
        async def interrupted(request):
            self.calls.append('interrupted-extract')
            raise asyncio.CancelledError()
        self.writer.models.extract=interrupted
        with self.assertRaises(asyncio.CancelledError): await self.writer.process_next(self.owner)
        with self.store.connect() as db: job=db.execute('SELECT id FROM job').fetchone()[0]
        self.store.resume_chunk_job(self.owner,job)
        self.writer.models.extract=original
        with self.assertRaisesRegex(Rejected,'paid_retry_requires_review'): await self.writer.process_next(self.owner)
        self.assertEqual(self.calls,['interrupted-extract'])

    async def test_delete_during_chunk_processing_purges_plan_and_rejects_results(self):
        self.store.put_source(self.owner,self.large)
        original=self.writer.models.extract
        async def deleted(request):
            self.store.delete_source(self.owner,'large')
            return await original(request)
        self.writer.models.extract=deleted
        with self.assertRaisesRegex(Rejected,'stale_job'): await self.writer.process_next(self.owner)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_chunk').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM job_result').fetchone()[0],0)
        self.assertEqual(self.store.search(self.owner),[])

    def test_foreign_resume_and_revised_job_rejected(self):
        self.store.put_source(self.owner,self.large)
        job=self.store.claim_job(self.owner)
        self.store.chunk_plan(job)
        self.store.recover_jobs()
        other=self.store.owner_for('other')
        with self.assertRaisesRegex(Rejected,'chunk_resume_not_eligible'): self.store.resume_chunk_job(other,job['id'])
        self.store.put_source(self.owner,dict(self.large,revision=2))
        with self.assertRaisesRegex(Rejected,'stale_job'): self.store.complete_chunk(job,'missing',[])
        with self.assertRaisesRegex(Rejected,'chunk_resume_not_eligible'): self.store.resume_chunk_job(self.owner,job['id'])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_chunk').fetchone()[0],0)

    def test_cached_plan_rejects_changed_processing_contract(self):
        self.store.put_source(self.owner,self.large)
        job=self.store.claim_job(self.owner)
        self.store.chunk_plan(job)
        with patch('memory_chunks.VERSION','changed-contract'):
            with self.assertRaisesRegex(Rejected,'chunk_contract_changed'):
                self.store.chunk_plan(job)
        self.assertEqual(self.calls,[])

    def test_schema6_migration_keeps_sources_and_no_automatic_plans(self):
        self.store.put_source(self.owner,self.large)
        with self.store.connect() as db:
            db.execute('DROP TABLE memory_chunk');db.execute('PRAGMA user_version=6')
        migrated=MemoryStore(self.path)
        self.assertEqual(migrated.source(self.owner,'large'),self.large)
        with migrated.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_chunk').fetchone()[0],0)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])


if __name__=='__main__': unittest.main()
