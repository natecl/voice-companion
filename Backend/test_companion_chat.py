import json
from pathlib import Path
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from admission import Rejected
from companion_chat import CompanionChat
from memory_store import MemoryStore
from memory_context import select
from test_memory import source,candidate


class CompanionChatTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/'memory.sqlite'
        self.store=MemoryStore(self.path,clock=lambda:300.)
        self.owner=self.store.owner_for('qa');self.other=self.store.owner_for('other')
        self.chat=CompanionChat(self.store)

    def evidence(self):
        self.store.put_source(self.owner,source('s',text='Maya enjoys swimming.'))
        return select(self.store,self.owner,[dict(session_id='s',revision=1,passage_id='p1')])

    def turn(self,key,text='Hello',answer='Hello back',**kwargs):
        self.chat.start(self.owner,key,text);self.chat.complete(self.owner,key,answer,**kwargs)

    def test_one_main_reopen_owner_isolation_and_idempotency(self):
        main=self.chat.main(self.owner)
        self.assertEqual(self.chat.main(self.owner),main)
        self.assertNotEqual(self.chat.main(self.other),main)
        with ThreadPoolExecutor(2) as pool:
            results=list(pool.map(lambda _:self.chat.start(self.owner,'q1','Hello'),range(2)))
        self.assertEqual(sum(row['created'] for row in results),1)
        with self.assertRaisesRegex(Rejected,'chat_busy'):self.chat.start(self.owner,'q2','Another question')
        with self.assertRaisesRegex(Rejected,'question_id_conflict'):self.chat.start(self.owner,'q1','Changed')
        self.chat.complete(self.owner,'q1','Hello back')
        reopened=CompanionChat(MemoryStore(self.path))
        self.assertEqual(reopened.main(self.owner),main)
        self.assertEqual(reopened.page(self.owner)['turns'][0]['answer'],'Hello back')
        self.assertFalse(reopened.start(self.owner,'q1','Hello')['created'])
        self.assertEqual(reopened.page(self.other)['turns'],[])
        with self.assertRaisesRegex(Rejected,'chat_turn_not_pending'):reopened.complete(self.other,'q1','stolen')

    def test_failure_remains_terminal_without_automatic_paid_retry(self):
        self.chat.start(self.owner,'q','Hello')
        reopened=CompanionChat(MemoryStore(self.path))
        self.assertEqual(reopened.start(self.owner,'q','Hello')['turn']['state'],'pending')
        reopened.fail(self.owner,'q')
        self.assertEqual(reopened.start(self.owner,'q','Hello')['turn']['state'],'failed')
        with self.assertRaisesRegex(Rejected,'chat_turn_not_pending'):reopened.complete(self.owner,'q','late reply')
        self.assertEqual(reopened.context(self.owner)['turns'],[])
        reopened.start(self.owner,'new','A new request')

    def test_deletion_preserves_answers_and_removes_unavailable_citations(self):
        packet=self.evidence();citation=dict(id='m1',source=packet['items'][0])
        self.turn('a','What sport?','Maya enjoys swimming. [[m1]]',packets=[packet],citations=[citation])
        history=self.chat.context(self.owner)
        self.turn('b','Say it briefly','Swimming.',history_ids=history['history_ids'])
        self.store.delete_source(self.owner,'s')
        turns=self.chat.page(self.owner)['turns']
        self.assertEqual([t['state'] for t in turns],['outdated','outdated'])
        self.assertEqual([t['answer'] for t in turns],['Maya enjoys swimming. [[m1]]','Swimming.'])
        self.assertTrue(all(t['citations']==[] for t in turns))
        reopened=CompanionChat(MemoryStore(self.path))
        self.assertEqual(reopened.page(self.owner)['turns'],turns)
        with self.assertRaisesRegex(Rejected,'source_unavailable'):reopened.citation(self.owner,'a','m1')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM companion_dependency').fetchone()[0],0)
        self.assertEqual(self.chat.context(self.owner)['turns'],[])

    def test_stale_packet_and_history_cannot_finish(self):
        packet=self.evidence();self.turn('a',packets=[packet])
        self.chat.start(self.owner,'b','Follow up')
        changed=source('s',text='Maya now enjoys tennis.');changed['revision']=2
        self.store.put_source(self.owner,changed)
        with self.assertRaisesRegex(Rejected,'chat_history_changed'):
            self.chat.complete(self.owner,'b','Swimming.',history_ids=['a'])
        with self.assertRaisesRegex(Rejected,'memory_context_changed'):
            self.chat.complete(self.owner,'b','Swimming.',packets=[packet])
        self.assertEqual(self.chat.page(self.owner)['turns'][-1]['state'],'pending')

    def test_lifecycle_change_invalidates_without_source_revision(self):
        packet=self.evidence()
        self.store.commit_claims(self.store.claim_job(self.owner),[candidate('Maya enjoys swimming.')])
        packet=select(self.store,self.owner,packet['items'])
        self.turn('a',packets=[packet])
        old=self.store.search(self.owner)[0]['id']
        self.store.put_source(self.owner,source('new',text='Maya now enjoys tennis.'))
        self.store.commit_claims(self.store.claim_job(self.owner),[candidate('Maya enjoys tennis.',relation='supersedes',target=old)])
        turn=self.chat.page(self.owner)['turns'][0]
        self.assertEqual(turn['state'],'outdated')
        self.assertEqual(turn['answer'],'Hello back')
        self.assertEqual(self.chat.context(self.owner)['turns'],[])
        self.store.delete_source(self.owner,'s')
        turn=self.chat.page(self.owner)['turns'][0]
        self.assertEqual(turn['state'],'outdated')
        self.assertEqual(turn['answer'],'Hello back')

    def test_citations_must_match_canonical_evidence(self):
        packet=self.evidence();self.chat.start(self.owner,'a','What sport?')
        with self.assertRaisesRegex(Rejected,'invalid_chat_citations'):
            self.chat.complete(self.owner,'a','Swimming [[m1]]',packets=[packet])
        with self.assertRaisesRegex(Rejected,'invalid_chat_evidence'):
            self.chat.complete(self.owner,'a','answer',packets=[dict(packet,owner=self.other)])
        self.chat.complete(self.owner,'a','Swimming [[m1]]',packets=[packet],citations=[dict(id='m1',source=packet['items'][0])])
        self.assertEqual(self.chat.page(self.owner)['turns'][0]['citations'][0]['source']['session_id'],'s')

    def test_bounded_whole_turn_suffix_pagination_and_invalid_boundary(self):
        for i in range(12):self.turn(f'q{i}',answer='answer '*15)
        history=self.chat.context(self.owner,max_turns=3,max_bytes=500)
        self.assertTrue(history['history_limited']);self.assertLessEqual(len(history['turns']),3)
        self.assertEqual(history['history_ids'][-1],'q11')
        self.assertLessEqual(len(json.dumps(history['turns'],ensure_ascii=False).encode()),500)
        page=self.chat.page(self.owner,limit=5);older=self.chat.page(self.owner,before=page['next_before'],limit=5)
        self.assertEqual([t['sequence'] for t in page['turns']],[8,9,10,11,12])
        self.assertEqual([t['sequence'] for t in older['turns']],[3,4,5,6,7])
        self.chat.start(self.owner,'bad','failed');self.chat.fail(self.owner,'bad')
        self.turn('last')
        self.assertEqual(self.chat.context(self.owner)['history_ids'],['last'])

    def test_schema12_migration_preserves_sources_and_tombstones(self):
        self.evidence();self.store.delete_source(self.owner,'deleted')
        with self.store.connect() as db:
            db.executescript('DROP TABLE companion_dependency; DROP TABLE companion_turn; DROP TABLE companion_chat; PRAGMA user_version=12;')
        migrated=MemoryStore(self.path)
        self.assertEqual(migrated.source(self.owner,'s')['passages'][0]['text'],'Maya enjoys swimming.')
        self.assertEqual(migrated.put_source(self.owner,source('deleted'))['status'],'deleted')
        self.assertEqual(CompanionChat(migrated).page(self.owner)['turns'],[])
        with migrated.connect() as db:self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],19)
