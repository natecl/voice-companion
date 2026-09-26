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

    def test_explicit_weekday_context_and_conflicts(self):
        anchor = epoch('2026-09-26T12:00:00-04:00')  # Saturday
        cases = {'Tuesday next week': '2026-09-29', 'Tuesday of this week': '2026-09-22',
                 'Tuesday last week': '2026-09-15', 'this coming Tuesday': '2026-09-29',
                 'upcoming Tuesday': '2026-09-29', 'this past Tuesday': '2026-09-22'}
        for expression, expected in cases.items():
            with self.subTest(expression=expression):
                self.assertEqual(resolve(expression, anchor, 'America/New_York')['date'], expected)
        for expression in ['Tuesday', 'next Tuesday', 'last Tuesday', 'every Tuesday',
                           'not this coming Tuesday', 'Tuesday next week or Wednesday', 'Tuesday next week at 3']:
            self.assertEqual(resolve(expression, anchor, 'America/New_York')['resolution'], 'unresolved')
        for expression, status in [('Tuesday this week', 'future'), ('Tuesday next week', 'past')]:
            self.assertEqual(resolve(expression, anchor, 'America/New_York', reported_status=status)['reason'],
                             'conflicting_temporal_context')
        tuesday = epoch('2026-09-29T10:00:00-04:00')
        self.assertEqual(resolve('upcoming Tuesday', tuesday, 'America/New_York')['reason'], 'same_day_ambiguity')

    def test_weekday_dates_use_local_week_and_cross_dst_year(self):
        # Sunday in New York but Monday in Tokyo: next week's Tuesday differs by seven days.
        instant = epoch('2026-09-28T02:00:00+00:00')
        self.assertEqual(resolve('Tuesday next week', instant, 'America/New_York')['date'], '2026-09-29')
        self.assertEqual(resolve('Tuesday next week', instant, 'Asia/Tokyo')['date'], '2026-10-06')
        self.assertEqual(resolve('Monday next week', epoch('2026-12-31T12:00:00+00:00'), 'UTC')['date'], '2027-01-04')
        self.assertEqual(resolve('Monday next week', epoch('2026-03-08T12:00:00-04:00'), 'America/New_York')['date'], '2026-03-09')

    def test_real_atomic_store_preserves_future_plan_across_reads_and_deletion(self):
        self.exercise_plan('tomorrow', '2026-09-27')
        self.exercise_plan('Tuesday next week', '2026-09-29')

    def exercise_plan(self, expression, expected_date):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'memory.sqlite'
            now = [epoch('2026-09-27T02:00:00+00:00')]
            store = MemoryStore(path, clock=lambda: now[0])
            owner = store.owner_for('qa')
            original = source(text=f'Maya might go swimming {expression}.')
            original.update(captured_at=now[0], timezone='America/New_York')
            store.put_source(owner, original)
            raw = dict(text=original['passages'][0]['text'], kind='event', basis='tentative', scope='named',
                mention=dict(name='Maya', relationship=None, qualifiers=[], speaker_label=None),
                evidence=[dict(passage='p1', quote=original['passages'][0]['text'])],
                time=dict(status='future', expression=expression),
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
                self.assertEqual(temporal['date'], expected_date)
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
