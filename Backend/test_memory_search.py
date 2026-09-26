import tempfile
from pathlib import Path
import unittest
from memory_store import MemoryStore
from memory_search import retrieve
from test_memory import source,candidate
from admission import Rejected


class SearchTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.store=MemoryStore(Path(folder.name)/'memory.sqlite',clock=lambda:300.)
        self.owner=self.store.owner_for('qa')

    def test_index_update_deletion_tombstone_and_owner_scope(self):
        self.store.put_source(self.owner,source(text='Maya studies astronomy.'))
        other=self.store.owner_for('other');self.store.put_source(other,source(text='Private astronomy.'))
        self.assertEqual(len(retrieve(self.store,self.owner,'astronomy')),1)
        revised=source(revision=2,text='Maya studies biology.')
        self.store.put_source(self.owner,revised)
        self.assertEqual(retrieve(self.store,self.owner,'astronomy'),[])
        self.assertEqual(retrieve(self.store,self.owner,'biology')[0]['revision'],2)
        self.assertEqual(retrieve(self.store,self.owner,'biology',exclude_session='session-a'),[])
        self.store.delete_source(self.owner,'session-a')
        self.store.put_source(self.owner,revised)
        self.assertEqual(retrieve(self.store,self.owner,'biology'),[])
        self.assertEqual(len(retrieve(self.store,other,'astronomy')),1)

    def test_query_is_literal_and_lifecycle_is_preserved(self):
        self.store.put_source(self.owner,source(text='The café appointment is Tuesday.'))
        self.store.commit_claims(self.store.claim_job(self.owner),[candidate(valid_until=200.)])
        result=retrieve(self.store,self.owner,'café')
        self.assertEqual(result[0]['lifecycle'][0]['state'],'expired')
        for query in ['" OR * : NEAR(', '', '!!!']:
            self.assertEqual(retrieve(self.store,self.owner,query),[])
        with self.assertRaises(Rejected):retrieve(self.store,self.owner,'a',limit=0)
        with self.assertRaises(Rejected):retrieve(self.store,self.owner,'a'*1001)

    def test_schema9_rebuild_preserves_sources_and_does_not_queue_learning(self):
        self.store.put_source(self.owner,source(text='Old astronomy note.'))
        self.store.commit_claims(self.store.claim_job(self.owner),[])
        with self.store.connect() as db:
            db.execute('DROP TABLE IF EXISTS memory_embedding');db.execute('DROP TABLE memory_passage_index');db.execute('PRAGMA user_version=9')
        reopened=MemoryStore(self.store.path)
        self.assertEqual(retrieve(reopened,self.owner,'astronomy')[0]['text'],'Old astronomy note.')
        self.assertIsNone(reopened.claim_job(self.owner))
        with reopened.connect() as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            db.execute("INSERT INTO memory_passage_index(memory_passage_index) VALUES('integrity-check')")

    def test_older_match_survives_one_thousand_source_library(self):
        self.store.put_source(self.owner,source('oldest',text='Maya practices underwater hockey at the municipal pool.'))
        for i in range(999):
            self.store.put_source(self.owner,source(f'n{i}',text='Maya practices swimming at the neighborhood pool.'))
        hits=retrieve(self.store,self.owner,'underwater hockey',limit=8)
        self.assertEqual([h['session_id'] for h in hits],['oldest'])
        self.assertEqual(len(self.store.recall_snapshot(self.owner)),1000)

    def test_function_words_do_not_create_false_lexical_matches(self):
        self.store.put_source(self.owner,source(text='My physics examination is on Thursday.'))
        self.assertEqual(retrieve(self.store,self.owner,'When is a good time to ring my father?'),[])
        self.assertEqual(retrieve(self.store,self.owner,'When is my physics examination?')[0]['text'],
                         'My physics examination is on Thursday.')
