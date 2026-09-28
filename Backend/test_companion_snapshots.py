from pathlib import Path
import tempfile
import unittest
from admission import Rejected
from companion_chat import CompanionChat
from companion_context import assemble
from companion_snapshots import freeze,release
from memory_context import valid
from memory_store import MemoryStore
from test_memory import source

class SnapshotTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.path=Path(folder.name)/'memory.sqlite';self.store=MemoryStore(self.path)
        self.owner=self.store.owner_for('qa');self.chat=CompanionChat(self.store)
        self.live=source('recording',text='Maya enjoys swimming.');self.live['completed']=False

    def saved_answer(self):
        self.chat.start(self.owner,'q','What does Maya enjoy?')
        prepared=assemble(self.store,self.owner,'What does Maya enjoy?',live=self.live)
        item=prepared['data']['sources'][0]
        self.chat.complete(self.owner,'q','Swimming [[p1]]',packets=prepared['packets'],citations=[dict(id='p1',source=item)])
        return prepared

    def test_reopen_append_finalize_followup_then_delete(self):
        prepared=self.saved_answer()
        reopened=MemoryStore(self.path);chat=CompanionChat(reopened)
        complete=source('recording',text='Maya enjoys swimming. She also likes painting.')
        reopened.put_source(self.owner,complete)
        appended=dict(complete,revision=2);appended['passages']=[dict(complete['passages'][0],text=complete['passages'][0]['text']+' More words.')]
        reopened.put_source(self.owner,appended)
        self.assertTrue(valid(reopened,self.owner,prepared['packets'][0]))
        context=assemble(reopened,self.owner,'What else can you tell me?')
        self.assertEqual(context['history_ids'],['q'])
        self.assertEqual(context['data']['sources'][0]['text'],'Maya enjoys swimming.')
        self.assertEqual(context['data']['history'][0]['assistant'],'Swimming [[p1]]')
        chat.start(self.owner,'q2','Say it briefly');chat.complete(self.owner,'q2','Swimming.',history_ids=context['history_ids'])
        reopened.delete_source(self.owner,'recording')
        self.assertTrue(all(t['answer'] is not None for t in chat.page(self.owner)['turns']))
        self.assertFalse(valid(reopened,self.owner,prepared['packets'][0]))
        with reopened.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM companion_snapshot').fetchone()[0],0)
        with self.assertRaisesRegex(Rejected,'live_snapshot_changed'):
            freeze(reopened,self.owner,self.live,prepared['packets'][0]['items'])

    def test_corrected_used_text_scrubs_answer_and_blocks_late_completion(self):
        prepared=self.saved_answer()
        self.store.put_source(self.owner,source('recording',text='Maya enjoys tennis.'))
        self.assertIsNone(self.chat.page(self.owner)['turns'][0]['answer'])
        self.chat.start(self.owner,'late','What sport?')
        with self.assertRaisesRegex(Rejected,'memory_context_changed'):
            self.chat.complete(self.owner,'late','Swimming.',packets=prepared['packets'])

    def test_frozen_owner_isolation_unused_release_and_idempotency(self):
        refs=[dict(session_id='recording',revision=1,passage_id='p1',text_start=0,text_end=len(self.live['passages'][0]['text']))]
        packet=freeze(self.store,self.owner,self.live,refs)
        self.assertEqual(freeze(self.store,self.owner,self.live,refs),packet)
        other=self.store.owner_for('other')
        self.assertFalse(valid(self.store,other,dict(packet,owner=other)))
        release(self.store,self.owner,packet['items'][0]['snapshot_id'])
        self.assertFalse(valid(self.store,self.owner,packet))
        saved=self.saved_answer();release(self.store,self.owner,saved['packets'][0]['items'][0]['snapshot_id'])
        self.assertTrue(valid(self.store,self.owner,saved['packets'][0]))
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM job').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM memory_passage_index').fetchone()[0],0)

    def test_migration_preserves_existing_chat_and_source(self):
        self.store.put_source(self.owner,source('old'))
        self.chat.start(self.owner,'old-question','Hello');self.chat.complete(self.owner,'old-question','Hello back')
        with self.store.connect() as db:db.executescript('DROP TABLE companion_snapshot; PRAGMA user_version=13;')
        migrated=MemoryStore(self.path)
        self.assertEqual(CompanionChat(migrated).page(self.owner)['turns'][0]['answer'],'Hello back')
        self.assertIsNotNone(migrated.source(self.owner,'old'))
