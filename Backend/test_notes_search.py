import json
from pathlib import Path
import tempfile
import unittest
from memory_store import MemoryStore
from recording_notes import RecordingNotes
from notes_search import retrieve
from test_memory import source
from test_recording_notes import notes


class NotesSearchTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.store=MemoryStore(Path(self.folder.name)/'memory.sqlite',retain_recording_memories=True)
        self.owner=self.store.owner_for('one');self.other=self.store.owner_for('two')
        self.source=source(text='Project Cedar meets at the pavilion.')
        self.store.put_source(self.owner,self.source)
        self.notes=RecordingNotes(self.store)
        self.notes.enqueue(self.owner,'session-a',1)
        self.notes.complete(self.notes.claim(self.owner,'session-a'),notes())

    def test_reopen_owner_exclusion_and_bounded_entries(self):
        reopened=MemoryStore(self.store.path)
        hits=retrieve(reopened,self.owner,'Cedar',limit=1)
        self.assertEqual(len(hits),1)
        self.assertEqual(hits[0]['passages'],['p1'])
        self.assertLess(len(hits[0]['text']),2000)
        self.assertEqual(retrieve(reopened,self.other,'Cedar'),[])
        self.assertEqual(retrieve(reopened,self.owner,'Cedar',exclude_session='session-a'),[])
        self.assertEqual(retrieve(reopened,self.owner,'the'),[])

    def test_revision_and_deletion_remove_entries(self):
        self.store.put_source(self.owner,dict(self.source,revision=2))
        self.assertEqual(retrieve(self.store,self.owner,'Cedar'),[])
        self.notes.enqueue(self.owner,'session-a',2)
        self.notes.complete(self.notes.claim(self.owner,'session-a'),notes())
        self.assertEqual(retrieve(self.store,self.owner,'Cedar')[0]['revision'],2)
        self.store.delete_source(self.owner,'session-a')
        self.assertEqual(retrieve(self.store,self.owner,'Cedar'),[])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM recording_note_index').fetchone()[0],0)

    def test_pending_failed_and_old_generation_are_not_candidates(self):
        with self.store.transaction() as db:
            db.execute("UPDATE recording_notes SET generation_version='old'")
        self.assertEqual(retrieve(self.store,self.owner,'Cedar'),[])
        with self.store.transaction() as db:
            db.execute("UPDATE recording_notes SET state='outdated'")
        self.notes.enqueue(self.owner,'session-a',1)
        self.assertEqual(retrieve(self.store,self.owner,'Cedar'),[])
        job=self.notes.claim(self.owner,'session-a');self.notes.fail(job,'generation_failed')
        self.assertEqual(retrieve(self.store,self.owner,'Cedar'),[])

    def test_schema17_backfills_existing_notes_without_inference(self):
        with self.store.connect() as db:
            before=[tuple(r) for r in db.execute('SELECT * FROM recording_notes')]
            db.execute('DROP TABLE recording_note_index');db.execute('PRAGMA user_version=17')
        reopened=MemoryStore(self.store.path)
        self.assertTrue(retrieve(reopened,self.owner,'Cedar'))
        with reopened.connect() as db:
            self.assertEqual(before,[tuple(r) for r in db.execute('SELECT * FROM recording_notes')])
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
