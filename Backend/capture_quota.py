"""Customer capture-time quota and reservation contract (B1). Pure and deterministic.

Scope. Capture admission only: integer milliseconds of customer capture time per
owner and entitlement period. It is NOT an LLM/tool safety allowance and is
separate from the operator provider-cost ledger in admission.py. It never reads,
deletes or blocks notes or chat; it only returns capture admission decisions.
Free is 3,600,000 ms and Plus is 72,000,000 ms per period (same core agent).
There is no clock, randomness, I/O, database or global mutable state.

State. One immutable QuotaAccount per owner spans ALL periods and is the single
compare-and-swap unit. Periods are append-only and nonoverlapping; history is
never reset, removed or backfilled. Admission chronology: a NEW capture may only
reserve in the latest recorded period (or append a newer, nonoverlapping one); a
new reserve naming an older recorded period, e.g. from a stale injected time, is
rejected with `period_backfill` and changes nothing. This is chronology only, not
a reset/upgrade policy or a clock. Exact retries (looked up first) still return the
original decision, and existing captures of older periods keep accepting events and
settling against their own period. Every accepted command adds exactly one
OperationRecord and one revision, and the account can always be rebuilt with
`replay`. `settled + outstanding_reserved <= PLAN allowance` holds for every
period in every accepted account. Loaded or reconstructed accounts are fully
re-validated (by replaying their log) at the public `apply`, `commit`,
`period_summary` and `QuotaAccount` boundaries, so a forged account cannot yield
an accepted candidate.

Idempotency. Keys are scoped to the owner's account: reserve (capture,'reserve',0),
event (capture,'event',sequence), recover (capture,'recover',0). The stored
command is the full validated fingerprint (for reserve: capture, entitlement
owner/plan/bounds, wall time and amount). An exact retry returns the original
stored Decision with the account unchanged, even after settlement or rollover.
ANY changed payload for a key conflicts, so a capture cannot be re-bound to
another period or plan. Denials are not recorded and are re-evaluated on retry.

Reservation. Before capture the caller reserves; the grant is min(requested,
available) when available > 0, else `quota_exhausted`. There is no per-request cap
here; any cap is a runtime policy outside this contract.

Time. Capture time is a TRUSTED, monotonic offset relative to the capture,
independent of the entitlement's wall-clock bounds (which only decide the period
at reserve time). Only explicit events bill: start (reserved->active), pause
(closes the interval), resume (paused->active), checkpoint (acknowledges the
active interval) and end. Never audio amplitude or forwarded bytes: composer
dictation forwards silent meeting frames, so those totals include pause. Sequences
are contiguous from 1 and offsets non-decreasing. No implicit resume exists.
Connection preparation before `start` and finalization after `end` are not billed.

Settlement is atomic with termination. `end` (reason stopped / failed /
interrupted) and `Recover` each close the interval and settle in the SAME revision:
billed = min(measured active time, reserved), the rest is released, and
`overrun_ms` reports measured time beyond the reservation (measured time stays
recorded, only billing is capped). A terminal end/recover race commits once; the
loser gets `capture_closed`. Failure before start releases zero-billed quota.
Overrun acceptance is bookkeeping only: stopping at the reservation is a future
runtime obligation and the decision grants NO permission to capture beyond it.

Emitter obligations (not wired here). `end` must come from a trusted server-side
observer that knows the real terminal offset (including reason `interrupted` when
the offset is known). `Recover` is for when no reliable terminal offset exists
(crash, restart, lost connection): it takes no wall time or sequence from the
failed caller and closes at the LAST ACKNOWLEDGED offset, inventing no
unacknowledged tail, so checkpoint cadence bounds what a crash can lose. Clients
must never be able to emit either directly.

Future integration gates (not solved here): owner IDs must be the authenticated
server-side canonical UUID (any other scheme must be mapped before calling);
entitlements must be server-verified; upgrade/downgrade/grace/refund/reset policy
is deliberately deferred (a changed snapshot fails closed); `commit` needs a
durable atomic CAS store with log retention/compaction and backups that never
roll usage back; validation replays the whole log, so its cost grows with log size
and needs a bound or snapshotting before production volume.
"""
from dataclasses import dataclass, fields
from types import MappingProxyType
import uuid

MAX_MS = 2 ** 63 - 1
PLAN_ALLOWANCE_MS = MappingProxyType({'free': 3_600_000, 'plus': 72_000_000})
MAX_EVENTS_PER_CAPTURE = 1024
DEFAULT_ATTEMPTS = 3
MAX_ATTEMPTS = 16
EVENT_KINDS = ('start', 'pause', 'resume', 'checkpoint', 'end')
END_REASONS = ('stopped', 'failed', 'interrupted')
CLOSE_REASONS = END_REASONS + ('recovered',)
STATUSES = ('reserved', 'active', 'paused', 'settled')
DECISION_KINDS = ('reserve', 'event', 'recover')


class QuotaError(Exception):
    """Base error. `.code` is a stable, content-free reason."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


class _Coded(QuotaError):
    CODES = ()

    def __init__(self, code):
        if code not in self.CODES:
            raise ValueError('unknown error code')
        super().__init__(code)


class InvalidInput(QuotaError):
    def __init__(self):
        super().__init__('invalid_input')


class OwnerMismatch(QuotaError):
    def __init__(self):
        super().__init__('owner_mismatch')


class EntitlementChanged(QuotaError):
    def __init__(self):
        super().__init__('entitlement_changed')


class IdempotencyConflict(QuotaError):
    def __init__(self):
        super().__init__('idempotency_conflict')


class InvariantViolation(QuotaError):
    def __init__(self):
        super().__init__('invariant_violation')


class CommitConflict(QuotaError):
    def __init__(self):
        super().__init__('cas_exhausted')


class PeriodError(_Coded):
    CODES = ('outside_period', 'period_overlap', 'period_backfill')


class CaptureConflict(_Coded):
    CODES = ('unknown_capture', 'capture_closed')


class EventRejected(_Coded):
    CODES = ('sequence_gap', 'sequence_conflict', 'time_regression', 'invalid_transition', 'event_limit')


class QuotaExceeded(QuotaError):
    """No allowance is available in the period (`quota_exhausted`)."""

    def __init__(self, remaining_ms=0):
        super().__init__('quota_exhausted')
        self.remaining_ms = remaining_ms


# --- validation helpers -----------------------------------------------------

def _ms(value, low=0, high=MAX_MS):
    """Strict integer: rejects bool, float, int subclasses and out-of-range values."""
    if type(value) is not int or not low <= value <= high:
        raise InvalidInput()
    return value


def _uuid(value):
    """Canonical lowercase UUID only; never an email, token or other scheme."""
    if type(value) is not str or len(value) != 36:
        raise InvalidInput()
    try:
        parsed = uuid.UUID(value)
    except ValueError:
        raise InvalidInput() from None
    if str(parsed) != value:
        raise InvalidInput()
    return value


def _member(value, allowed):
    if type(value) is not str or value not in allowed:
        raise InvalidInput()
    return value


# --- public value types -----------------------------------------------------

@dataclass(frozen=True)
class Entitlement:
    """Trusted, server-verified plan for one owner over [period_start_ms, period_end_ms)."""
    owner: str
    plan: str
    period_start_ms: int
    period_end_ms: int

    def __post_init__(self):
        _uuid(self.owner)
        _member(self.plan, PLAN_ALLOWANCE_MS)
        _ms(self.period_start_ms)
        _ms(self.period_end_ms, low=1)
        if self.period_start_ms >= self.period_end_ms:
            raise InvalidInput()


@dataclass(frozen=True)
class Reserve:
    capture_id: str
    entitlement: Entitlement
    requested_at_ms: int  # wall time; must lie inside the entitlement period
    requested_ms: int

    def __post_init__(self):
        _uuid(self.capture_id)
        if not isinstance(self.entitlement, Entitlement):
            raise InvalidInput()
        _ms(self.requested_at_ms)
        _ms(self.requested_ms, low=1)


@dataclass(frozen=True)
class CaptureEvent:
    """Trusted lifecycle fact. `offset_ms` is a trusted monotonic offset relative to the capture."""
    capture_id: str
    sequence: int
    kind: str
    offset_ms: int
    end_reason: object = None  # required for 'end', forbidden otherwise

    def __post_init__(self):
        _uuid(self.capture_id)
        _ms(self.sequence, low=1)
        _member(self.kind, EVENT_KINDS)
        _ms(self.offset_ms)
        if self.kind == 'end':
            _member(self.end_reason, END_REASONS)
        elif self.end_reason is not None:
            raise InvalidInput()


@dataclass(frozen=True)
class Recover:
    """Close and settle at the last acknowledged offset; needs no wall time or sequence."""
    capture_id: str

    def __post_init__(self):
        _uuid(self.capture_id)


@dataclass(frozen=True)
class Decision:
    kind: str
    capture_id: str
    status: str
    reserved_ms: int           # granted reservation
    measured_ms: int           # acknowledged active time (never clamped)
    charged_ms: object         # billed once settled, else None
    released_ms: object        # unused reservation released at settlement, else None
    overrun_ms: int            # measured beyond the reservation (reported, never billed)
    reservation_left_ms: int
    remaining_ms: int          # allowance still available in the period after this command
    committed_revision: int
    period_start_ms: int
    period_end_ms: int
    end_reason: object         # stopped / failed / interrupted / recovered once settled

    def __post_init__(self):
        _member(self.kind, DECISION_KINDS)
        _uuid(self.capture_id)
        _member(self.status, STATUSES)
        for value in (self.reserved_ms, self.measured_ms, self.overrun_ms,
                      self.reservation_left_ms, self.remaining_ms, self.period_start_ms):
            _ms(value)
        _ms(self.period_end_ms, low=1)
        _ms(self.committed_revision, low=1)
        if (self.charged_ms is None) != (self.released_ms is None):
            raise InvalidInput()
        if self.charged_ms is not None:
            _ms(self.charged_ms)
            _ms(self.released_ms)
        if self.end_reason is not None:
            _member(self.end_reason, CLOSE_REASONS)


@dataclass(frozen=True)
class CaptureRecord:
    capture_id: str
    period_start_ms: int
    period_end_ms: int
    requested_at_ms: int
    requested_ms: int
    reserved_ms: int
    status: str
    events: tuple
    end_reason: object
    charged_ms: object

    def __post_init__(self):
        _uuid(self.capture_id)
        _ms(self.period_start_ms)
        _ms(self.period_end_ms, low=1)
        _ms(self.requested_at_ms)
        _ms(self.requested_ms, low=1)
        _ms(self.reserved_ms, low=1, high=self.requested_ms)
        _member(self.status, STATUSES)
        if type(self.events) is not tuple or not all(isinstance(e, CaptureEvent) for e in self.events):
            raise InvalidInput()
        settled = self.status == 'settled'
        if (self.charged_ms is not None) != settled or (self.end_reason is not None) != settled:
            raise InvalidInput()
        if settled:
            _ms(self.charged_ms, high=self.reserved_ms)
            _member(self.end_reason, CLOSE_REASONS)


@dataclass(frozen=True)
class OperationRecord:
    key: tuple
    command: object
    decision: Decision

    def __post_init__(self):
        if type(self.command) not in (Reserve, CaptureEvent, Recover) or type(self.decision) is not Decision:
            raise InvalidInput()
        expected = _key(self.command)
        # Strict: equality alone would accept (capture, 'reserve', False) for (capture, 'reserve', 0).
        if (type(self.key) is not tuple or self.key != expected
                or [type(part) for part in self.key] != [type(part) for part in expected]):
            raise InvalidInput()


@dataclass(frozen=True)
class QuotaAccount:
    """All periods and captures of ONE owner; the compare-and-swap unit.

    Public construction re-validates by replaying the whole operation log, so a
    forged or corrupted account cannot be built through the constructor."""
    owner: str
    revision: int
    periods: tuple     # Entitlement, append-only, ascending and nonoverlapping
    captures: tuple    # CaptureRecord, strictly sorted by capture_id
    operations: tuple  # OperationRecord in commit order; len == revision

    def __post_init__(self):
        _validate_account(self)


@dataclass(frozen=True)
class Outcome:
    account: QuotaAccount
    decision: Decision
    changed: bool        # False for an exact retry: `account` is the input, unchanged
    base_revision: int   # the revision a CAS must still find stored


@dataclass(frozen=True)
class PeriodSummary:
    entitlement: Entitlement
    allowance_ms: int
    settled_ms: int
    outstanding_reserved_ms: int
    available_ms: int
    capture_ids: tuple


# --- internals --------------------------------------------------------------

def _key(command):
    if isinstance(command, Reserve):
        return (command.capture_id, 'reserve', 0)
    if isinstance(command, CaptureEvent):
        return (command.capture_id, 'event', command.sequence)
    return (command.capture_id, 'recover', 0)


_RECORDS = (Entitlement, Reserve, CaptureEvent, Recover, Decision, CaptureRecord, OperationRecord)


# Legitimate nesting is at most 4 levels (account tuple -> record -> tuple/record -> record),
# so this bound rejects self-referencing or absurdly deep forged values before recursion limits.
_MAX_CLEAN_DEPTH = 8


def _clean(value, depth=0):
    """Rebuild a value through its dataclass constructors so a forged one (made with
    object.__new__, a subclass, or bool/float/str in an int slot that merely compares
    equal) cannot skip strict validation. Returns a validated copy. Nesting deeper than
    _MAX_CLEAN_DEPTH (a cycle or a forged chain) is rejected as invalid input."""
    if depth > _MAX_CLEAN_DEPTH:
        raise InvalidInput()
    kind = type(value)
    if kind is tuple:
        return tuple(_clean(item, depth + 1) for item in value)
    if isinstance(value, _RECORDS):
        if kind not in _RECORDS:
            raise InvalidInput()
        return kind(**{f.name: _clean(getattr(value, f.name), depth + 1) for f in fields(kind)})
    return value


def _clean_command(command):
    if type(command) not in (Reserve, CaptureEvent, Recover):
        raise InvalidInput()
    try:
        return _clean(command)
    except (AttributeError, TypeError, KeyError, RecursionError):
        raise InvalidInput() from None


def _trusted_account(owner, revision, periods, captures, operations):
    """Wrap a transition result that was just checked, without re-replaying it."""
    account = object.__new__(QuotaAccount)
    for name, value in (('owner', owner), ('revision', revision), ('periods', periods),
                        ('captures', captures), ('operations', operations)):
        object.__setattr__(account, name, value)
    return account


def _find_capture(captures, capture_id):
    for capture in captures:
        if capture.capture_id == capture_id:
            return capture
    return None


def _find_period(periods, start, end):
    for period in periods:
        if period.period_start_ms == start and period.period_end_ms == end:
            return period
    return None


def _usage(captures, start, end):
    settled = outstanding = 0
    for capture in captures:
        if capture.period_start_ms == start and capture.period_end_ms == end:
            if capture.status == 'settled':
                settled += capture.charged_ms
            else:
                outstanding += capture.reserved_ms
    return settled, outstanding


def _fold(events):
    """(status, closed ms, open-since offset, last acknowledged offset); raises on bad order."""
    status, closed, since, ack = 'reserved', 0, None, None
    for event in events:
        kind, at = event.kind, event.offset_ms
        if kind == 'start' and status == 'reserved':
            status, since, ack = 'active', at, at
        elif kind == 'checkpoint' and status == 'active':
            ack = at
        elif kind == 'pause' and status == 'active':
            closed += at - since
            status, since = 'paused', None
        elif kind == 'resume' and status == 'paused':
            status, since, ack = 'active', at, at
        elif kind == 'end' and status != 'settled':
            if status == 'active':
                closed += at - since  # trusted terminal offset
            status, since = 'settled', None
        else:
            raise EventRejected('invalid_transition')
    return status, closed, since, ack


def _acknowledged(closed, since, ack):
    return closed + (ack - since if since is not None else 0)


def _lookup(account, command):
    key = _key(command)
    for op in account.operations:
        if op.key == key:
            if op.command != command:
                raise IdempotencyConflict()
            return Outcome(account, op.decision, False, account.revision)
    return None


def _finish(account, periods, captures, command, record, kind, measured):
    start, end = record.period_start_ms, record.period_end_ms
    allowance = PLAN_ALLOWANCE_MS[_find_period(periods, start, end).plan]
    settled, outstanding = _usage(captures, start, end)
    if settled + outstanding > allowance:  # accepted-state invariant
        raise InvariantViolation()
    done = record.status == 'settled'
    decision = Decision(
        kind=kind, capture_id=record.capture_id, status=record.status, reserved_ms=record.reserved_ms,
        measured_ms=measured, charged_ms=record.charged_ms,
        released_ms=record.reserved_ms - record.charged_ms if done else None,
        overrun_ms=max(0, measured - record.reserved_ms),
        reservation_left_ms=0 if done else max(0, record.reserved_ms - measured),
        remaining_ms=allowance - settled - outstanding, committed_revision=account.revision + 1,
        period_start_ms=start, period_end_ms=end, end_reason=record.end_reason)
    new_account = _trusted_account(account.owner, account.revision + 1, periods, captures,
                                   account.operations + (OperationRecord(_key(command), command, decision),))
    return Outcome(new_account, decision, True, account.revision)


def _replace_capture(captures, record):
    return tuple(record if c.capture_id == record.capture_id else c for c in captures)


def _settle_record(capture, events, reason, measured):
    return CaptureRecord(capture.capture_id, capture.period_start_ms, capture.period_end_ms,
                         capture.requested_at_ms, capture.requested_ms, capture.reserved_ms,
                         'settled', events, reason, min(measured, capture.reserved_ms))


def _reserve(account, command):
    entitlement = command.entitlement
    start, end = entitlement.period_start_ms, entitlement.period_end_ms
    if not start <= command.requested_at_ms < end:
        raise PeriodError('outside_period')
    periods = account.periods
    known = _find_period(periods, start, end)
    if known is not None:
        if start != periods[-1].period_start_ms:  # chronology: a NEW capture only enters the latest period
            raise PeriodError('period_backfill')
        if known != entitlement:  # same bounds with a different plan: fail closed, no policy
            raise EntitlementChanged()
    else:
        if any(start < p.period_end_ms and p.period_start_ms < end for p in periods):
            raise PeriodError('period_overlap')
        if periods and start < periods[-1].period_end_ms:
            raise PeriodError('period_backfill')
        periods = periods + (entitlement,)
    settled, outstanding = _usage(account.captures, start, end)
    available = PLAN_ALLOWANCE_MS[entitlement.plan] - settled - outstanding
    if available <= 0:
        raise QuotaExceeded(0)
    record = CaptureRecord(command.capture_id, start, end, command.requested_at_ms, command.requested_ms,
                           min(command.requested_ms, available), 'reserved', (), None, None)
    captures = tuple(sorted(account.captures + (record,), key=lambda c: c.capture_id))
    return _finish(account, periods, captures, command, record, 'reserve', 0)


def _event(account, command):
    capture = _find_capture(account.captures, command.capture_id)
    if capture is None:
        raise CaptureConflict('unknown_capture')
    if capture.status == 'settled':
        raise CaptureConflict('capture_closed')
    last = capture.events[-1] if capture.events else None
    last_sequence = last.sequence if last else 0
    if command.sequence <= last_sequence:
        raise EventRejected('sequence_conflict')
    if command.sequence > last_sequence + 1:
        raise EventRejected('sequence_gap')
    if last is not None and command.offset_ms < last.offset_ms:
        raise EventRejected('time_regression')
    events = capture.events + (command,)
    status, closed, since, ack = _fold(events)
    if command.kind != 'end' and len(capture.events) >= MAX_EVENTS_PER_CAPTURE:
        raise EventRejected('event_limit')
    measured = _acknowledged(closed, since, ack)
    if status == 'settled':  # end closes AND settles in this same revision
        record = _settle_record(capture, events, command.end_reason, measured)
    else:
        record = CaptureRecord(capture.capture_id, capture.period_start_ms, capture.period_end_ms,
                               capture.requested_at_ms, capture.requested_ms, capture.reserved_ms,
                               status, events, None, None)
    return _finish(account, account.periods, _replace_capture(account.captures, record),
                   command, record, 'event', measured)


def _recover(account, command):
    capture = _find_capture(account.captures, command.capture_id)
    if capture is None:
        raise CaptureConflict('unknown_capture')
    if capture.status == 'settled':
        raise CaptureConflict('capture_closed')
    _, closed, since, ack = _fold(capture.events)
    measured = _acknowledged(closed, since, ack)  # last acknowledged offset, no invented tail
    record = _settle_record(capture, capture.events, 'recovered', measured)
    return _finish(account, account.periods, _replace_capture(account.captures, record),
                   command, record, 'recover', measured)


def _step(account, command):
    """Pure transition on an already-validated account; the only place accounting happens."""
    if isinstance(command, Reserve):
        if command.entitlement.owner != account.owner:
            raise OwnerMismatch()
    elif not isinstance(command, (CaptureEvent, Recover)):
        raise InvalidInput()
    hit = _lookup(account, command)
    if hit is not None:
        return hit
    if isinstance(command, Reserve):
        return _reserve(account, command)
    if isinstance(command, CaptureEvent):
        return _event(account, command)
    return _recover(account, command)


def _validate_account(account):
    _uuid(account.owner)
    _ms(account.revision)
    if (type(account.periods) is not tuple or type(account.captures) is not tuple
            or type(account.operations) is not tuple):
        raise InvalidInput()
    if account.revision != len(account.operations):
        raise InvariantViolation()
    try:
        # Every stored record is rebuilt through its strict constructors, then the
        # WHOLE history (key, command, decision), periods and captures must equal
        # what replaying the stored commands from an empty account produces.
        periods, captures, operations = (_clean(account.periods), _clean(account.captures),
                                         _clean(account.operations))
        if (not all(type(p) is Entitlement for p in periods)
                or not all(type(c) is CaptureRecord for c in captures)
                or not all(type(o) is OperationRecord for o in operations)):
            raise InvalidInput()
        work = _trusted_account(account.owner, 0, (), (), ())
        for op in operations:
            outcome = _step(work, op.command)
            if not outcome.changed:
                raise InvariantViolation()
            work = outcome.account
        if work.operations != operations or work.periods != periods or work.captures != captures:
            raise InvariantViolation()
        for period in work.periods:
            settled, outstanding = _usage(work.captures, period.period_start_ms, period.period_end_ms)
            if settled + outstanding > PLAN_ALLOWANCE_MS[period.plan]:
                raise InvariantViolation()
    except QuotaError:
        raise InvariantViolation() from None
    except (TypeError, AttributeError, ValueError, KeyError, RecursionError):
        raise InvariantViolation() from None


def _apply_trusted(account, owner, command):
    if _uuid(owner) != account.owner:
        raise OwnerMismatch()
    return _step(account, command)


# --- public API -------------------------------------------------------------

def new_account(owner):
    """Empty account (revision 0) for an authenticated owner UUID."""
    return QuotaAccount(owner, 0, (), (), ())


def apply(account, owner, command):
    """Pure transition. Fully validates `account` first; never mutates it.

    Returns Outcome(changed=False) with the original stored Decision for an exact
    retry. Otherwise returns the next account (revision + 1) and its Decision; the
    caller must persist it only if the stored revision still equals base_revision.
    """
    if type(account) is not QuotaAccount:
        raise InvalidInput()
    command = _clean_command(command)  # a forged command cannot skip constructor validation
    if _uuid(owner) != account.owner:
        raise OwnerMismatch()
    _validate_account(account)
    return _apply_trusted(account, owner, command)


def commit(load, cas, owner, command, attempts=DEFAULT_ATTEMPTS):
    """Bounded compare-and-swap loop over an injected store.

    `load()` returns the owner's current QuotaAccount. `cas(expected_revision,
    new_account)` must atomically replace the stored account only if its revision
    still equals `expected_revision` and return exactly True, else exactly False.
    Every loaded account is validated by `apply` before anything is written. Exact
    retries return the original decision without writing; lost swaps reload and
    recompute (no provider call happens here), at most `attempts` times.
    """
    _ms(attempts, low=1, high=MAX_ATTEMPTS)
    for _ in range(attempts):
        outcome = apply(load(), owner, command)
        if not outcome.changed:
            return outcome
        if outcome.account.revision != outcome.base_revision + 1:
            raise InvariantViolation()
        swapped = cas(outcome.base_revision, outcome.account)
        if swapped is True:
            return outcome
        if swapped is not False:
            raise InvalidInput()
    raise CommitConflict()


def replay(owner, accepted):
    """Deterministically reconstruct an account from accepted commands or OperationRecords."""
    account = new_account(owner)
    for item in accepted:
        recorded = type(item) is OperationRecord
        if recorded:
            try:
                item = _clean(item)
            except (AttributeError, TypeError, KeyError, RecursionError):
                raise InvalidInput() from None
        outcome = _apply_trusted(account, owner, _clean_command(item.command if recorded else item))
        if not outcome.changed or (recorded and outcome.decision != item.decision):
            raise InvariantViolation()  # an accepted log has no duplicates or divergent results
        account = outcome.account
    return account


def period_summary(account, period_start_ms, period_end_ms):
    """Allowance, settled, outstanding reserved and available for one recorded period."""
    if type(account) is not QuotaAccount:
        raise InvalidInput()
    _validate_account(account)
    period = _find_period(account.periods, _ms(period_start_ms), _ms(period_end_ms, low=1))
    if period is None:
        raise PeriodError('outside_period')
    settled, outstanding = _usage(account.captures, period_start_ms, period_end_ms)
    allowance = PLAN_ALLOWANCE_MS[period.plan]
    ids = tuple(c.capture_id for c in account.captures
                if (c.period_start_ms, c.period_end_ms) == (period_start_ms, period_end_ms))
    return PeriodSummary(period, allowance, settled, outstanding, allowance - settled - outstanding, ids)
