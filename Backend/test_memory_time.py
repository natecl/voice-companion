from datetime import datetime
from pathlib import Path
import tempfile
import unittest

import memory_atomic
import memory_evidence
from memory_store import MemoryStore
from memory_time import resolve
from test_memory import source


def epoch(value):
    return datetime.fromisoformat(value).timestamp()


class CalendarTests(unittest.TestCase):
    def test_source_timezone_not_server_or_read_date(self):
        instant = epoch('2026-09-27T02:00:00+00:00')
        self.assertEqual(resolve('today', instant, 'America/New_York')['date'], '2026-09-26')
        self.assertEqual(resolve('today', instant, 'Asia/Tokyo')['date'], '2026-09-27')
        self.assertEqual(resolve('tomorrow', instant, 'America/New_York')['date'], '2026-09-27')

    def test_calendar_arithmetic_across_dst_leap_and_year_boundaries(self):
        cases = [('2026-03-08T04:30:00-04:00', 'yesterday', '2026-03-07'),
                 ('2026-11-01T23:30:00-05:00', 'tomorrow', '2026-11-02'),
                 ('2028-02-28T12:00:00-05:00', 'tomorrow', '2028-02-29'),
                 ('2026-12-31T23:30:00-05:00', 'tomorrow', '2027-01-01')]
        for anchor, expression, expected in cases:
            with self.subTest(anchor=anchor):
                self.assertEqual(resolve(expression, epoch(anchor), 'America/New_York')['date'], expected)

    def test_ambiguity_and_bad_anchors_never_guess(self):
        for expression in ['until Friday', 'this semester', 'not today', 'today or tomorrow',
                           'tomorrow at 3', '2026-02-30', None]:
            self.assertEqual(resolve(expression, 100., 'UTC')['resolution'], 'unresolved')
        for zone in ['not/a-zone', '../UTC']:
            self.assertEqual(resolve('today', 100., zone)['reason'], 'invalid_anchor')
        self.assertEqual(resolve('today', 1e100, 'UTC')['resolution'], 'unresolved')
        self.assertEqual(resolve('2026-09-27', 100., 'UTC')['date'], '2026-09-27')

    def test_real_atomic_store_preserves_future_plan_across_reads_and_deletion(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'memory.sqlite'
            now = [epoch('2026-09-27T02:00:00+00:00')]
            store = MemoryStore(path, clock=lambda: now[0])
            owner = store.owner_for('qa')
            original = source(text='Maya might go swimming tomorrow.')
            original.update(captured_at=now[0], timezone='America/New_York')
            store.put_source(owner, original)
            raw = dict(text=original['passages'][0]['text'], kind='event', basis='tentative', scope='named',
                mention=dict(name='Maya', relationship=None, qualifiers=[], speaker_label=None),
                evidence=[dict(passage='p1', quote=original['passages'][0]['text'])],
                time=dict(status='future', expression='tomorrow'),
                change=dict(kind='none', previous_text=None))
            proposal = memory_evidence.parse(dict(memories=[raw]), original)[0]
            # Fixture-accepted decisions exercise the actual commit boundary; no model quality claim.
            memory_atomic.commit(store, store.claim_job(owner), [dict(proposal=proposal, action='new',
                rubric='fixture-only', judgments={})])
            for elapsed in [0, 7 * 86400]:
                now[0] = original['captured_at'] + elapsed
                store = MemoryStore(path, clock=lambda: now[0])
                claim = store.search(owner, unresolved_only=True)[0]
                temporal = claim['temporal_evidence']
                self.assertEqual(temporal['date'], '2026-09-27')
                self.assertEqual(temporal['basis'], 'tentative')
                self.assertEqual(temporal['reported_status'], 'future')
                self.assertIsNone(claim['valid_until'])
                self.assertEqual(store.search(owner), [])
                self.assertEqual(store.evidence(owner, 'session-a')['passages'][0]['claims'][0]['temporal_evidence'], temporal)
                self.assertEqual(store.recall_snapshot(owner)[0]['passages'][0]['claims'][0]['temporal_evidence'], temporal)
                self.assertEqual(store.source(owner, 'session-a'), original)
            other = store.owner_for('other')
            self.assertEqual(store.search(other, unresolved_only=True), [])
            store.delete_source(owner, 'session-a')
            self.assertEqual(store.search(owner, unresolved_only=True), [])
            self.assertEqual(store.recall_snapshot(owner), [])
