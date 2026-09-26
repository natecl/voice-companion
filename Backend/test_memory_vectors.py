from pathlib import Path
import tempfile
import unittest
from admission import Rejected
from memory_store import MemoryStore
from memory_vectors import index_source,retrieve
from test_memory import source


class TinyEmbedder:
    contract='fixture-model-v1';dimensions=2
    def __init__(self):self.calls=0;self.after=None
    def windows(self,text):yield 0,len(text),text
    def passages(self,texts):
        self.calls+=1
        if self.after:self.after()
        return [[1.,0.] for text in texts]
    def query(self,text):return [1.,0.]


class VectorTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.store=MemoryStore(Path(folder.name)/'memory.sqlite');self.owner=self.store.owner_for('qa')
        self.embedder=TinyEmbedder()
        self.store.put_source(self.owner,source())

    def test_versioned_cache_and_reopen(self):
        self.assertEqual(index_source(self.store,self.owner,'session-a',self.embedder)['status'],'indexed')
        self.assertEqual(index_source(self.store,self.owner,'session-a',self.embedder)['status'],'cached')
        self.assertEqual(self.embedder.calls,1)
        reopened=MemoryStore(self.store.path)
        self.assertEqual(len(retrieve(reopened,self.owner,'appointment',self.embedder)),1)
        self.embedder.contract='fixture-model-v2'
        self.assertEqual(retrieve(reopened,self.owner,'appointment',self.embedder),[])
        index_source(reopened,self.owner,'session-a',self.embedder)
        self.assertEqual(self.embedder.calls,2)

    def test_deletion_revision_and_owner_scope(self):
        index_source(self.store,self.owner,'session-a',self.embedder)
        other=self.store.owner_for('other')
        self.assertEqual(retrieve(self.store,other,'appointment',self.embedder),[])
        self.assertEqual(retrieve(self.store,self.owner,'appointment',self.embedder,exclude_session='session-a'),[])
        self.store.put_source(self.owner,source(revision=2))
        self.assertEqual(retrieve(self.store,self.owner,'appointment',self.embedder),[])
        index_source(self.store,self.owner,'session-a',self.embedder)
        self.store.delete_source(self.owner,'session-a')
        self.assertEqual(retrieve(self.store,self.owner,'appointment',self.embedder),[])
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM memory_embedding').fetchone()[0],0)

    def test_late_result_cannot_resurrect_deleted_or_revised_source(self):
        for revision in (False,True):
            with self.subTest(revision=revision):
                session='revised' if revision else 'deleted'
                self.store.put_source(self.owner,source(session))
                self.embedder.after=lambda:self.store.put_source(self.owner,source(session,revision=2)) if revision else self.store.delete_source(self.owner,session)
                with self.assertRaisesRegex(Rejected,'stale_embedding_source'):
                    index_source(self.store,self.owner,session,self.embedder)
                with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM memory_embedding WHERE session=?',(session,)).fetchone()[0],0)

    def test_invalid_vectors_are_not_cached(self):
        self.embedder.passages=lambda texts:[[float('nan'),0.]]
        with self.assertRaisesRegex(Rejected,'invalid_embedding'):
            index_source(self.store,self.owner,'session-a',self.embedder)
        self.assertEqual(retrieve(self.store,self.owner,'appointment',self.embedder),[])

    def test_schema10_adds_empty_cache_without_inference(self):
        with self.store.connect() as db:
            db.execute('DROP TABLE memory_embedding');db.execute('PRAGMA user_version=10')
        reopened=MemoryStore(self.store.path)
        with reopened.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_embedding').fetchone()[0],0)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        self.assertIsNotNone(reopened.source(self.owner,'session-a'))
