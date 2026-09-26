"""Exact provider replay for the repaired location flow; retain the preference miss."""
import asyncio,copy,json,tempfile,unittest
from pathlib import Path
from memory_store import MemoryStore
from memory_evidence_writer import EvidenceWriter
from ask import instructions,input_fits,references

ROOT=Path(__file__).parent/'fixtures/subject-continuity'

class SubjectContinuityTests(unittest.IsolatedAsyncioTestCase):
    async def test_recorded_location_correction_with_unchanged_abstention(self):
        recorded=json.loads((ROOT/'calls.json').read_text());index=0;outer=self
        class Models:
            async def consume(self,role,request):
                nonlocal index
                item=recorded[index];index+=1
                outer.assertEqual((role,request),(item['role'],item['request']))
                return copy.deepcopy(item['response'])
            async def extract(self,req):return await self.consume('extract',req)
            async def judge(self,req):return await self.consume('judge',req)
        class Budget:
            def reserve(self,*args):pass
            def finish(self,*args):pass
        sources=[json.loads(c['request']['input']) for c in recorded if c['role']=='extract'
            and c['request'].get('text',{}).get('format',{}).get('name')=='memory_evidence_v2'][:2]
        with tempfile.TemporaryDirectory() as folder:
            store=MemoryStore(Path(folder)/'memory.sqlite');owner=store.owner_for('qa')
            writer=EvidenceWriter(store,Models(),Budget(),chunking=True,semantic_boundaries=True,expiry=True,consolidation=True)
            for s in sources:
                s.pop('origin',None);store.put_source(owner,s);await writer.process_next(owner)
            rows=store.search(owner,historical=True)
            self.assertEqual(sorted(r['state'] for r in rows),['active','superseded'])
            self.assertEqual(len({r['entity_id'] for r in rows}),1)
            self.assertTrue(any('community center' in r['text'] and r['state']=='active' for r in rows))
            self.assertFalse(any('morning' in r['text'] for r in rows)) # Known conservative rejection, not a success.
            self.assertEqual(store.search(owner,unresolved_only=True),[])
            self.assertEqual(index,9)

    def test_current_answer_prompt_matches_real_checks(self):
        rows=[r for r in json.loads((ROOT/'results.json').read_text()) if 'answer' in r]
        self.assertEqual(len(rows),3)
        for row in rows:
            self.assertEqual(instructions(row['data']),row['instructions'])
            self.assertTrue(input_fits(row['data']))
            self.assertTrue(references(row['answer'],row['data']['sources']))
        self.assertIn('identified as you',rows[1]['answer'])
        self.assertNotIn('yours',rows[0]['answer'])
