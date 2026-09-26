import copy
from pathlib import Path
import tempfile
import unittest
from admission import Rejected
from companion_chat import CompanionChat
from companion_context import assemble,size
from memory_context import select
from memory_store import MemoryStore
from test_memory import source

class CompanionContextTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.store=MemoryStore(Path(temp.name)/'m.sqlite')
        self.owner=self.store.owner_for('a');self.other=self.store.owner_for('b')
        self.chat=CompanionChat(self.store)

    def test_empty_chat_and_continuity_with_canonical_history_evidence(self):
        self.assertEqual(assemble(self.store,self.owner,'Hello')['data']['sources'],[])
        self.store.put_source(self.owner,source('s',text='Maya enjoys swimming.'))
        packet=select(self.store,self.owner,[dict(session_id='s',revision=1,passage_id='p1')])
        self.chat.start(self.owner,'q','What sport?');self.chat.complete(self.owner,'q','Swimming.',packets=[packet])
        result=assemble(self.store,self.owner,'What about her hobby?')
        self.assertEqual(result['history_ids'],['q'])
        self.assertEqual(result['data']['sources'][0]['text'],'Maya enjoys swimming.')
        self.store.delete_source(self.owner,'s')
        result=assemble(self.store,self.owner,'What about her hobby?')
        self.assertEqual(result['history_ids'],[]);self.assertEqual(result['data']['sources'],[])

    def test_attachment_owner_revision_deleted_and_memory_opt_out(self):
        self.store.put_source(self.owner,source('s'))
        ref=dict(session_id='s',revision=1)
        with self.assertRaisesRegex(Rejected,'attachment_unavailable'):assemble(self.store,self.other,'What happened?',attachment=ref)
        with self.assertRaisesRegex(Rejected,'attachment_changed'):assemble(self.store,self.owner,'What happened?',attachment=dict(ref,revision=2))
        packet=select(self.store,self.owner,[dict(session_id='s',revision=1,passage_id='p1')])
        with self.assertRaisesRegex(Rejected,'memory_disabled'):assemble(self.store,self.owner,'Hello',past=packet)
        result=assemble(self.store,self.owner,'What happened?',attachment=ref,past=packet,memory_status='available')
        self.assertEqual(len(result['data']['sources']),1)
        self.assertEqual(result['data']['source_groups']['attached'],result['data']['source_groups']['past'])
        self.store.delete_source(self.owner,'s')
        with self.assertRaisesRegex(Rejected,'attachment_unavailable'):assemble(self.store,self.owner,'What happened?',attachment=ref)

    def test_long_attachment_finds_late_fact_and_exposes_partial_coverage(self):
        text=('The seminar discussed routine topics. '*300)+' The access code is cobalt.'
        self.store.put_source(self.owner,source('s',text=text))
        result=assemble(self.store,self.owner,'What is the access code?',attachment=dict(session_id='s',revision=1))
        self.assertEqual(result['data']['recordings']['attached']['coverage'],'partial')
        self.assertTrue(any('cobalt' in item['text'] for item in result['data']['sources']))
        for item in result['data']['sources']:
            self.assertEqual(item['text'],text[item['text_start']:item['text_end']])
        no_match=assemble(self.store,self.owner,'Where is Saturn?',attachment=dict(session_id='s',revision=1))
        self.assertEqual(no_match['data']['sources'],[])
        self.assertEqual(no_match['data']['recordings']['attached']['coverage'],'partial_no_match')

    def test_live_snapshot_is_fixed_separate_and_does_not_commit_memory(self):
        self.store.put_source(self.owner,source('past',text='Maya enjoyed swimming last year.'))
        live=source('current',text='Maya now enjoys tennis.');live['completed']=False
        original=copy.deepcopy(live)
        result=assemble(self.store,self.owner,'What changed?',attachment=dict(session_id='past',revision=1),live=live)
        live['passages'][0]['text']='Later words must not enter the answer.'
        self.assertEqual(result['live_snapshot'],original)
        self.assertIsNone(self.store.source(self.owner,'current'))
        self.assertNotEqual(result['data']['source_groups']['live'],result['data']['source_groups']['attached'])
        self.assertEqual(result['data']['recordings']['live']['cutoff_seconds'],2.)
        self.assertTrue(all(item['session_id']!='current' for packet in result['packets'] for item in packet['items']))

    def test_whole_history_trim_and_explicit_overflow(self):
        for i in range(8):
            self.chat.start(self.owner,f'q{i}','Hello');self.chat.complete(self.owner,f'q{i}','Hello '*300)
        result=assemble(self.store,self.owner,'Hello')
        self.assertTrue(result['data']['history_limited']);self.assertLessEqual(size(result['data']),12000)
        with self.assertRaisesRegex(Rejected,'invalid_question'):assemble(self.store,self.owner,'x'*1001)

    def test_explicit_no_past_precedes_chat_read_and_citations_are_remapped(self):
        from unittest.mock import patch
        with patch.object(CompanionChat,'context',side_effect=AssertionError('must not read history')):
            result=assemble(self.store,self.owner,"Only use this transcript: what happened?")
            explicit=assemble(self.store,self.owner,'What happened?',use_memory=False)
            self.assertEqual(explicit['data']['history'],[])
        self.assertEqual(result['data']['memory_status'],'disabled')
        self.store.put_source(self.owner,source('s',text='Maya enjoys swimming.'))
        packet=select(self.store,self.owner,[dict(session_id='s',revision=1,passage_id='p1')])
        self.chat.start(self.owner,'q','What sport?')
        self.chat.complete(self.owner,'q','Swimming [[m1]]',packets=[packet],citations=[dict(id='m1',source=packet['items'][0])])
        result=assemble(self.store,self.owner,'What about her hobby?')
        self.assertEqual(result['data']['history'][0]['assistant'],'Swimming [[p1]]')
        self.assertEqual(result['data']['sources'][0]['id'],'p1')
        self.assertEqual(self.chat.page(self.owner)['turns'][0]['answer'],'Swimming [[m1]]')
