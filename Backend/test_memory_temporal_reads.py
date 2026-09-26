"""Real SQLite validity projections; no inference or wall-clock sleeps."""
from pathlib import Path
import tempfile
import unittest

from admission import Rejected
from memory_store import MemoryStore
from memory_recall import MemoryRecall
from test_memory import source, candidate
from test_memory_recall import Budget, Judge
from test_ask import QUESTION


class TemporalReads(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'memory.sqlite'
        self.now = 150.
        self.store = MemoryStore(self.path, clock=lambda: self.now)
        self.owner = self.store.owner_for('credential')

    def write(self, **bounds):
        original = source()
        self.store.put_source(self.owner, original)
        claim = candidate()
        claim.update(bounds)
        self.store.commit_claims(self.store.claim_job(self.owner), [claim])
        return original

    def states(self):
        return [self.store.search(self.owner, historical=True)[0]['state'],
                self.store.evidence(self.owner, 'session-a')['passages'][0]['claims'][0]['state'],
                self.store.recall_snapshot(self.owner)[0]['passages'][0]['claims'][0]['state']]

    async def test_all_reads_agree_at_start_and_end_without_maintenance(self):
        original = self.write(valid_from=200., valid_until=300.)
        for now, expected in [(199.999, 'future'), (200., 'active'), (299.999, 'active'), (300., 'expired')]:
            self.now = now
            self.assertEqual(self.states(), [expected] * 3)
            self.assertEqual(bool(self.store.search(self.owner)), expected == 'active')
            self.assertEqual(self.store.source(self.owner, 'session-a'), original)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT state FROM claim').fetchone()[0], 'active')
        self.store.maintain()
        self.assertEqual(self.states(), ['expired'] * 3)
        self.store = MemoryStore(self.path, clock=lambda: self.now)
        self.assertEqual(self.states(), ['expired'] * 3)
        self.assertEqual(self.store.source(self.owner, 'session-a'), original)

    async def test_future_cannot_enter_current_recall_even_if_judge_says_relevant(self):
        self.write(valid_from=200.)
        recall = MemoryRecall(self.store, Judge(), Budget())
        result = await recall.prepare('credential', QUESTION)
        self.assertEqual(result['sources'], [])
        self.now = 200.
        result = await recall.prepare('credential', QUESTION)
        self.assertEqual(len(result['sources']), 1)

    async def test_expiry_invalidates_inflight_context_without_maintenance(self):
        self.write(valid_until=200.)
        recall = MemoryRecall(self.store, Judge(), Budget())
        manifest = await recall.prepare('credential', QUESTION)
        self.assertEqual(len(manifest['sources']), 1)
        self.now = 199.
        await recall.validate(manifest)
        self.now = 200.
        with self.assertRaisesRegex(Rejected, 'memory_context_changed'):
            await recall.validate(manifest)

    async def test_stable_fact_does_not_decay_and_deletion_removes_evidence(self):
        self.write()
        self.now = 10**10
        self.store.maintain()
        self.assertEqual(self.states(), ['active'] * 3)
        other = self.store.owner_for('other')
        self.assertEqual(self.store.search(other, historical=True), [])
        self.assertIsNone(self.store.evidence(other, 'session-a'))
        self.store.delete_source(self.owner, 'session-a')
        self.assertEqual(self.store.search(self.owner, historical=True), [])
        self.assertEqual(self.store.recall_snapshot(self.owner), [])
        self.assertIsNone(self.store.evidence(self.owner, 'session-a'))

    async def test_retired_and_uncertain_states_are_not_promoted_by_time(self):
        for state in ['superseded', 'unresolved', 'invalid', 'expired']:
            item = dict(state=state, valid_from=200., valid_until=300.)
            self.store._qualify_time(item, 250.)
            self.assertEqual(item['state'], state)
