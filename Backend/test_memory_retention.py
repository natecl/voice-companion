"""Real storage/writer/recall composition, exact saved provider responses only."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from admission import Rejected
from memory_store import MemoryStore
from memory_evidence_writer import EvidenceWriter
from memory_models import fingerprint
from companion_chat import CompanionChat
import companion_context
import memory_candidates
import memory_context
import memory_hybrid
import memory_related

ROOT=Path(__file__).parent/'fixtures'

class RecordedModels:
    def __init__(self):
        calls=[]
        for name in ('subject-continuity/calls.json','source-verification/initial-calls.json','source-verification/verified-calls.json'):
            calls.extend(json.loads((ROOT/name).read_text()))
        self.responses={fingerprint(c['request']):c['response'] for c in calls}
    async def call(self,request):
        key=fingerprint(request)
        if key not in self.responses:
            raise AssertionError('No exact saved response; network is forbidden: '+request.get('text',{}).get('format',{}).get('name','judgment'))
        return copy.deepcopy(self.responses[key])
    extract=call
    judge=call

class ReplayBudget:
    def reserve(self,*args):pass
    def finish(self,*args):pass

class RetentionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.path=Path(self.folder.name)/'memory.sqlite'
        self.store=MemoryStore(self.path,retain_recording_memories=True)
        self.owner=self.store.owner_for('owner')
        self.writer=EvidenceWriter(self.store,RecordedModels(),ReplayBudget(),chunking=True,semantic_boundaries=True,
            expiry=True,consolidation=True,independent_source_verification=True)
        calls=json.loads((ROOT/'subject-continuity/calls.json').read_text())
        self.sources=[json.loads(calls[i]['request']['input']) for i in (0,3)]
        for source in self.sources:source.pop('origin',None)

    async def learn(self,index):
        self.store.put_source(self.owner,self.sources[index]);await self.writer.process_next(self.owner)

    def delete(self,index):self.store.delete_source(self.owner,self.sources[index]['session_id'])

    def check_correction(self):
        rows=self.store.search(self.owner,historical=True)
        self.assertEqual(sorted(r['state'] for r in rows),['active','active','superseded'])
        self.assertTrue(any('community center' in r['text'] and r['state']=='active' for r in rows))
        self.assertTrue(any('library' in r['text'] and r['state']=='superseded' for r in rows))
        self.assertTrue(all(r['subject']!='user' and not r['profile_link'] for r in rows))
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM memory_correction WHERE state='active'").fetchone()[0],1)

    async def test_delete_correction_first_preserves_correction_and_recall(self):
        await self.learn(0);await self.learn(1)
        before=self.store.search(self.owner,historical=True)
        packet=memory_hybrid.retrieve(self.store,self.owner,'Juniper library')['packet']
        self.delete(1);self.check_correction()
        expanded=memory_related.expand(self.store,self.owner,memory_hybrid.retrieve(self.store,self.owner,'Juniper library')['packet'])
        self.assertTrue(any(i['evidence_type']=='retained_memory' and 'community center' in i['text'] for i in expanded['items']))
        self.delete(0);self.delete(1);self.check_correction()
        self.assertFalse(memory_context.valid(self.store,self.owner,packet))
        self.assertEqual(before,self.store.search(self.owner,historical=True))
        reopened=MemoryStore(self.path) # feature off never destroys retained knowledge
        self.assertEqual(before,reopened.search(self.owner,historical=True))
        for source in self.sources:
            self.assertIsNone(reopened.source(self.owner,source['session_id']))
            self.assertEqual(reopened.put_source(self.owner,source)['status'],'deleted')
        with reopened.connect() as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            for table in ('memory_embedding','memory_passage_index','memory_chunk','job_result','companion_snapshot'):
                self.assertEqual(db.execute('SELECT count(*) FROM '+table).fetchone()[0],0,table)
            self.assertFalse(db.execute('SELECT 1 FROM source WHERE payload IS NOT NULL').fetchone())
        packet=memory_related.expand(reopened,self.owner,memory_hybrid.retrieve(reopened,self.owner,'Juniper meetings')['packet'])
        self.assertTrue(memory_context.valid(reopened,self.owner,packet))
        self.assertTrue(all(i['evidence_type']=='retained_memory' and i['source_available'] is False for i in packet['items']))
        other=reopened.owner_for('other')
        self.assertEqual(memory_hybrid.retrieve(reopened,other,'Juniper')['packet']['items'],[])
        self.assertFalse(memory_context.valid(reopened,other,packet))

    async def test_correction_after_original_deleted_uses_exact_saved_writer_responses(self):
        await self.learn(0);self.delete(0)
        await self.learn(1);self.check_correction()
        self.delete(1);self.check_correction()

    async def test_saved_answer_reopens_with_retained_label_and_no_source_endpoint(self):
        await self.learn(0);await self.learn(1);self.delete(0);self.delete(1)
        packet=memory_related.expand(self.store,self.owner,memory_hybrid.retrieve(self.store,self.owner,'Juniper community center')['packet'])
        context=companion_context.assemble(self.store,self.owner,'Where does Juniper meet?',past=packet,memory_status='available')
        selected=next(i for i in context['data']['sources'] if 'community center' in i['text'])
        chat=CompanionChat(self.store);chat.start(self.owner,'question','Where does Juniper meet?')
        # This is an injected answer to exercise storage/citation contracts, not model quality evidence.
        chat.complete(self.owner,'question','Project Juniper meets at the community center. [['+selected['id']+']]',
            packets=context['packets'],citations=[dict(id=selected['id'],source=selected)])
        self.delete(0);self.delete(1)
        page=CompanionChat(MemoryStore(self.path)).page(self.owner)
        turn=page['turns'][0];self.assertEqual(turn['state'],'complete')
        self.assertIn('retained_claim_id',turn['citations'][0]['source'])
        with self.assertRaisesRegex(Rejected,'source_unavailable'):chat.citation(self.owner,'question',selected['id'])
        followup=companion_context.assemble(self.store,self.owner,'And where?',memory_status='no_match')
        self.assertEqual(len(followup['data']['history']),1)
        self.assertTrue(followup['data']['source_groups']['history_evidence'])

    async def test_revision_still_invalidates_and_does_not_create_retained_memory(self):
        await self.learn(0)
        revised=copy.deepcopy(self.sources[0]);revised['revision']+=1
        self.store.put_source(self.owner,revised)
        self.assertEqual(self.store.search(self.owner,historical=True),[])
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM retained_recording').fetchone()[0],0)

    async def test_unlearned_deletion_never_creates_memory_or_resumes_work(self):
        self.store.put_source(self.owner,self.sources[0]);job=self.store.claim_job(self.owner)
        self.delete(0)
        self.assertEqual(memory_hybrid.retrieve(self.store,self.owner,'Juniper')['packet']['items'],[])
        with self.assertRaisesRegex(Rejected,'stale_job'):self.store.chunk_plan(job)

    async def test_inflight_original_answer_cannot_commit_after_delete(self):
        await self.learn(0)
        packet=memory_hybrid.retrieve(self.store,self.owner,'Juniper')['packet']
        chat=CompanionChat(self.store);chat.start(self.owner,'pending','Where?')
        self.delete(0)
        with self.assertRaisesRegex(Rejected,'memory_context_changed'):
            chat.complete(self.owner,'pending','The library.',packets=[packet])

    async def test_retained_packet_retires_after_new_correction(self):
        await self.learn(0);self.delete(0)
        packet=memory_hybrid.retrieve(self.store,self.owner,'Juniper library')['packet']
        self.assertTrue(memory_context.valid(self.store,self.owner,packet))
        await self.learn(1)
        self.assertFalse(memory_context.valid(self.store,self.owner,packet))
        self.check_correction()

    async def test_future_expired_and_unresolved_states_survive_delete(self):
        await self.learn(0)
        rows=self.store.search(self.owner,historical=True)
        with self.store.transaction() as db:
            db.execute('UPDATE claim SET valid_from=? WHERE id=?',(self.store.clock()+1000,rows[0]['id']))
            db.execute('UPDATE claim SET valid_until=? WHERE id=?',(self.store.clock()-1000,rows[1]['id']))
        self.delete(0)
        packet=memory_hybrid.retrieve(self.store,self.owner,'Juniper')['packet']
        self.assertEqual({i['lifecycle'][0]['state'] for i in packet['items']},{'future','expired'})
        with self.store.transaction() as db:db.execute("UPDATE claim SET state='unresolved' WHERE owner=?",(self.owner,))
        self.assertFalse(memory_context.valid(self.store,self.owner,packet))
        packet=memory_hybrid.retrieve(self.store,self.owner,'Juniper')['packet']
        self.assertEqual({i['lifecycle'][0]['state'] for i in packet['items']},{'unresolved'})

    async def test_unrelated_transcript_text_is_not_retained(self):
        await self.learn(0)
        # Mimic a long passage that contains unrelated words outside the verified
        # span; the retained representation must come from committed quotes only.
        with self.store.transaction() as db:
            row=db.execute('SELECT payload FROM source WHERE owner=?',(self.owner,)).fetchone()
            source=json.loads(row[0]);source['passages'].append(dict(id='unrelated',text='UNRELATED_SECRET',start=100,duration=1,speakers=[]))
            db.execute('UPDATE source SET payload=? WHERE owner=?',(json.dumps(source),self.owner))
        self.delete(0)
        with self.store.connect() as db:
            self.assertNotIn('UNRELATED_SECRET','\n'.join(db.iterdump()))
        self.assertEqual(memory_hybrid.retrieve(self.store,self.owner,'UNRELATED_SECRET')['packet']['items'],[])

    async def test_no_backfill_and_legacy_personal_note_deletion_unchanged(self):
        await self.learn(0)
        # A legacy personal note remains an explicit-authorship source with the
        # prior deletion contract. This test changes only origin to exercise routing.
        with self.store.transaction() as db:
            row=db.execute('SELECT payload FROM source WHERE owner=?',(self.owner,)).fetchone()
            source=json.loads(row[0]);source['origin']='personal_text'
            db.execute('UPDATE source SET payload=? WHERE owner=?',(json.dumps(source),self.owner))
        self.delete(0)
        self.assertEqual(self.store.search(self.owner,historical=True),[])
        self.assertEqual(memory_hybrid.retrieve(self.store,self.owner,'Juniper')['packet']['items'],[])
        self.store=MemoryStore(self.path,retain_recording_memories=True);self.delete(0)
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM retained_recording').fetchone()[0],0)

    async def test_schema15_upgrade_preserves_live_sources_without_backfill(self):
        await self.learn(0)
        before=self.store.search(self.owner,historical=True)
        with self.store.transaction() as db:
            db.execute('DROP TABLE retained_recording');db.execute('PRAGMA user_version=15')
        migrated=MemoryStore(self.path,retain_recording_memories=True)
        self.assertEqual(before,migrated.search(self.owner,historical=True))
        self.assertIsNotNone(migrated.source(self.owner,self.sources[0]['session_id']))
        with migrated.connect() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],18)
            self.assertEqual(db.execute('SELECT count(*) FROM retained_recording').fetchone()[0],0)


class RecordedRetentionAcceptance(unittest.IsolatedAsyncioTestCase):
    async def test_exact_provider_replay_through_companion_sockets(self):
        from evaluate_retention import run
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'replay'
            await run(path,replay=ROOT/'retained-memory/calls.json')
            summary=json.loads((path/'summary.json').read_text())
            self.assertEqual(summary['new_paid_calls'],0)
            self.assertTrue(summary['reopened'])
            self.assertEqual(summary['answers'],json.loads((ROOT/'retained-memory/summary.json').read_text())['answers'])
