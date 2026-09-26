from pathlib import Path
import tempfile
import unittest
from memory_store import MemoryStore
from memory_indexing import IndexWorker,coverage
from memory_vectors import retrieve
from test_memory import source
from test_memory_vectors import TinyEmbedder


class IndexingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.model=TinyEmbedder();self.path=Path(folder.name)/'memory.sqlite'
        self.store=MemoryStore(self.path,embedding_model=self.model.contract)
        self.owner=self.store.owner_for('qa')
        class Admission:
            def active_credentials(self):return ['qa']
        self.worker=IndexWorker(self.store,self.model,Admission())

    async def test_source_queue_worker_cache_and_deletion(self):
        self.store.put_source(self.owner,source())
        self.assertEqual(coverage(self.store,self.owner,self.model.contract),{'queued':1})
        self.assertEqual(self.model.calls,0)
        self.assertTrue(await self.worker.step())
        self.assertEqual(coverage(self.store,self.owner,self.model.contract),{'done':1})
        self.assertEqual(len(retrieve(self.store,self.owner,'appointment',self.model)),1)
        self.store.put_source(self.owner,source());self.assertFalse(await self.worker.step())
        self.store.delete_source(self.owner,'session-a')
        self.assertEqual(retrieve(self.store,self.owner,'appointment',self.model),[])
        self.assertEqual(coverage(self.store,self.owner,self.model.contract),{})

    async def test_revision_during_inference_and_other_owner(self):
        self.store.put_source(self.owner,source())
        self.model.after=lambda:self.store.put_source(self.owner,source(revision=2))
        self.assertEqual((await self.worker.step())['status'],'failed')
        self.model.after=None
        self.assertTrue(await self.worker.step())
        self.assertEqual(retrieve(self.store,self.owner,'appointment',self.model)[0]['revision'],2)
        other=self.store.owner_for('not-authorized');self.store.put_source(other,source())
        self.assertFalse(await self.worker.step())

    async def test_failed_source_does_not_block_next_and_restart_reuses_cache(self):
        self.store.put_source(self.owner,source('bad'));self.store.put_source(self.owner,source('good'))
        original=self.model.windows
        def too_large(text):
            for i in range(513):yield 0,len(text),text
        self.model.windows=too_large
        self.assertEqual((await self.worker.step())['reason'],'embedding_source_too_large')
        self.model.windows=original
        job=self.worker.claim()
        from memory_vectors import index_source
        index_source(self.store,self.owner,job['session'],self.model)
        self.worker.recover()
        self.assertEqual((await self.worker.step())['status'],'cached')
        self.assertEqual(coverage(self.store,self.owner,self.model.contract),{'done':1,'failed':1})
        self.assertFalse(await self.worker.step())

    async def test_default_off_migration_no_backfill_or_incomplete_indexing(self):
        default=MemoryStore(self.path)
        default.put_source(self.owner,source('old'))
        self.assertEqual(coverage(default,self.owner,self.model.contract),{'unindexed':1})
        incomplete=source('partial');incomplete['completed']=False
        self.store.put_source(self.owner,incomplete)
        self.assertFalse(await self.worker.step())
        with self.store.connect() as db:
            db.execute('DROP TABLE memory_index_job');db.execute('DROP INDEX claim_replacement');db.execute('PRAGMA user_version=11')
        reopened=MemoryStore(self.path,embedding_model=self.model.contract)
        self.assertEqual(coverage(reopened,self.owner,self.model.contract),{'unindexed':1})
        self.assertEqual(self.model.calls,0)

    async def test_revision_changed_before_computation_is_rejected_without_model_work(self):
        from memory_vectors import index_source
        from admission import Rejected
        self.store.put_source(self.owner,source(revision=2))
        with self.assertRaisesRegex(Rejected,'stale_embedding_source'):
            index_source(self.store,self.owner,'session-a',self.model,expected_revision=1)
        self.assertEqual(self.model.calls,0)
