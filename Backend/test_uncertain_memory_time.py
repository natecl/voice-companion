"""Saved phone responses through the real writer, storage, and retained recall."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from memory_models import fingerprint
from memory_store import MemoryStore
from memory_evidence_writer import EvidenceWriter
import memory_hybrid
import memory_context

FIXTURE=Path(__file__).parent/'fixtures/uncertain-time/cedar.json'

class UncertainTimeTests(unittest.IsolatedAsyncioTestCase):
    async def run_fixture(self, mutate=None, verified_mutate=None):
        fixture=json.loads(FIXTURE.read_text())
        if mutate:mutate(fixture)
        responses={r['request_hash']:r['response'] for r in fixture['results']}
        calls=[]
        class Models:
            async def call(self,request):
                key=fingerprint(request)
                if key not in responses:raise AssertionError('Unrecorded request; network forbidden')
                calls.append(key)
                return copy.deepcopy(responses[key])
            extract=call
            judge=call
        class Budget:
            def reserve(self,*args):pass
            def finish(self,*args):pass
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        path=Path(folder.name)/'memory.sqlite'
        store=MemoryStore(path,retain_recording_memories=True);owner=store.owner_for('test')
        store.put_source(owner,fixture['source'])
        writer=EvidenceWriter(store,Models(),Budget(),chunking=True,semantic_boundaries=True,
            expiry=True,consolidation=True,independent_source_verification=True)
        if verified_mutate:
            original=writer.extract_verified
            async def changed(*args,**kwargs):
                parts=await original(*args,**kwargs)
                verified_mutate(parts)
                return parts
            writer.extract_verified=changed
        result=await writer.process_next(owner)
        self.assertEqual(len(calls),4)
        return store,owner,fixture['source'],result

    async def test_phone_failure_retains_unresolved_through_delete_reopen_and_context(self):
        store,owner,source,result=await self.run_fixture()
        self.assertEqual(result['accepted'],1)
        self.assertEqual(store.search(owner),[])
        with store.connect() as db:
            claim=dict(db.execute('SELECT * FROM claim').fetchone())
            evidence=dict(db.execute('SELECT * FROM memory_fact_evidence').fetchone())
        self.assertEqual(claim['state'],'unresolved')
        self.assertIsNone(claim['valid_from']);self.assertIsNone(claim['valid_until'])
        self.assertNotEqual(claim['subject'],'user')
        checks=json.loads(evidence['judgments'])['source']['time']
        self.assertFalse(checks['accepted']);self.assertEqual(checks['probability'],.59)
        self.assertEqual(checks['proposed_time']['status'],'current')
        self.assertEqual(checks['disposition'],'retain_time_unresolved')
        self.assertEqual(json.loads(evidence['proposal'])['time'],dict(status='uncertain',expression=None))
        store.delete_source(owner,source['session_id'])
        reopened=MemoryStore(store.path)
        self.assertIsNone(reopened.source(owner,source['session_id']))
        packet=memory_hybrid.retrieve(reopened,owner,'Project Cedar garden pavilion')['packet']
        self.assertTrue(memory_context.valid(reopened,owner,packet))
        self.assertEqual(len(packet['items']),1)
        item=packet['items'][0]
        self.assertEqual(item['evidence_type'],'retained_memory')
        self.assertFalse(item['source_available'])
        self.assertEqual(item['lifecycle'][0]['state'],'unresolved')
        self.assertEqual(item['lifecycle'][0]['temporal_evidence']['reported_status'],'uncertain')
        self.assertEqual(memory_hybrid.retrieve(reopened,reopened.owner_for('other'),'Cedar')['packet']['items'],[])

    async def test_temporal_fallback_does_not_rescue_unsupported_fact(self):
        def mutate(fixture):
            row=next(r for r in fixture['results'] if ':support:' in r['stage'])
            row['response']['data']['case_0']['verdict']='contradicted'
        store,owner,_,result=await self.run_fixture(mutate)
        self.assertEqual(result['accepted'],0)
        self.assertEqual(store.search(owner,unresolved_only=True),[])

    async def test_temporal_fallback_does_not_rescue_unverified_modality(self):
        def mutate(fixture):
            row=next(r for r in fixture['results'] if ':metadata:' in r['stage'])
            a=row['response']['data']['answers']['modality_0']
            a['choice']='hypothetical'
            a['probabilities']={k:float(k=='hypothetical') for k in a['probabilities']}
        store,owner,_,result=await self.run_fixture(mutate)
        self.assertEqual(result['accepted'],0)
        self.assertEqual(store.search(owner,unresolved_only=True),[])

    async def test_confident_temporal_disagreement_is_unresolved_not_reclassified(self):
        def mutate(fixture):
            row=next(r for r in fixture['results'] if ':metadata:' in r['stage'])
            a=row['response']['data']['answers']['time_0']
            a['choice']='future'
            a['probabilities']={k:float(k=='future') for k in a['probabilities']}
        store,owner,_,result=await self.run_fixture(mutate)
        self.assertEqual(result['accepted'],1)
        self.assertEqual(store.search(owner),[])
        self.assertEqual(len(store.search(owner,unresolved_only=True)),1)

    async def test_explicit_unverified_date_is_not_rescued(self):
        def change(parts):
            parts[0]['proposal']['time']['expression']='tomorrow'
        store,owner,_,result=await self.run_fixture(verified_mutate=change)
        self.assertEqual(result['accepted'],0)
        self.assertEqual(store.search(owner,unresolved_only=True),[])
