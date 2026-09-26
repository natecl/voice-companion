import unittest
import test_memory_evidence_writer as writer_fixtures
from test_memory_learning import answers
from memory_store import MemoryStore


class ConsolidationTests(unittest.IsolatedAsyncioTestCase):
    setUp=writer_fixtures.EvidenceWriterTests.setUp
    run_source=writer_fixtures.EvidenceWriterTests.run_source

    async def pair(self):
        self.writer.consolidation=True
        normal=self.writer.models.judge
        async def judge(request):
            if any('duplicate' in q['criteria'] for q in request['questions'].values()):
                return dict(data=answers(request,{key:'duplicate' for key in request['questions']}),usage={})
            return await normal(request)
        await self.run_source('first',[writer_fixtures.proposal('My daughter Maya enjoys swimming.')])
        self.writer.models.judge=judge
        await self.run_source('second',[writer_fixtures.proposal('My daughter Maya enjoys swimming.')])
        self.writer.models.judge=normal

    async def test_one_memory_two_sources_reopen_and_delete_second(self):
        await self.pair()
        rows=self.store.search(self.owner)
        self.assertEqual(len(rows),1)
        self.assertEqual(len(rows[0]['sources']),2)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_fact_evidence').fetchone()[0],2)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        self.store=MemoryStore(self.store.path,clock=lambda:300.)
        self.store.delete_source(self.owner,'second')
        rows=self.store.search(self.owner)
        self.assertEqual(len(rows),1)
        self.assertEqual([r['session'] for r in rows[0]['sources']],['first'])
        self.store.delete_source(self.owner,'first')
        self.assertEqual(self.store.search(self.owner,historical=True),[])

    async def test_deleting_identity_anchor_preserves_evidence_as_uncertain(self):
        await self.pair()
        self.store.delete_source(self.owner,'first')
        self.assertEqual(self.store.search(self.owner),[])
        rows=self.store.search(self.owner,unresolved_only=True)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['identity_status'],'unresolved')
        self.assertEqual([r['session'] for r in rows[0]['sources']],['second'])

    async def test_correction_replaces_consolidated_fact_once(self):
        await self.pair()
        await self.run_source('correction',[writer_fixtures.proposal('My daughter Maya now enjoys tennis instead of swimming.','correction')])
        rows=self.store.search(self.owner,historical=True)
        self.assertEqual(sorted(r['state'] for r in rows),['active','superseded'])
        self.assertEqual(len(next(r for r in rows if r['state']=='superseded')['sources']),2)

    async def test_added_interest_is_not_consolidated(self):
        self.writer.consolidation=True
        await self.run_source('first',[writer_fixtures.proposal('My daughter Maya enjoys swimming.')])
        await self.run_source('second',[writer_fixtures.proposal('My daughter Maya enjoys tennis.')])
        self.assertEqual(len(self.store.search(self.owner)),2)

    async def test_schema8_migration_preserves_existing_evidence(self):
        await self.run_source('first',[writer_fixtures.proposal('My daughter Maya enjoys swimming.')])
        with self.store.connect() as db:
            before=[tuple(r) for r in db.execute('SELECT * FROM memory_fact_evidence')]
            db.executescript('''BEGIN;
                ALTER TABLE memory_fact_evidence RENAME TO evidence9;
                DROP INDEX fact_evidence_source;
                CREATE TABLE memory_fact_evidence(claim TEXT PRIMARY KEY REFERENCES claim(id),owner TEXT NOT NULL,
                    session TEXT NOT NULL,revision INTEGER NOT NULL,proposal TEXT NOT NULL,judgments TEXT NOT NULL,
                    FOREIGN KEY(owner,session) REFERENCES source(owner,session));
                INSERT INTO memory_fact_evidence SELECT * FROM evidence9;
                DROP TABLE evidence9;
                CREATE INDEX fact_evidence_source ON memory_fact_evidence(owner,session);
                DROP TABLE IF EXISTS memory_embedding; DROP TABLE IF EXISTS memory_passage_index; PRAGMA user_version=8; COMMIT;''')
        reopened=MemoryStore(self.store.path,clock=lambda:300.)
        with reopened.connect() as db:
            self.assertEqual([tuple(r) for r in db.execute('SELECT * FROM memory_fact_evidence')],before)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],13)
        self.assertIsNone(reopened.claim_job(self.owner))

    async def test_exact_live_consolidation_replay(self):
        import copy
        import json
        from pathlib import Path
        directory=Path(__file__).parent/'fixtures/memory_consolidation/recorded'
        artifact=json.loads((directory/'result.json').read_text())
        calls=json.loads((directory/'provider-calls.json').read_text());index=0
        self.store.clock=lambda:1790424100.
        self.writer.luna_identity=True;self.writer.consolidation=True
        async def consume(role,request):
            nonlocal index
            expected=calls[index];index+=1
            self.assertEqual((role,request),(expected['role'],expected['request']))
            return copy.deepcopy(expected['response'])
        async def extract(req):return await consume('extract',req)
        async def judge(req):return await consume('judge',req)
        self.writer.models.extract=extract;self.writer.models.judge=judge
        for i,source in enumerate(artifact['sources']):
            self.store.put_source(self.owner,source)
            await self.writer.process_next(self.owner)
            rows=self.store.search(self.owner,historical=True)
            expected=artifact['snapshots'][i]['rows']
            self.assertEqual(sorted((r['text'],r['state'],len(r['sources'])) for r in rows),
                             sorted((r['text'],r['state'],len(r['sources'])) for r in expected))
            self.assertEqual(self.store.search(self.owner,unresolved_only=True),[])
        self.assertEqual(index,len(calls))
