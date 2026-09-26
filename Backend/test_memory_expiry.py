from datetime import datetime
import unittest
import memory_expiry
import test_memory_atomic as atomic_fixtures
from test_memory_time import epoch


class ExpiryStorage(unittest.TestCase):
    setUp = atomic_fixtures.AtomicTests.setUp
    prepare = atomic_fixtures.AtomicTests.prepare
    def test_actual_atomic_expiry_preserves_source(self):
        job,item=self.prepare('temporary','My daughter Maya is staying in Boston through 2026-09-30.')
        # Existing atomic fixture has epoch source time in UTC.
        item['proposal']['time']['expression']='through 2026-09-30'
        item['expiry']=dict(version=memory_expiry.VERSION,accepted=True,label='ends',probabilities={'ends':1.},confidence=1.)
        import memory_atomic
        memory_atomic.commit(self.store,job,[item])
        rows=self.store.search(self.owner)
        self.assertEqual(rows[0]['valid_until'],epoch('2026-10-01T00:00:00+00:00'))
        self.store.clock=lambda:epoch('2026-10-01T00:00:00+00:00')
        self.assertEqual(self.store.search(self.owner),[])
        self.assertEqual(self.store.search(self.owner,historical=True)[0]['state'],'expired')
        self.assertIsNotNone(self.store.source(self.owner,'temporary'))


class ExpiryBoundary(unittest.TestCase):
    def test_date_is_inclusive_and_dst_aware(self):
        source=dict(captured_at=epoch('2026-03-07T12:00:00-05:00'),timezone='America/New_York')
        proposal=dict(basis='stated',time=dict(status='current',expression='through 2026-03-08'))
        self.assertEqual(memory_expiry.boundary(source,proposal),epoch('2026-03-09T00:00:00-04:00'))
        for expression in ['until Friday','through September 30','on 2026-03-08','not through 2026-03-08','through 2026-02-30']:
            proposal['time']['expression']=expression
            self.assertIsNone(memory_expiry.boundary(source,proposal))
        proposal['time']['expression']='through 2026-03-08';proposal['basis']='tentative'
        self.assertIsNone(memory_expiry.boundary(source,proposal))
        proposal['basis']='stated';proposal['time']['status']='future'
        self.assertIsNone(memory_expiry.boundary(source,proposal))


class ExpiryReplay(unittest.IsolatedAsyncioTestCase):
    async def test_exact_live_writer_replay_and_late_deletion(self):
        import copy
        import json
        import tempfile
        from pathlib import Path
        from admission import Rejected
        from memory_store import MemoryStore
        from memory_evidence_writer import EvidenceWriter
        directory=Path(__file__).parent/'fixtures/memory_expiry/recorded'
        artifact=json.loads((directory/'writer.json').read_text())
        calls=json.loads((directory/'provider-calls.json').read_text())
        for delete in (False,True):
            with self.subTest(delete=delete), tempfile.TemporaryDirectory() as folder:
                store=MemoryStore(Path(folder)/'memory.sqlite',personal_learning=True,clock=lambda:1790424001.)
                owner=store.owner_for('fixture');original=artifact['source'];store.put_source(owner,original)
                index=0
                outer=self
                class Models:
                    async def consume(self,role,request):
                        nonlocal index
                        expected=calls[index];index+=1
                        outer.assertEqual((role,request),(expected['role'],expected['request']))
                        if delete and index==len(calls):store.delete_source(owner,original['session_id'])
                        return copy.deepcopy(expected['response'])
                    async def extract(self,request):return await self.consume('extract',request)
                    async def judge(self,request):return await self.consume('judge',request)
                class Budget:
                    def reserve(self,*args):pass
                    def finish(self,*args):pass
                writer=EvidenceWriter(store,Models(),Budget(),expiry=True)
                if delete:
                    with self.assertRaisesRegex(Rejected,'stale_job'):await writer.process_next(owner)
                    self.assertEqual(store.search(owner,historical=True),[])
                else:
                    await writer.process_next(owner)
                    end=artifact['rows'][0]['valid_until']
                    self.assertEqual(store.search(owner)[0]['valid_until'],end)
                    store.clock=lambda:end
                    self.assertEqual(store.search(owner),[])
                    self.assertEqual(store.search(owner,historical=True)[0]['state'],'expired')
                    self.assertEqual(store.source(owner,original['session_id']),original)
                self.assertEqual(index,len(calls))

    async def test_recorded_role_decisions_keep_negative_claims_unexpired(self):
        import json
        from pathlib import Path
        from evaluate_memory_expiry import fixture,source
        directory=Path(__file__).parent/'fixtures/memory_expiry'
        cases=json.loads((directory/'cases.json').read_text())
        artifact=json.loads((directory/'recorded/role.json').read_text())
        for case in cases:
            proposal=fixture(case);original=source(case['text'])
            req=memory_expiry.request(original,proposal)
            response=dict(artifact['response']['data'],answers={'expiry':artifact['response']['data']['answers'][case['id']]})
            proof=memory_expiry.decision(response,req)
            self.assertEqual(proof['accepted'],case['accept'])
            self.assertEqual(memory_expiry.verified_boundary(original,proposal,proof) is not None,case['accept'])
