import copy
import json
from pathlib import Path
import tempfile
import unittest
from admission import Rejected
from memory_store import MemoryStore
from recording_notes import RecordingNotes, MAX_INPUT_BYTES
from test_memory import source


def notes():
    return dict(title='Cedar meeting', overview=dict(text='Cedar meets at the pavilion.',passages=['p1']),
                sections=[dict(heading='Details',items=[dict(text='The venue is the pavilion.',passages=['p1'])])])

class RecordingNotesTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.path=Path(self.folder.name)/'memory.sqlite'
        self.store=MemoryStore(self.path,retain_recording_memories=True)
        self.owner=self.store.owner_for('one');self.other=self.store.owner_for('two')
        self.source=source(text='Project Cedar meets at the pavilion.')
        self.store.put_source(self.owner,self.source)
        self.notes=RecordingNotes(self.store)

    def start(self):
        self.assertEqual(self.notes.enqueue(self.owner,'session-a',1),'pending')
        return self.notes.claim(self.owner,'session-a')

    def test_save_reopen_no_duplicate_attempt_or_implicit_backfill(self):
        self.assertIsNone(self.notes.read(self.owner,'session-a'))
        job=self.start()
        self.assertIsNone(self.notes.claim(self.owner,'session-a'))
        self.assertEqual(self.notes.enqueue(self.owner,'session-a',1),'generating')
        self.notes.complete(job,notes())
        reopened=RecordingNotes(MemoryStore(self.path))
        self.assertEqual(reopened.read(self.owner,'session-a')['notes'],notes())
        self.assertEqual(reopened.enqueue(self.owner,'session-a',1),'ready')
        self.assertIsNone(reopened.claim(self.owner,'session-a'))
        self.assertFalse(reopened.read(self.owner,'session-a')['incomplete'])

    def test_revision_hides_notes_and_blocks_late_result(self):
        job=self.start();self.notes.complete(job,notes())
        changed=dict(self.source,revision=2)
        self.store.put_source(self.owner,changed)
        self.assertEqual(self.notes.read(self.owner,'session-a')['state'],'outdated')
        self.assertIsNone(self.notes.read(self.owner,'session-a')['notes'])
        with self.assertRaisesRegex(Rejected,'stale_notes'):self.notes.complete(job,notes())
        self.assertEqual(self.notes.enqueue(self.owner,'session-a',2),'pending')
        fresh=self.notes.claim(self.owner,'session-a');self.notes.complete(fresh,notes())
        self.assertEqual(self.notes.read(self.owner,'session-a')['revision'],2)

    def test_deletion_erases_notes_even_when_retention_enabled(self):
        job=self.start();self.notes.complete(job,notes())
        self.store.delete_source(self.owner,'session-a')
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM recording_notes').fetchone()[0],0)
        for action in [lambda:self.notes.read(self.owner,'session-a'),lambda:self.notes.complete(job,notes()),lambda:self.notes.enqueue(self.owner,'session-a',1)]:
            with self.assertRaisesRegex(Rejected,'source_unavailable'):action()
        self.assertEqual(self.store.put_source(self.owner,self.source)['status'],'deleted')

    def test_delete_during_generation_never_recreates_notes(self):
        job=self.start();self.store.delete_source(self.owner,'session-a')
        with self.assertRaises(Rejected):self.notes.complete(job,notes())
        self.notes.fail(job,'generation_failed')
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM recording_notes').fetchone()[0],0)

    def test_failed_attempt_needs_explicit_retry_and_old_result_cannot_win(self):
        old=self.start();self.notes.fail(old,'generation_failed')
        self.assertEqual(self.notes.enqueue(self.owner,'session-a',1),'failed')
        self.assertIsNone(self.notes.claim(self.owner,'session-a'))
        self.assertEqual(self.notes.enqueue(self.owner,'session-a',1,retry=True),'pending')
        new=self.notes.claim(self.owner,'session-a')
        with self.assertRaisesRegex(Rejected,'stale_notes'):self.notes.complete(old,notes())
        self.notes.fail(old,'generation_failed')
        self.notes.complete(new,notes())
        self.assertEqual(self.notes.read(self.owner,'session-a')['state'],'ready')

    def test_restart_does_not_retry_inflight_paid_work(self):
        job=self.start();reopened=RecordingNotes(MemoryStore(self.path))
        reopened.recover_interrupted()
        self.assertEqual(reopened.read(self.owner,'session-a')['error'],'generation_interrupted')
        with self.assertRaisesRegex(Rejected,'stale_notes'):reopened.complete(job,notes())
        self.assertIsNone(reopened.claim(self.owner,'session-a'))

    def test_incomplete_recording_is_explicit(self):
        self.store.put_source(self.owner,dict(self.source,revision=2,completed=False))
        self.notes.enqueue(self.owner,'session-a',2)
        self.notes.complete(self.notes.claim(self.owner,'session-a'),notes())
        self.assertTrue(self.notes.read(self.owner,'session-a')['incomplete'])

    def test_empty_and_oversized_inputs_never_claim_generation(self):
        for data,reason in [(dict(self.source,passages=[]),'empty_transcript'),
                            (source(text='x'*MAX_INPUT_BYTES),'notes_input_too_large')]:
            data=dict(data,revision=2 if reason=='empty_transcript' else 3)
            self.store.put_source(self.owner,data)
            self.assertEqual(self.notes.enqueue(self.owner,'session-a',data['revision']),'failed')
            self.assertEqual(self.notes.read(self.owner,'session-a')['error'],reason)
            self.assertIsNone(self.notes.claim(self.owner,'session-a'))

    def test_owner_isolation(self):
        self.start()
        with self.assertRaisesRegex(Rejected,'source_unavailable'):self.notes.read(self.other,'session-a')
        self.store.put_source(self.other,self.source)
        self.assertIsNone(self.notes.read(self.other,'session-a'))
        self.assertIsNone(self.notes.claim(self.other,'session-a'))

    def test_bad_citation_and_unbounded_output_never_saved(self):
        job=self.start()
        for mutate in [lambda n:n['overview'].update(passages=['invented']),
                       lambda n:n.update(title=' '*3),
                       lambda n:n['overview'].update(text='x'*1201),
                       lambda n:n.update(extra='ignored'),
                       lambda n:n['overview'].update(passages=['p1','p1'])]:
            value=notes();mutate(value)
            with self.assertRaises(Rejected):self.notes.complete(job,value)
        self.assertEqual(self.notes.read(self.owner,'session-a')['state'],'generating')
        self.assertIsNone(self.notes.read(self.owner,'session-a')['notes'])

    def test_personal_text_is_not_automatically_summarized(self):
        data=source('personal');data['origin']='personal_text'
        self.store.put_source(self.owner,data)
        with self.assertRaisesRegex(Rejected,'notes_require_recording'):self.notes.enqueue(self.owner,'personal',1)

    def test_schema16_upgrade_preserves_existing_source_without_backfill(self):
        with self.store.connect() as db:
            before=[tuple(r) for r in db.execute('SELECT * FROM source')]
            db.execute('DROP TABLE recording_note_index');db.execute('DROP TABLE recording_notes');db.execute('DROP TABLE account_identity');db.execute('PRAGMA user_version=16')
        migrated=MemoryStore(self.path)
        with migrated.connect() as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM source')],before)
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],20)
            self.assertEqual(db.execute('SELECT count(*) FROM recording_notes').fetchone()[0],0)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
