import ast
import dataclasses
from pathlib import Path
import threading
import unittest
from unittest import mock
import uuid

import capture_quota as cq

OWNER_A = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa'
OWNER_B = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb'
P0 = (0, 1_000)
P1 = (1_000, 1_001_000)
P2 = (1_001_000, 2_001_000)
P3 = (2_001_000, 3_001_000)
OVERLAP = (500_000, 1_500_000)
FREE, PLUS = 3_600_000, 72_000_000
CHUNK = 300_000


def cid(number):
    return str(uuid.UUID(int=number))


def ent(owner=OWNER_A, plan='free', period=P1):
    return cq.Entitlement(owner, plan, period[0], period[1])


def res(capture, ms=CHUNK, at=1_500, **entitlement):
    return cq.Reserve(cid(capture), ent(**entitlement), at, ms)


def ev(capture, sequence, kind, offset, reason=None):
    return cq.CaptureEvent(cid(capture), sequence, kind, offset, reason)


def end(capture, sequence, offset, reason='stopped'):
    return ev(capture, sequence, 'end', offset, reason)


def rec(capture):
    return cq.Recover(cid(capture))


def do(account, command):
    return cq.apply(account, account.owner, command)


def step(account, *commands):
    for command in commands:
        account = do(account, command).account
    return account


def events(capture, steps, first=1):
    return [ev(capture, first + i, kind, offset) if kind != 'end' else end(capture, first + i, offset)
            for i, (kind, offset) in enumerate(steps)]


def started(steps, capture=1, ms=CHUNK, **entitlement):
    """Account with one reserved capture advanced through (kind, offset) steps."""
    return step(cq.new_account(OWNER_A), res(capture, ms, **entitlement), *events(capture, steps))


def fill(account, count, ms=CHUNK, period=P1, plan='free', first=100):
    return step(account, *[res(first + i, ms, period=period, plan=plan) for i in range(count)])


def checked(account):
    """Force the public constructor's full validation and return the account."""
    return dataclasses.replace(account)


def forge(record, **fields):
    """Copy any record while bypassing constructor validation, as a corrupt store could."""
    forged = object.__new__(type(record))
    for field in dataclasses.fields(record):
        object.__setattr__(forged, field.name, fields.get(field.name, getattr(record, field.name)))
    return forged


class PlainStore:
    """Minimal CAS store that validates NOTHING and records every swap attempt."""

    def __init__(self, account):
        self.account, self.swaps = account, []

    def load(self):
        return self.account

    def cas(self, expected_revision, new_account):
        self.swaps.append((expected_revision, new_account))
        if self.account.revision != expected_revision:
            return False
        self.account = new_account
        return True


class Base(unittest.TestCase):
    def assertCode(self, exc_type, code, fn, *args, **kwargs):
        with self.assertRaises(exc_type) as raised:
            fn(*args, **kwargs)
        self.assertEqual(raised.exception.code, code)
        return raised.exception


class ValidationTests(Base):
    BAD_INTS = [True, False, 1.0, 1.5, -1, '1', None, cq.MAX_MS + 1, 10 ** 30, b'1', [1]]

    def test_public_shape(self):
        names = lambda cls: [f.name for f in dataclasses.fields(cls)]
        self.assertEqual(names(cq.Entitlement), ['owner', 'plan', 'period_start_ms', 'period_end_ms'])
        self.assertEqual(names(cq.Reserve), ['capture_id', 'entitlement', 'requested_at_ms', 'requested_ms'])
        self.assertEqual(names(cq.CaptureEvent), ['capture_id', 'sequence', 'kind', 'offset_ms', 'end_reason'])
        self.assertEqual(names(cq.Recover), ['capture_id'])
        self.assertEqual(names(cq.QuotaAccount), ['owner', 'revision', 'periods', 'captures', 'operations'])
        self.assertEqual(names(cq.Outcome), ['account', 'decision', 'changed', 'base_revision'])
        every = {n for cls in (cq.Entitlement, cq.Reserve, cq.CaptureEvent, cq.Recover) for n in names(cls)}
        self.assertFalse({n for n in every if 'byte' in n or 'amplitude' in n or 'audio' in n})
        self.assertEqual(cq.MAX_MS, 2 ** 63 - 1)
        self.assertEqual(cq.EVENT_KINDS, ('start', 'pause', 'resume', 'checkpoint', 'end'))
        self.assertEqual(cq.END_REASONS, ('stopped', 'failed', 'interrupted'))

    def test_allowances_exact_and_immutable(self):
        self.assertEqual(dict(cq.PLAN_ALLOWANCE_MS), {'free': 3_600_000, 'plus': 72_000_000})
        with self.assertRaises(TypeError):
            cq.PLAN_ALLOWANCE_MS['free'] = 1

    def test_integers_are_strict(self):
        class Subclass(int):
            pass
        for bad in self.BAD_INTS + [Subclass(5)]:
            with self.subTest(bad=repr(bad)):
                for build in (lambda: cq.Reserve(cid(1), ent(), bad, 1),
                              lambda: cq.Reserve(cid(1), ent(), 1, bad),
                              lambda: cq.CaptureEvent(cid(1), bad, 'start', 0),
                              lambda: cq.CaptureEvent(cid(1), 1, 'start', bad),
                              lambda: cq.Entitlement(OWNER_A, 'free', bad, 100),
                              lambda: cq.Entitlement(OWNER_A, 'free', 0, bad)):
                    self.assertCode(cq.InvalidInput, 'invalid_input', build)
        cq.Reserve(cid(1), cq.Entitlement(OWNER_A, 'free', 0, cq.MAX_MS), cq.MAX_MS - 1, cq.MAX_MS)
        cq.CaptureEvent(cid(1), cq.MAX_MS, 'start', cq.MAX_MS)

    def test_bounds(self):
        for build in (lambda: cq.Reserve(cid(1), ent(), 1_500, 0),
                      lambda: cq.CaptureEvent(cid(1), 0, 'start', 0),
                      lambda: cq.Entitlement(OWNER_A, 'free', 5, 5),
                      lambda: cq.Entitlement(OWNER_A, 'free', 6, 5),
                      lambda: cq.Entitlement(OWNER_A, 'free', 0, 0)):
            self.assertRaises(cq.InvalidInput, build)

    def test_owner_and_capture_must_be_canonical_uuid(self):
        bad = ['', 'person@example.com', 'x' * 43, OWNER_A.upper(), '{' + OWNER_A + '}',
               'urn:uuid:' + OWNER_A, OWNER_A.replace('-', ''), None, uuid.UUID(OWNER_A), b'x' * 36]
        account = cq.new_account(OWNER_A)
        for value in bad:
            with self.subTest(value=repr(value)):
                self.assertRaises(cq.InvalidInput, cq.Entitlement, value, 'free', 0, 10)
                self.assertRaises(cq.InvalidInput, cq.new_account, value)
                self.assertRaises(cq.InvalidInput, cq.Reserve, value, ent(), 1_500, 1)
                self.assertRaises(cq.InvalidInput, cq.CaptureEvent, value, 1, 'start', 0)
                self.assertRaises(cq.InvalidInput, cq.Recover, value)
                self.assertRaises(cq.InvalidInput, cq.apply, account, value, res(1))

    def test_plan_kind_and_end_reason_rules(self):
        for plan in ['Free', 'pro', '', None, 1]:
            self.assertRaises(cq.InvalidInput, cq.Entitlement, OWNER_A, plan, 0, 10)
        for kind in ['bytes', 'amplitude', 'START', 'active', 'stop', '', None, 3]:
            self.assertRaises(cq.InvalidInput, cq.CaptureEvent, cid(1), 1, kind, 0)
        self.assertRaises(cq.InvalidInput, cq.CaptureEvent, cid(1), 1, 'end', 0)
        self.assertRaises(cq.InvalidInput, cq.CaptureEvent, cid(1), 1, 'end', 0, 'done')
        self.assertRaises(cq.InvalidInput, cq.CaptureEvent, cid(1), 1, 'pause', 0, 'stopped')
        for reason in cq.END_REASONS:
            cq.CaptureEvent(cid(1), 1, 'end', 0, reason)

    def test_wrong_argument_types(self):
        account = cq.new_account(OWNER_A)
        self.assertRaises(cq.InvalidInput, cq.apply, None, OWNER_A, res(1))
        self.assertRaises(cq.InvalidInput, cq.apply, account, OWNER_A, 'junk')
        self.assertRaises(cq.InvalidInput, cq.Reserve, cid(1), 'free', 1_500, 1)
        self.assertRaises(cq.InvalidInput, cq.period_summary, None, 0, 1)


class ReserveTests(Base):
    def test_full_partial_and_exhausted_grants(self):
        account = fill(cq.new_account(OWNER_A), 10)  # 3,000,000 reserved
        grant = do(account, res(1, 1_000_000))
        self.assertEqual((grant.decision.reserved_ms, grant.decision.remaining_ms), (600_000, 0))
        self.assertEqual(do(account, res(1, 600_000)).decision.reserved_ms, 600_000)
        account = grant.account
        error = self.assertCode(cq.QuotaExceeded, 'quota_exhausted', do, account, res(2, 1))
        self.assertEqual(error.remaining_ms, 0)
        summary = cq.period_summary(account, *P1)
        self.assertEqual((summary.settled_ms, summary.outstanding_reserved_ms, summary.available_ms),
                         (0, FREE, 0))

    def test_request_larger_than_allowance_is_granted_the_allowance(self):
        self.assertEqual(do(cq.new_account(OWNER_A), res(1, 10_000_000)).decision.reserved_ms, FREE)

    def test_plus_one_hour_reservation_accepted_without_invented_cap(self):
        account = cq.new_account(OWNER_A)
        grant = do(account, res(1, 3_600_000, plan='plus'))
        self.assertEqual(grant.decision.reserved_ms, 3_600_000)
        self.assertEqual(grant.decision.remaining_ms, PLUS - 3_600_000)
        self.assertEqual(do(account, res(1, 100_000_000, plan='plus')).decision.reserved_ms, PLUS)

    def test_denial_is_not_recorded_and_is_reevaluated(self):
        full = fill(cq.new_account(OWNER_A), 12)
        self.assertEqual(full.revision, 12)
        self.assertRaises(cq.QuotaExceeded, do, full, res(1))
        self.assertEqual(full.revision, 12)
        freed = step(full, end(100, 1, 0, 'failed'))  # failure before start releases everything
        self.assertEqual(do(freed, res(1)).decision.reserved_ms, CHUNK)

    def test_wall_time_must_be_inside_half_open_period(self):
        account = cq.new_account(OWNER_A)
        for at in (P1[1], P1[1] + 1, P1[0] - 1):
            self.assertCode(cq.PeriodError, 'outside_period', do, account, res(1, at=at))
        for at in (P1[0], P1[1] - 1):
            self.assertEqual(do(account, res(1, at=at)).decision.status, 'reserved')

    def test_owner_checks(self):
        account = cq.new_account(OWNER_A)
        self.assertCode(cq.OwnerMismatch, 'owner_mismatch', do, account, res(1, owner=OWNER_B))
        self.assertCode(cq.OwnerMismatch, 'owner_mismatch', cq.apply, account, OWNER_B, res(1))
        self.assertCode(cq.OwnerMismatch, 'owner_mismatch', cq.apply, account, OWNER_B, rec(1))

    def test_decision_fields(self):
        outcome = do(cq.new_account(OWNER_A), res(1, 120_000, at=7_000))
        self.assertEqual((outcome.base_revision, outcome.changed, outcome.account.revision), (0, True, 1))
        self.assertEqual(outcome.decision, cq.Decision(
            kind='reserve', capture_id=cid(1), status='reserved', reserved_ms=120_000, measured_ms=0,
            charged_ms=None, released_ms=None, overrun_ms=0, reservation_left_ms=120_000,
            remaining_ms=FREE - 120_000, committed_revision=1, period_start_ms=P1[0], period_end_ms=P1[1],
            end_reason=None))


class IdempotencyTests(Base):
    def test_operation_keys(self):
        account = step(cq.new_account(OWNER_A), res(1), ev(1, 1, 'start', 0), ev(1, 2, 'checkpoint', 5),
                       rec(1))
        self.assertEqual([op.key for op in account.operations],
                         [(cid(1), 'reserve', 0), (cid(1), 'event', 1), (cid(1), 'event', 2),
                          (cid(1), 'recover', 0)])

    def test_exact_retry_returns_original_with_unchanged_account(self):
        first = do(cq.new_account(OWNER_A), res(1, 100_000))
        again = do(first.account, res(1, 100_000))
        self.assertFalse(again.changed)
        self.assertIs(again.account, first.account)
        self.assertIs(again.decision, first.decision)
        self.assertEqual(again.base_revision, first.account.revision)

    def test_exact_retry_after_settlement_and_rollover_is_unchanged(self):
        first = do(cq.new_account(OWNER_A), res(1, 100_000))
        later = step(first.account, ev(1, 1, 'start', 0), end(1, 2, 50),
                     res(2, 1_000, period=P2, at=1_500_000, plan='plus'))
        again = do(later, res(1, 100_000))
        self.assertFalse(again.changed)
        self.assertIs(again.account, later)
        self.assertEqual(again.decision, first.decision)
        self.assertEqual(again.decision.committed_revision, 1)
        self.assertEqual(again.decision.status, 'reserved')  # as originally answered, not today's status

    def test_same_capture_cannot_be_rebound_to_another_period_or_plan(self):
        account = step(cq.new_account(OWNER_A), res(1), res(2, period=P2, at=1_500_000))
        for change in (res(1, period=P2, at=1_500_000), res(1, plan='plus'),
                       res(1, at=2_000), res(1, ms=CHUNK + 1), res(1, period=P3, at=2_500_000)):
            with self.subTest(change=change):
                self.assertCode(cq.IdempotencyConflict, 'idempotency_conflict', do, account, change)
        self.assertEqual(len(account.periods), 2)
        self.assertEqual(len(account.captures), 2)

    def test_changed_snapshot_time_or_amount_conflicts(self):
        account = step(cq.new_account(OWNER_A), res(1, 100_000, at=2_000))
        changes = [res(1, 100_000, at=2_001), res(1, 100_001, at=2_000), res(1, 100_000, at=2_000, plan='plus'),
                   res(1, 100_000, at=2_000, period=(1_000, 1_001_001)),
                   res(1, 100_000, at=2_000, period=(999, 1_001_000))]
        for change in changes:
            with self.subTest(change=change):
                self.assertCode(cq.IdempotencyConflict, 'idempotency_conflict', do, account, change)

    def test_event_and_recover_retries(self):
        account = step(cq.new_account(OWNER_A), res(1), ev(1, 1, 'start', 5))
        stopped = do(account, end(1, 2, 50))
        self.assertIs(do(stopped.account, end(1, 2, 50)).decision, stopped.decision)  # after settlement
        self.assertIs(do(stopped.account, ev(1, 1, 'start', 5)).account, stopped.account)
        for change in (ev(1, 1, 'start', 6), ev(1, 1, 'checkpoint', 5), end(1, 2, 51),
                       end(1, 2, 50, 'failed'), end(1, 2, 50, 'interrupted')):
            with self.subTest(change=change):
                self.assertCode(cq.IdempotencyConflict, 'idempotency_conflict', do, stopped.account, change)
        recovered = do(account, rec(1))
        again = do(recovered.account, rec(1))
        self.assertFalse(again.changed)
        self.assertIs(again.decision, recovered.decision)

    def test_owner_isolation(self):
        a = step(cq.new_account(OWNER_A), res(1, 200_000))
        b = step(cq.new_account(OWNER_B), res(1, 100_000, owner=OWNER_B))
        self.assertEqual(cq.period_summary(a, *P1).outstanding_reserved_ms, 200_000)
        self.assertEqual(cq.period_summary(b, *P1).outstanding_reserved_ms, 100_000)
        self.assertCode(cq.OwnerMismatch, 'owner_mismatch', cq.apply, a, OWNER_B, res(1, 200_000))
        self.assertCode(cq.OwnerMismatch, 'owner_mismatch', cq.apply, a, OWNER_B, ev(1, 1, 'start', 0))
        self.assertCode(cq.OwnerMismatch, 'owner_mismatch', do, a, res(1, 200_000, owner=OWNER_B))


class LifecycleTests(Base):
    def test_paused_gap_is_not_billed_and_end_settles_in_same_revision(self):
        account = started([('start', 0), ('pause', 60_000), ('resume', 90_000)])
        before = account.revision
        outcome = do(account, end(1, 4, 150_000))
        self.assertEqual(outcome.account.revision, before + 1)  # one revision, one CAS
        decision = outcome.decision
        self.assertEqual((decision.status, decision.measured_ms, decision.charged_ms, decision.released_ms),
                         ('settled', 120_000, 120_000, 180_000))
        self.assertEqual(decision.end_reason, 'stopped')
        summary = cq.period_summary(outcome.account, *P1)
        self.assertEqual((summary.settled_ms, summary.outstanding_reserved_ms, summary.available_ms),
                         (120_000, 0, FREE - 120_000))

    def test_preparation_and_finalization_unbilled_and_checkpoints_not_double_counted(self):
        account = started([('start', 5_000), ('checkpoint', 35_000), ('checkpoint', 65_000)])
        self.assertEqual(do(account, end(1, 4, 65_000)).decision.charged_ms, 60_000)
        self.assertEqual(do(account, end(1, 4, 71_000)).decision.charged_ms, 66_000)

    def test_end_from_paused_adds_nothing(self):
        account = started([('start', 0), ('pause', 40_000)])
        self.assertEqual(do(account, end(1, 3, 90_000)).decision.charged_ms, 40_000)

    def test_failure_before_start_releases_zero_billed_quota_both_paths(self):
        for command in (end(1, 1, 0, 'failed'), end(1, 1, 7, 'stopped'), end(1, 1, 7, 'interrupted'), rec(1)):
            with self.subTest(command=command):
                account = step(cq.new_account(OWNER_A), res(1))
                outcome = do(account, command)
                self.assertEqual((outcome.decision.charged_ms, outcome.decision.released_ms), (0, CHUNK))
                self.assertEqual(outcome.decision.measured_ms, 0)
                summary = cq.period_summary(outcome.account, *P1)
                self.assertEqual((summary.settled_ms, summary.outstanding_reserved_ms, summary.available_ms),
                                 (0, 0, FREE))

    def test_end_interrupted_trusts_terminal_offset_but_recover_uses_last_acknowledgement(self):
        account = started([('start', 0), ('checkpoint', 30_000)])
        ended = do(account, end(1, 3, 90_000, 'interrupted'))
        self.assertEqual((ended.decision.charged_ms, ended.decision.end_reason), (90_000, 'interrupted'))
        recovered = do(account, rec(1))
        self.assertEqual((recovered.decision.charged_ms, recovered.decision.end_reason), (30_000, 'recovered'))
        self.assertEqual(recovered.decision.released_ms, CHUNK - 30_000)

    def test_recover_bills_only_acknowledged_usage(self):
        cases = [([('start', 0)], 0),
                 ([('start', 0), ('checkpoint', 10_000)], 10_000),
                 ([('start', 0), ('pause', 40_000)], 40_000),
                 ([('start', 0), ('pause', 40_000), ('resume', 50_000)], 40_000),
                 ([('start', 0), ('pause', 40_000), ('resume', 50_000), ('checkpoint', 55_000)], 45_000)]
        for steps, expected in cases:
            with self.subTest(steps=steps):
                outcome = do(started(steps), rec(1))
                self.assertEqual(outcome.decision.charged_ms, expected)
                self.assertEqual(outcome.decision.status, 'settled')
                self.assertEqual(cq.period_summary(outcome.account, *P1).outstanding_reserved_ms, 0)

    def test_overrun_reports_measured_but_bills_reservation(self):
        account = started([('start', 0)], ms=60_000)
        mid = do(account, ev(1, 2, 'checkpoint', 30_000))
        self.assertEqual((mid.decision.overrun_ms, mid.decision.reservation_left_ms), (0, 30_000))
        over = do(mid.account, ev(1, 3, 'checkpoint', 70_000))
        self.assertEqual((over.decision.measured_ms, over.decision.overrun_ms, over.decision.reservation_left_ms),
                         (70_000, 10_000, 0))
        self.assertEqual(cq.period_summary(over.account, *P1).outstanding_reserved_ms, 60_000)
        done = do(over.account, end(1, 4, 90_000))
        self.assertEqual((done.decision.measured_ms, done.decision.charged_ms, done.decision.released_ms,
                          done.decision.overrun_ms), (90_000, 60_000, 0, 30_000))
        self.assertEqual(cq.period_summary(done.account, *P1).settled_ms, 60_000)
        checked(done.account)

    def test_billing_is_clamped_to_a_partial_grant(self):
        account = fill(cq.new_account(OWNER_A), 10)
        account = step(account, res(1, 1_000_000), ev(1, 1, 'start', 0))
        outcome = do(account, end(1, 2, 700_000))
        self.assertEqual((outcome.decision.reserved_ms, outcome.decision.measured_ms,
                          outcome.decision.charged_ms, outcome.decision.overrun_ms), (600_000, 700_000, 600_000, 100_000))
        summary = cq.period_summary(outcome.account, *P1)
        self.assertEqual((summary.settled_ms, summary.outstanding_reserved_ms), (600_000, 3_000_000))

    def test_terminal_end_and_recover_settle_once_and_close_the_capture(self):
        account = started([('start', 0), ('checkpoint', 20_000)])
        ended = do(account, end(1, 3, 50_000))
        self.assertCode(cq.CaptureConflict, 'capture_closed', do, ended.account, rec(1))
        self.assertCode(cq.CaptureConflict, 'capture_closed', do, ended.account, end(1, 4, 60_000))
        self.assertCode(cq.CaptureConflict, 'capture_closed', do, ended.account, ev(1, 4, 'resume', 60_000))
        recovered = do(account, rec(1))
        self.assertCode(cq.CaptureConflict, 'capture_closed', do, recovered.account, end(1, 3, 50_000))
        self.assertCode(cq.CaptureConflict, 'capture_closed', do, recovered.account, ev(1, 3, 'start', 50_000))
        self.assertEqual(cq.period_summary(ended.account, *P1).settled_ms, 50_000)
        self.assertEqual(cq.period_summary(recovered.account, *P1).settled_ms, 20_000)

    def test_no_implicit_resume(self):
        account = started([('start', 0), ('pause', 10)])
        for kind in ('pause', 'checkpoint', 'start'):
            self.assertCode(cq.EventRejected, 'invalid_transition', do, account, ev(1, 3, kind, 20))
        self.assertEqual(do(account, ev(1, 3, 'resume', 20)).decision.status, 'active')

    def test_unknown_capture(self):
        account = cq.new_account(OWNER_A)
        self.assertCode(cq.CaptureConflict, 'unknown_capture', do, account, ev(9, 1, 'start', 0))
        self.assertCode(cq.CaptureConflict, 'unknown_capture', do, account, rec(9))

    def test_offsets_are_independent_of_entitlement_wall_time(self):
        account = started([('start', 0), ('checkpoint', 9_999_999_999)])
        self.assertEqual(do(account, end(1, 3, 9_999_999_999)).decision.measured_ms, 9_999_999_999)

    def test_transition_table(self):
        reach = {'reserved': [], 'active': [('start', 0)], 'paused': [('start', 0), ('pause', 10)]}
        allowed = {'reserved': {'start', 'end'}, 'active': {'pause', 'checkpoint', 'end'},
                   'paused': {'resume', 'end'}}
        for status, steps in list(reach.items()) + [('settled', None)]:
            for kind in cq.EVENT_KINDS:
                with self.subTest(status=status, kind=kind):
                    account = started(reach.get(status, [('start', 0), ('end', 5)]))
                    sequence = len(account.captures[0].events) + 1
                    command = end(1, sequence, 100) if kind == 'end' else ev(1, sequence, kind, 100)
                    if status == 'settled':
                        self.assertCode(cq.CaptureConflict, 'capture_closed', do, account, command)
                    elif kind in allowed[status]:
                        do(account, command)
                    else:
                        self.assertCode(cq.EventRejected, 'invalid_transition', do, account, command)

    def test_bounded_sequence_sweep(self):
        steps = [('start', 0), ('checkpoint', 10), ('pause', 20), ('resume', 30), ('checkpoint', 40), ('end', 50)]
        account = step(cq.new_account(OWNER_A), res(1, 100_000))
        for applied, (kind, offset) in enumerate(steps):
            expected = applied + 1
            for sequence in range(1, expected + 4):
                if sequence == expected:
                    continue
                with self.subTest(applied=applied, sequence=sequence):
                    command = end(1, sequence, offset) if kind == 'end' else ev(1, sequence, kind, offset)
                    if sequence < expected:
                        self.assertCode(cq.IdempotencyConflict, 'idempotency_conflict', do, account, command)
                    else:
                        self.assertCode(cq.EventRejected, 'sequence_gap', do, account, command)
            command = end(1, expected, offset) if kind == 'end' else ev(1, expected, kind, offset)
            account = do(account, command).account
        self.assertEqual(account.captures[0].status, 'settled')
        self.assertEqual(cq.period_summary(account, *P1).settled_ms, 20 + 20)

    def test_time_regression_and_equal_offsets(self):
        account = started([('start', 100)])
        self.assertCode(cq.EventRejected, 'time_regression', do, account, ev(1, 2, 'checkpoint', 99))
        self.assertEqual(do(account, ev(1, 2, 'checkpoint', 100)).decision.measured_ms, 0)

    def test_rejected_commands_leave_the_account_unchanged(self):
        account = started([('start', 0), ('checkpoint', 30_000)])
        for command in (ev(1, 9, 'pause', 40_000), ev(1, 3, 'resume', 40_000), ev(1, 3, 'checkpoint', 10),
                        ev(2, 1, 'start', 0), rec(2)):
            self.assertRaises(cq.QuotaError, do, account, command)
        self.assertEqual(checked(account), account)
        self.assertEqual(do(account, rec(1)).decision.charged_ms, 30_000)

    def test_event_limit_bounds_the_log_but_end_and_recover_stay_admissible(self):
        limit = cq.MAX_EVENTS_PER_CAPTURE
        commands = [res(1), ev(1, 1, 'start', 0)] + [ev(1, n, 'checkpoint', n) for n in range(2, limit + 1)]
        account = cq.replay(OWNER_A, commands)
        self.assertEqual(len(account.captures[0].events), limit)
        self.assertCode(cq.EventRejected, 'event_limit', do, account, ev(1, limit + 1, 'checkpoint', limit + 1))
        self.assertCode(cq.EventRejected, 'event_limit', do, account, ev(1, limit + 1, 'pause', limit + 1))
        self.assertEqual(do(account, end(1, limit + 1, 5_000)).decision.charged_ms, 5_000)
        self.assertEqual(do(account, rec(1)).decision.charged_ms, limit)  # last acknowledged offset

    def test_prior_accounts_are_immutable(self):
        original = step(cq.new_account(OWNER_A), res(1))
        copy = cq.replay(OWNER_A, [op.command for op in original.operations])
        later = step(original, ev(1, 1, 'start', 0), end(1, 2, 5))
        self.assertEqual(original, copy)
        self.assertEqual((original.revision, original.captures[0].status, original.captures[0].events),
                         (1, 'reserved', ()))
        self.assertEqual(later.revision, 3)
        with self.assertRaises(dataclasses.FrozenInstanceError):
            original.revision = 99
        with self.assertRaises(dataclasses.FrozenInstanceError):
            original.captures[0].status = 'settled'
        for field in ('periods', 'captures', 'operations'):
            self.assertIsInstance(getattr(original, field), tuple)

    def test_deterministic_and_reconstructable(self):
        def script():
            account = fill(cq.new_account(OWNER_A), 3)
            account = step(account, *events(101, [('start', 0), ('pause', 10), ('resume', 20), ('end', 40)]))
            return step(account, rec(102))
        first, second = script(), script()
        self.assertEqual(first, second)
        self.assertEqual(hash(first), hash(second))
        commands = [op.command for op in first.operations]
        self.assertEqual(cq.replay(OWNER_A, commands), first)
        self.assertEqual(cq.replay(OWNER_A, first.operations), first)
        self.assertEqual(checked(first), first)


class PeriodTests(Base):
    def test_periods_append_only_and_history_retained(self):
        account = step(cq.new_account(OWNER_A), res(1), ev(1, 1, 'start', 0), end(1, 2, 100_000))
        old = cq.period_summary(account, *P1)
        account = step(account, res(2, period=P2, plan='plus', at=1_500_000))
        self.assertEqual([(p.period_start_ms, p.period_end_ms) for p in account.periods], [P1, P2])
        self.assertEqual(cq.period_summary(account, *P1), old)  # nothing reset or removed
        self.assertEqual(old.settled_ms, 100_000)
        self.assertEqual(cq.period_summary(account, *P2).allowance_ms, PLUS)
        self.assertEqual(len(account.captures), 2)
        later = step(account, res(3, period=P3, at=2_500_000))
        self.assertEqual(len(later.periods), 3)
        self.assertEqual(cq.period_summary(later, *P1), old)

    def test_overlap_backfill_and_changed_plan_are_rejected(self):
        account = step(cq.new_account(OWNER_A), res(1, period=P2, at=1_500_000))
        self.assertCode(cq.PeriodError, 'period_overlap', do, account, res(2, period=OVERLAP, at=1_200_000))
        self.assertCode(cq.PeriodError, 'period_overlap', do, account,
                        res(2, period=(P2[0], P2[1] + 1), at=1_500_000))
        self.assertCode(cq.PeriodError, 'period_overlap', do, account,
                        res(2, period=(P2[0] + 1, P2[1]), at=1_500_000))
        self.assertCode(cq.PeriodError, 'period_overlap', do, account,
                        res(2, period=(P2[0] - 5, P2[1] + 5), at=1_500_000))
        self.assertCode(cq.PeriodError, 'period_backfill', do, account, res(2, period=P1, at=1_500))
        self.assertCode(cq.PeriodError, 'period_backfill', do, account, res(2, period=P0, at=500))
        self.assertCode(cq.EntitlementChanged, 'entitlement_changed', do, account,
                        res(2, period=P2, plan='plus', at=1_500_000))
        self.assertEqual(len(account.periods), 1)
        self.assertEqual(len(do(account, res(2, period=P3, at=2_500_000)).account.periods), 2)

    def test_stale_new_reserve_into_an_older_recorded_period_is_rejected(self):
        account = step(cq.new_account(OWNER_A), res(1, 100_000, at=2_000), ev(1, 1, 'start', 0),
                       res(2, 1_000, period=P2, at=1_500_000))
        store = PlainStore(account)
        stale = [res(3, 50_000, at=3_000), res(3, 50_000, at=P1[1] - 1),
                 res(3, 50_000, at=3_000, plan='plus')]  # changed plan on an older period: chronology first
        for command in stale:
            with self.subTest(command=command):
                self.assertCode(cq.PeriodError, 'period_backfill', do, account, command)
                self.assertCode(cq.PeriodError, 'period_backfill', cq.commit, store.load, store.cas,
                                OWNER_A, command)
        self.assertEqual(store.swaps, [])  # nothing reached the CAS
        self.assertIs(store.account, account)
        self.assertNotIn(cid(3), [c.capture_id for c in account.captures])
        self.assertEqual(len(account.captures), 2)
        self.assertEqual((account.revision, len(account.periods)), (3, 2))
        # The latest period still admits new captures, as does a newer nonoverlapping one.
        self.assertEqual(do(account, res(3, 50_000, period=P2, at=1_600_000)).decision.status, 'reserved')
        self.assertEqual(do(account, res(3, 50_000, period=P3, at=2_500_000)).decision.status, 'reserved')

    def test_old_period_retries_and_existing_captures_still_work_after_rollover(self):
        account = step(cq.new_account(OWNER_A), res(1, 100_000, at=2_000), res(2, 100_000, at=3_000),
                       ev(1, 1, 'start', 0), ev(2, 1, 'start', 0), ev(2, 2, 'checkpoint', 25_000),
                       res(3, 1_000, period=P2, at=1_500_000))
        original = do(account, res(1, 100_000, at=2_000))
        self.assertFalse(original.changed)  # exact retry of an older reserve is looked up first
        self.assertIs(original.account, account)
        self.assertEqual(original.decision, account.operations[0].decision)
        for changed in (res(1, 100_001, at=2_000), res(1, 100_000, at=2_001), res(1, 100_000, at=2_000, plan='plus')):
            with self.subTest(changed=changed):
                self.assertCode(cq.IdempotencyConflict, 'idempotency_conflict', do, account, changed)
        ended = do(account, ev(1, 2, 'checkpoint', 40_000))
        ended = do(ended.account, end(1, 3, 60_000))
        recovered = do(ended.account, rec(2))
        self.assertEqual((ended.decision.charged_ms, recovered.decision.charged_ms), (60_000, 25_000))
        self.assertEqual({(d.period_start_ms, d.period_end_ms) for d in (ended.decision, recovered.decision)}, {P1})
        summary = cq.period_summary(recovered.account, *P1)
        self.assertEqual((summary.settled_ms, summary.outstanding_reserved_ms), (85_000, 0))
        self.assertEqual(cq.period_summary(recovered.account, *P2).outstanding_reserved_ms, 1_000)
        checked(recovered.account)

    def test_gap_between_periods_is_allowed_but_not_filled_later(self):
        account = step(cq.new_account(OWNER_A), res(1, period=P1), res(2, period=P3, at=2_500_000))
        self.assertCode(cq.PeriodError, 'period_backfill', do, account, res(3, period=P2, at=1_500_000))

    def test_old_captures_settle_the_old_allowance_after_a_new_period(self):
        account = fill(cq.new_account(OWNER_A), 11)  # 300,000 left in P1
        account = step(account, res(1, 200_000, at=2_000))
        account = step(account, ev(1, 1, 'start', 0), res(2, 1_000, period=P2, plan='plus', at=1_500_000))
        done = do(account, end(1, 2, 150_000))
        self.assertEqual(done.decision.charged_ms, 150_000)
        self.assertEqual((done.decision.period_start_ms, done.decision.period_end_ms), P1)
        self.assertEqual(done.decision.remaining_ms, FREE - 11 * CHUNK - 150_000)
        p1, p2 = cq.period_summary(done.account, *P1), cq.period_summary(done.account, *P2)
        self.assertEqual((p1.settled_ms, p1.outstanding_reserved_ms), (150_000, 11 * CHUNK))
        self.assertEqual((p2.settled_ms, p2.outstanding_reserved_ms), (0, 1_000))
        checked(done.account)

    def test_old_period_recover_after_rollover(self):
        account = step(cq.new_account(OWNER_A), res(1), ev(1, 1, 'start', 0), ev(1, 2, 'checkpoint', 25_000),
                       res(2, period=P2, at=1_500_000))
        done = do(account, rec(1))
        self.assertEqual(cq.period_summary(done.account, *P1).settled_ms, 25_000)
        self.assertEqual(cq.period_summary(done.account, *P2).settled_ms, 0)

    def test_periods_have_independent_allowances(self):
        account = fill(cq.new_account(OWNER_A), 12)
        self.assertRaises(cq.QuotaExceeded, do, account, res(1))
        grant = do(account, res(1, period=P2, at=1_500_000))
        self.assertEqual(grant.decision.reserved_ms, CHUNK)
        self.assertEqual(cq.period_summary(grant.account, *P1).available_ms, 0)

    def test_summary_of_unknown_period_fails(self):
        account = step(cq.new_account(OWNER_A), res(1))
        self.assertCode(cq.PeriodError, 'outside_period', cq.period_summary, account, *P2)
        self.assertRaises(cq.InvalidInput, cq.period_summary, account, True, P1[1])


class ForgeryTests(Base):
    def account(self):
        account = step(cq.new_account(OWNER_A), res(1), ev(1, 1, 'start', 0), end(1, 2, 100),
                       res(2, period=P2, plan='plus', at=1_500_000))
        return checked(account)

    def test_reconstructed_invalid_records_are_rejected(self):
        a = self.account()
        first, second = a.captures
        ops = a.operations
        forgeries = {
            'revision': lambda: dataclasses.replace(a, revision=a.revision + 1),
            'plan': lambda: dataclasses.replace(a, periods=(dataclasses.replace(a.periods[0], plan='plus'),
                                                            a.periods[1])),
            'inflated charge': lambda: dataclasses.replace(
                a, captures=(dataclasses.replace(first, charged_ms=first.charged_ms + 1), second)),
            'reopened capture': lambda: dataclasses.replace(
                a, captures=(dataclasses.replace(first, status='active', charged_ms=None, end_reason=None), second)),
            'dropped op': lambda: dataclasses.replace(a, revision=a.revision - 1, operations=ops[1:]),
            'duplicate op': lambda: dataclasses.replace(a, revision=a.revision + 1, operations=ops + ops[-1:]),
            'reordered ops': lambda: dataclasses.replace(a, operations=ops[::-1]),
            'swapped decision': lambda: dataclasses.replace(
                a, operations=(dataclasses.replace(ops[0], decision=ops[-1].decision),) + ops[1:]),
            'unsorted captures': lambda: dataclasses.replace(a, captures=(second, first)),
            'extra capture': lambda: dataclasses.replace(
                a, captures=a.captures + (dataclasses.replace(second, capture_id=cid(99)),)),
            'foreign period owner': lambda: dataclasses.replace(
                a, periods=(dataclasses.replace(a.periods[0], owner=OWNER_B), a.periods[1])),
            'list captures': lambda: dataclasses.replace(a, captures=list(a.captures)),
            'wrong key': lambda: dataclasses.replace(
                a, operations=(dataclasses.replace(ops[0], key=(cid(2), 'reserve', 0)),) + ops[1:]),
        }
        for name, build in forgeries.items():
            with self.subTest(name=name):
                self.assertRaises(cq.QuotaError, build)

    def test_record_level_invalid_values(self):
        base = self.account().captures[0]
        for change in (dict(charged_ms=base.reserved_ms + 1), dict(charged_ms=None), dict(status='weird'),
                       dict(end_reason='bogus'), dict(reserved_ms=base.requested_ms + 1), dict(events=[])):
            with self.subTest(change=change):
                self.assertRaises(cq.InvalidInput, dataclasses.replace, base, **change)
        self.assertRaises(cq.InvalidInput, cq.OperationRecord, 'key', 'junk', None)

    def test_forged_plus_allowance_cannot_admit_a_thirteenth_reservation(self):
        full = fill(cq.new_account(OWNER_A), 12)  # genuine Free account, exactly full
        forged = forge(full, periods=(ent(plan='plus'),))
        calls = []
        for command in (res(1, plan='plus'), res(1), ev(100, 1, 'start', 0), rec(100)):
            with self.subTest(command=command):
                self.assertCode(cq.InvariantViolation, 'invariant_violation', cq.apply, forged, OWNER_A, command)
                self.assertCode(cq.InvariantViolation, 'invariant_violation', cq.commit,
                                lambda: forged, lambda *a: calls.append(a) or True, OWNER_A, command)
        self.assertEqual(calls, [])  # nothing reached the store
        self.assertRaises(cq.InvariantViolation, cq.period_summary, forged, *P1)
        self.assertRaises(cq.InvariantViolation, dataclasses.replace, forged)

    def test_forged_overcommitted_or_tampered_accounts_are_rejected_before_use(self):
        full = fill(cq.new_account(OWNER_A), 12)
        extra = dataclasses.replace(full.captures[0], capture_id=cid(500))
        tampered = (forge(full, captures=full.captures + (extra,)),
                    forge(full, revision=full.revision + 1),
                    forge(full, operations=full.operations[:-1]),
                    forge(full, operations=full.operations + full.operations[-1:], revision=13),
                    forge(full, captures=()), forge(full, owner=OWNER_B))
        for index, forged in enumerate(tampered):
            with self.subTest(index=index):
                self.assertRaises(cq.QuotaError, cq.apply, forged, forged.owner, res(900))
                self.assertRaises(cq.QuotaError, cq.apply, forged, OWNER_A, res(900))

    def test_forged_charge_and_garbage_fields_fail_closed(self):
        done = self.account()
        first = done.captures[0]
        for forged in (forge(done, captures=(dataclasses.replace(first, charged_ms=0), done.captures[1])),
                       forge(done, captures=('junk',) + done.captures[1:]),
                       forge(done, operations=('junk',)), forge(done, periods='junk'),
                       forge(done, revision=True), forge(done, owner=5)):
            self.assertRaises(cq.QuotaError, cq.apply, forged, OWNER_A, rec(2))

    def test_corrupted_persisted_operation_key_is_rejected_before_cas(self):
        valid = step(cq.new_account(OWNER_A), res(1, 100))
        original = res(1, 100)
        bad_key = forge(valid.operations[0], key=(cid(1), 'reserve', 99))
        forged = forge(valid, operations=(bad_key,))
        # Before the fix this returned changed=True with two captures at revision 2.
        self.assertCode(cq.InvariantViolation, 'invariant_violation', cq.apply, forged, OWNER_A, original)
        store = PlainStore(forged)
        self.assertCode(cq.InvariantViolation, 'invariant_violation', cq.commit, store.load, store.cas,
                        OWNER_A, original)
        self.assertCode(cq.InvariantViolation, 'invariant_violation', cq.commit, store.load, store.cas,
                        OWNER_A, res(2, 100))
        self.assertEqual(store.swaps, [])
        for key in ((cid(2), 'reserve', 0), (cid(1), 'event', 0), (cid(1), 'reserve', False),
                    (cid(1), 'reserve', 0.0), [cid(1), 'reserve', 0], (cid(1), 'reserve'), 'junk', None):
            with self.subTest(key=key):
                account = forge(valid, operations=(forge(valid.operations[0], key=key),))
                self.assertRaises(cq.QuotaError, cq.apply, account, OWNER_A, original)
                self.assertRaises(cq.QuotaError, cq.period_summary, account, *P1)

    def test_nested_type_corruption_that_compares_equal_is_rejected(self):
        class IntSub(int):
            pass
        valid = step(cq.new_account(OWNER_A), res(1, 1), ev(1, 1, 'start', 0), ev(1, 2, 'checkpoint', 0))
        op_reserve, op_start, op_check = valid.operations
        capture, = valid.captures
        period, = valid.periods
        decision = op_reserve.decision
        corrupted = {
            'decision bool': forge(valid, operations=(
                forge(op_reserve, decision=forge(decision, committed_revision=True)), op_start, op_check)),
            'decision float': forge(valid, operations=(
                forge(op_reserve, decision=forge(decision, measured_ms=0.0)), op_start, op_check)),
            'decision subclass': forge(valid, operations=(
                forge(op_reserve, decision=forge(decision, reserved_ms=IntSub(1))), op_start, op_check)),
            'command bool amount': forge(valid, operations=(
                forge(op_reserve, command=forge(op_reserve.command, requested_ms=True)), op_start, op_check)),
            'command event sequence bool': forge(valid, operations=(
                op_reserve, forge(op_start, command=forge(op_start.command, sequence=True)), op_check)),
            'command offset float': forge(valid, operations=(
                op_reserve, op_start, forge(op_check, command=forge(op_check.command, offset_ms=0.0)))),
            'command entitlement bound float': forge(valid, operations=(
                forge(op_reserve, command=forge(op_reserve.command, entitlement=forge(
                    op_reserve.command.entitlement, period_start_ms=1000.0))), op_start, op_check)),
            'command entitlement plan': forge(valid, operations=(
                forge(op_reserve, command=forge(op_reserve.command, entitlement=forge(
                    op_reserve.command.entitlement, plan='gold'))), op_start, op_check)),
            'capture bool requested': forge(valid, captures=(forge(capture, requested_ms=True),)),
            'capture float reserved': forge(valid, captures=(forge(capture, reserved_ms=1.0),)),
            'capture event bool': forge(valid, captures=(forge(capture, events=(
                forge(capture.events[0], sequence=True), capture.events[1])),)),
            'capture events list': forge(valid, captures=(forge(capture, events=list(capture.events)),)),
            'period float': forge(valid, periods=(forge(period, period_end_ms=float(period.period_end_ms)),)),
            'period subclass': forge(valid, periods=(forge(period, period_start_ms=IntSub(period.period_start_ms)),)),
            'nonrecord op': forge(valid, operations=('junk', op_start, op_check)),
        }
        for name, account in corrupted.items():
            with self.subTest(name=name):
                self.assertRaises(cq.QuotaError, cq.apply, account, OWNER_A, ev(1, 3, 'checkpoint', 5))
                store = PlainStore(account)
                self.assertRaises(cq.QuotaError, cq.commit, store.load, store.cas, OWNER_A,
                                  ev(1, 3, 'checkpoint', 5))
                self.assertEqual(store.swaps, [])

    def test_forged_incoming_commands_cannot_skip_constructor_validation(self):
        class SubReserve(cq.Reserve):
            pass
        account = step(cq.new_account(OWNER_A), res(1), ev(1, 1, 'start', 0))
        good_reserve, good_event = res(2), ev(1, 2, 'checkpoint', 5)
        forged = {
            'reserve negative amount': forge(good_reserve, requested_ms=-5),
            'reserve bool amount': forge(good_reserve, requested_ms=True),
            'reserve float time': forge(good_reserve, requested_at_ms=1500.0),
            'reserve junk entitlement': forge(good_reserve, entitlement='free'),
            'reserve bad nested plan': forge(good_reserve, entitlement=forge(good_reserve.entitlement, plan='gold')),
            'reserve bad capture': forge(good_reserve, capture_id='not-a-uuid'),
            'event bad kind': forge(good_event, kind='bytes'),
            'event bool sequence': forge(good_event, sequence=True),
            'event reason on checkpoint': forge(good_event, end_reason='stopped'),
            'event end without reason': forge(end(1, 2, 5), end_reason=None),
            'recover bad id': forge(rec(1), capture_id='x'),
            'missing attributes': object.__new__(cq.Recover),
            'subclass': SubReserve(good_reserve.capture_id, good_reserve.entitlement, 1_500, 1),
            'plain string': 'reserve', 'none': None,
        }
        store = PlainStore(account)
        for name, command in forged.items():
            with self.subTest(name=name):
                self.assertCode(cq.InvalidInput, 'invalid_input', cq.apply, account, OWNER_A, command)
                self.assertRaises(cq.InvalidInput, cq.commit, store.load, store.cas, OWNER_A, command)
                self.assertRaises(cq.InvalidInput, cq.replay, OWNER_A, [command])
        self.assertEqual(store.swaps, [])
        # A forged command inside an otherwise valid OperationRecord is rejected by replay too.
        record = account.operations[0]
        self.assertRaises(cq.InvalidInput, cq.replay, OWNER_A, [forge(record, command=forged['reserve bool amount'])])
        self.assertRaises(cq.InvalidInput, cq.replay, OWNER_A, [forge(record, key=(cid(1), 'reserve', True))])

    def test_self_referencing_and_overdeep_forgeries_fail_closed_without_recursion_errors(self):
        def self_cycle(record, field):
            forged = forge(record)
            object.__setattr__(forged, field, forged)
            return forged

        def chain(depth):  # modest depth beyond the bound, never thousands
            node = 0
            for _ in range(depth):
                node = forge(ev(1, 1, 'start', 0), offset_ms=node)
            return node

        def nested(depth):
            node = ()
            for _ in range(depth):
                node = (node,)
            return node
        depth = cq._MAX_CLEAN_DEPTH + 4
        commands = {
            'event offset cycle': self_cycle(ev(1, 1, 'start', 0), 'offset_ms'),
            'recover id cycle': self_cycle(rec(1), 'capture_id'),
            'reserve entitlement cycle': self_cycle(res(1), 'entitlement'),
            'event chain': chain(depth),
            'event chain as field': forge(ev(1, 1, 'start', 0), offset_ms=chain(depth)),
        }
        valid = step(cq.new_account(OWNER_A), res(1), ev(1, 1, 'start', 0))
        store = PlainStore(valid)
        for name, command in commands.items():
            with self.subTest(command=name):
                self.assertCode(cq.InvalidInput, 'invalid_input', cq.apply, valid, OWNER_A, command)
                self.assertCode(cq.InvalidInput, 'invalid_input', cq.commit, store.load, store.cas, OWNER_A, command)
                self.assertCode(cq.InvalidInput, 'invalid_input', cq.replay, OWNER_A, [command])
                record = forge(valid.operations[0], command=command)
                self.assertCode(cq.InvalidInput, 'invalid_input', cq.replay, OWNER_A, [record])
        self.assertEqual(store.swaps, [])
        op, start = valid.operations
        capture, = valid.captures
        stored = {
            'op command cycle': forge(valid, operations=(
                forge(op, command=self_cycle(op.command, 'capture_id')), start)),
            'op event offset cycle': forge(valid, operations=(
                op, forge(start, command=self_cycle(start.command, 'offset_ms')))),
            'op decision cycle': forge(valid, operations=(forge(op, decision=self_cycle(op.decision, 'status')), start)),
            'capture event cycle': forge(valid, captures=(forge(
                capture, events=(self_cycle(capture.events[0], 'offset_ms'),)),)),
            'capture events deeply nested': forge(valid, captures=(forge(capture, events=nested(depth)),)),
            'period cycle': forge(valid, periods=(self_cycle(valid.periods[0], 'owner'),)),
            'operations deeply nested': forge(valid, operations=(nested(depth), start)),
        }
        for name, account in stored.items():
            with self.subTest(stored=name):
                self.assertCode(cq.InvariantViolation, 'invariant_violation', cq.apply, account, OWNER_A, rec(1))
                self.assertCode(cq.InvariantViolation, 'invariant_violation', cq.period_summary, account, *P1)
                bad = PlainStore(account)
                self.assertCode(cq.InvariantViolation, 'invariant_violation', cq.commit, bad.load, bad.cas,
                                OWNER_A, rec(1))
                self.assertEqual(bad.swaps, [])
                self.assertRaises(cq.QuotaError, dataclasses.replace, account)

    def test_recursion_error_is_caught_defensively_at_public_boundaries(self):
        valid = step(cq.new_account(OWNER_A), res(1))
        store = PlainStore(valid)
        def overflow(value, depth=0):
            if value == ():  # the empty account the module builds itself stays constructible
                return value
            raise RecursionError

        with mock.patch.object(cq, '_clean', side_effect=overflow):
            self.assertCode(cq.InvalidInput, 'invalid_input', cq.apply, valid, OWNER_A, res(2))
            self.assertCode(cq.InvalidInput, 'invalid_input', cq.commit, store.load, store.cas, OWNER_A, res(2))
            self.assertCode(cq.InvalidInput, 'invalid_input', cq.replay, OWNER_A, [res(2)])
            self.assertCode(cq.InvalidInput, 'invalid_input', cq.replay, OWNER_A, valid.operations)
            self.assertCode(cq.InvariantViolation, 'invariant_violation', cq.period_summary, valid, *P1)
        self.assertEqual(store.swaps, [])

    def test_legitimate_nesting_is_within_the_reconstruction_bound(self):
        account = step(cq.new_account(OWNER_A), res(1), *events(1, [('start', 0), ('pause', 5), ('resume', 9),
                                                                    ('checkpoint', 12), ('end', 20)]),
                       res(2, period=P2, plan='plus', at=1_500_000), ev(2, 1, 'start', 0))
        self.assertEqual(checked(account), account)
        self.assertEqual(cq.replay(OWNER_A, account.operations), account)
        self.assertEqual(do(account, rec(2)).decision.status, 'settled')
        self.assertEqual(cq.period_summary(account, *P2).allowance_ms, PLUS)
        self.assertGreaterEqual(cq._MAX_CLEAN_DEPTH, 5)  # deepest real path is 4 levels

    def test_replay_rejects_duplicates_divergence_and_wrong_owner(self):
        account = self.account()
        commands = [op.command for op in account.operations]
        self.assertRaises(cq.InvariantViolation, cq.replay, OWNER_A, commands + commands[:1])
        self.assertRaises(cq.CaptureConflict, cq.replay, OWNER_A, list(reversed(commands)))
        self.assertRaises(cq.InvalidInput, cq.replay, OWNER_A, ['junk'])
        self.assertRaises(cq.OwnerMismatch, cq.replay, OWNER_B, commands)
        bad = (dataclasses.replace(account.operations[0], decision=account.operations[1].decision),)
        self.assertRaises(cq.InvariantViolation, cq.replay, OWNER_A, bad + account.operations[1:])


class SyncedStore:
    """Test-only CAS cell. It supplies NO validation: that is commit/apply's job.
    Contenders meet at a Barrier before their first swap, so each has already
    computed a candidate from the same loaded revision."""

    def __init__(self, account, parties=None):
        self.account = account
        self.lock = threading.Lock()
        self.barrier = threading.Barrier(parties) if parties else None
        self.local = threading.local()
        self.loads = []
        self.swaps = []

    def load(self):
        with self.lock:
            self.loads.append((threading.get_ident(), self.account.revision))
            return self.account

    def cas(self, expected_revision, new_account):
        first = not getattr(self.local, 'seen', False)
        self.local.seen = True
        if first and self.barrier is not None:
            self.barrier.wait(timeout=5)
        with self.lock:
            won = self.account.revision == expected_revision
            if won:
                self.account = new_account
            self.swaps.append((threading.get_ident(), first, expected_revision, won))
            return won

    def contender(self, command, attempts=3):
        return lambda: cq.commit(self.load, self.cas, OWNER_A, command, attempts)


def run_parallel(*callables):
    outcomes = [None] * len(callables)

    def runner(index, fn):
        try:
            outcomes[index] = ('ok', fn())
        except BaseException as error:  # handed to the test, not swallowed
            outcomes[index] = ('err', error)
    threads = [threading.Thread(target=runner, args=(i, fn), daemon=True) for i, fn in enumerate(callables)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(15)
    if any(thread.is_alive() for thread in threads) or any(o is None for o in outcomes):
        raise AssertionError('contender did not finish')
    return outcomes


def split(outcomes):
    return [o[1] for o in outcomes if o[0] == 'ok'], [o[1] for o in outcomes if o[0] == 'err']


class ConcurrencyTests(Base):
    def first_swaps(self, store):
        return [s for s in store.swaps if s[1]]

    def test_two_same_revision_contenders_one_initial_commit_and_total_never_exceeds_allowance(self):
        base = fill(cq.new_account(OWNER_A), 11)  # 300,000 left
        store = SyncedStore(base, parties=2)
        oks, errors = split(run_parallel(store.contender(res(1, 200_000)), store.contender(res(2, 200_000))))
        self.assertEqual((len(oks), len(errors)), (2, 0))
        self.assertEqual(sorted(o.decision.reserved_ms for o in oks), [100_000, 200_000])  # loser re-granted less
        first = self.first_swaps(store)
        self.assertEqual({s[2] for s in first}, {base.revision})
        self.assertEqual(sorted(s[3] for s in first), [False, True])
        loser = next(tid for tid, _, _, won in first if not won)
        self.assertEqual([rev for tid, rev in store.loads if tid == loser], [11, 12])
        self.assertEqual(store.account.revision, 13)
        summary = cq.period_summary(store.account, *P1)
        self.assertEqual((summary.outstanding_reserved_ms, summary.available_ms), (FREE, 0))

    def test_loser_is_denied_when_nothing_remains(self):
        base = fill(cq.new_account(OWNER_A), 11)
        store = SyncedStore(base, parties=2)
        oks, errors = split(run_parallel(store.contender(res(1, CHUNK)), store.contender(res(2, CHUNK))))
        self.assertEqual((len(oks), len(errors)), (1, 1))
        self.assertIsInstance(errors[0], cq.QuotaExceeded)
        self.assertEqual(errors[0].code, 'quota_exhausted')
        self.assertEqual(store.account.revision, 12)
        self.assertEqual(cq.period_summary(store.account, *P1).available_ms, 0)

    def test_duplicate_payload_race_commits_once(self):
        store = SyncedStore(cq.new_account(OWNER_A), parties=2)
        command = res(1, 100_000)
        oks, errors = split(run_parallel(store.contender(command), store.contender(command)))
        self.assertEqual((len(oks), len(errors)), (2, 0))
        self.assertEqual(sorted(o.changed for o in oks), [False, True])
        self.assertEqual(oks[0].decision, oks[1].decision)
        self.assertEqual(store.account.revision, 1)
        self.assertEqual(len(store.swaps), 2)  # the loser replayed without writing again
        self.assertEqual(cq.period_summary(store.account, *P1).outstanding_reserved_ms, 100_000)

    def test_changed_payload_race_conflicts_once(self):
        store = SyncedStore(cq.new_account(OWNER_A), parties=2)
        oks, errors = split(run_parallel(store.contender(res(1, 100_000)), store.contender(res(1, 200_000))))
        self.assertEqual((len(oks), len(errors)), (1, 1))
        self.assertEqual(errors[0].code, 'idempotency_conflict')
        self.assertEqual(store.account.revision, 1)
        self.assertEqual(store.account.captures[0].reserved_ms, oks[0].decision.reserved_ms)

    def test_cross_period_rebind_race_conflicts_once(self):
        store = SyncedStore(cq.new_account(OWNER_A), parties=2)
        oks, errors = split(run_parallel(store.contender(res(1, 100_000)),
                                         store.contender(res(1, 100_000, period=P2, at=1_500_000))))
        self.assertEqual((len(oks), len(errors)), (1, 1))
        self.assertEqual(errors[0].code, 'idempotency_conflict')
        self.assertEqual(len(store.account.periods), 1)

    def test_end_versus_recover_race_settles_once_atomically(self):
        base = started([('start', 0), ('checkpoint', 20_000)])
        for _ in range(5):  # either terminal path may win; both must behave
            store = SyncedStore(base, parties=2)
            oks, errors = split(run_parallel(store.contender(end(1, 3, 50_000)), store.contender(rec(1))))
            self.assertEqual((len(oks), len(errors)), (1, 1))
            self.assertEqual(errors[0].code, 'capture_closed')
            winner = oks[0].decision
            self.assertEqual(winner.status, 'settled')
            self.assertEqual(winner.charged_ms, 50_000 if winner.kind == 'event' else 20_000)
            self.assertEqual(store.account.revision, base.revision + 1)  # exactly one commit
            summary = cq.period_summary(store.account, *P1)
            self.assertEqual((summary.settled_ms, summary.outstanding_reserved_ms), (winner.charged_ms, 0))
            self.assertEqual(summary.available_ms, FREE - winner.charged_ms)
            first = self.first_swaps(store)
            self.assertEqual({s[2] for s in first}, {base.revision})
            self.assertEqual(sorted(s[3] for s in first), [False, True])

    def test_two_different_ends_for_the_same_sequence_conflict(self):
        base = started([('start', 0)])
        store = SyncedStore(base, parties=2)
        oks, errors = split(run_parallel(store.contender(end(1, 2, 50_000, 'stopped')),
                                         store.contender(end(1, 2, 50_000, 'interrupted'))))
        self.assertEqual((len(oks), len(errors)), (1, 1))
        self.assertEqual(errors[0].code, 'idempotency_conflict')
        self.assertEqual(store.account.revision, base.revision + 1)

    def test_eight_contenders_commit_at_most_the_allowed_total(self):
        base = fill(cq.new_account(OWNER_A), 9)  # 900,000 left: exactly three full grants
        store = SyncedStore(base, parties=8)
        oks, errors = split(run_parallel(*[store.contender(res(i + 1, CHUNK), attempts=8) for i in range(8)]))
        self.assertEqual((len(oks), len(errors)), (3, 5))
        self.assertTrue(all(isinstance(e, cq.QuotaExceeded) for e in errors))
        first = self.first_swaps(store)
        self.assertEqual(len(first), 8)
        self.assertEqual({s[2] for s in first}, {base.revision})
        self.assertEqual(sum(1 for s in first if s[3]), 1)
        self.assertEqual(sum(1 for s in store.swaps if s[3]), 3)
        self.assertEqual(store.account.revision, 12)
        summary = cq.period_summary(store.account, *P1)
        self.assertEqual(summary.settled_ms + summary.outstanding_reserved_ms, FREE)
        checked(store.account)

    def test_bounded_retries(self):
        class AlwaysLose:
            def __init__(self):
                self.account, self.loads, self.swaps = cq.new_account(OWNER_A), 0, 0

            def load(self):
                self.loads += 1
                return self.account

            def cas(self, expected, new):
                self.swaps += 1
                return False
        store = AlwaysLose()
        self.assertCode(cq.CommitConflict, 'cas_exhausted', cq.commit, store.load, store.cas, OWNER_A,
                        res(1), 3)
        self.assertEqual((store.loads, store.swaps), (3, 3))
        self.assertEqual(store.account.revision, 0)

    def test_lost_swap_reloads_recomputes_then_commits(self):
        class OneInterloper(SyncedStore):
            def cas(self, expected, new):
                if not self.swaps:
                    self.account = do(self.account, res(2, 50_000)).account  # a competing writer
                    self.swaps.append(None)
                    return False
                return super().cas(expected, new)
        store = OneInterloper(cq.new_account(OWNER_A))
        outcome = cq.commit(store.load, store.cas, OWNER_A, res(1, 100_000))
        self.assertEqual((outcome.base_revision, store.account.revision), (1, 2))
        self.assertEqual(cq.period_summary(store.account, *P1).outstanding_reserved_ms, 150_000)

    def test_exact_retry_through_commit_never_writes(self):
        store = SyncedStore(cq.new_account(OWNER_A))
        cq.commit(store.load, store.cas, OWNER_A, res(1, 100))
        writes = len(store.swaps)
        again = cq.commit(store.load, store.cas, OWNER_A, res(1, 100))
        self.assertFalse(again.changed)
        self.assertEqual(len(store.swaps), writes)

    def test_commit_argument_and_store_contract_checks(self):
        store = SyncedStore(cq.new_account(OWNER_A))
        for attempts in (0, 17, True, 1.5, None):
            self.assertRaises(cq.InvalidInput, cq.commit, store.load, store.cas, OWNER_A, res(1), attempts)
        self.assertRaises(cq.OwnerMismatch, cq.commit, store.load, store.cas, OWNER_B, res(1))
        self.assertEqual(store.swaps, [])
        self.assertRaises(cq.InvalidInput, cq.commit, store.load, lambda e, n: 1, OWNER_A, res(1))
        other = cq.new_account(OWNER_B)
        self.assertRaises(cq.OwnerMismatch, cq.commit, lambda: other, store.cas, OWNER_A, res(1))
        self.assertRaises(cq.InvalidInput, cq.commit, lambda: 'junk', store.cas, OWNER_A, res(1))


class IsolationTests(Base):
    def test_module_imports_only_pure_standard_modules(self):
        tree = ast.parse(Path(cq.__file__).read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {alias.name.split('.')[0] for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported.add((node.module or '').split('.')[0])
        self.assertLessEqual(imported, {'dataclasses', 'types', 'uuid'})

    def test_no_notes_chat_or_ledger_api_and_no_existing_module_imports_it(self):
        public = [name for name in dir(cq) if not name.startswith('_')]
        for fragment in ('note', 'chat', 'delete', 'ledger', 'provider', 'admission'):
            self.assertFalse([n for n in public if fragment in n.lower()], fragment)
        backend = Path(cq.__file__).parent
        for path in backend.glob('*.py'):
            if path.name in ('capture_quota.py', 'test_capture_quota.py'):
                continue
            text = path.read_text(errors='replace')
            self.assertNotIn('import capture_quota', text, path.name)
            self.assertNotIn('from capture_quota', text, path.name)


if __name__ == '__main__':
    unittest.main()
