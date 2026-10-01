"""Pure session and lease contract for the personal agent harness (H1a).

No I/O, authentication, consent proof, persistence or global state, and not yet
wired into any runtime path. A trusted server integration supplies the
authenticated owner, verified user capture starts and durable control state;
this module only decides whether pending work may still emit. Every transition
returns a new immutable Session.
"""
from dataclasses import dataclass, replace
import math

OK = 'ok'
MAIN_CHAT, CAPTURE_LIVE = 'main_chat', 'capture_live'
REPLY, CUE, FOLLOWUP = 'reply', 'cue', 'followup'
ON, OFF, UNKNOWN = 'on', 'off', 'unknown'
ACTIVE, PAUSED, STOPPED = 'active', 'paused', 'stopped'
QUIET, CAPTURE_START, PAUSE, RESUME, STOP, BACKGROUND, REVOKE = (
    'quiet', 'capture_start', 'pause', 'resume', 'stop', 'background', 'revoke')

# Proposal §8.1.1: the transitions each lease kind survives. Restart is modelled
# by restore_session and invalidates every earlier lease. Only a reviewed O3
# decision may add a reply row; cues and follow-ups never survive a transition.
SURVIVES = {REPLY: frozenset({QUIET}), CUE: frozenset(), FOLLOWUP: frozenset()}
FLOOR_FIELDS = {REPLY: 'reply_floor', CUE: 'cue_floor', FOLLOWUP: 'followup_floor'}


class Denied(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Capture:
    session_id: str
    state: str = ACTIVE
    resume_revision: int | None = None


@dataclass(frozen=True)
class Session:
    owner: str
    epoch: int
    reply_floor: int   # each floor is the epoch of the last transition that kind does not survive
    cue_floor: int
    followup_floor: int
    mode: str = MAIN_CHAT
    capture: Capture | None = None
    quiet_capture: str = UNKNOWN
    quiet_main: str = UNKNOWN
    foreground: bool = False
    chat_revision: int = 0
    revoked: bool = False


@dataclass(frozen=True)
class Lease:
    owner: str
    kind: str
    epoch: int
    mode: str
    binding: str | None   # capture id, UNKNOWN, or None when unbound
    issued_at: float
    deadline: float
    revision: int | None = None   # transcript revision for cues, chat revision for follow-ups


def restore_session(owner, epoch_floor, *, quiet_capture=UNKNOWN, quiet_main=UNKNOWN, capture=None):
    """State at process start or after restart, from trusted durable values.

    `epoch_floor` must be at least the highest epoch ever issued for this owner.
    Missing or unreadable values are UNKNOWN. A capture is restored only as
    durably recorded: this never creates consent or resumes a paused capture.
    The client counts as background until it reconnects.
    """
    _identifier(owner)
    if not _whole(epoch_floor): raise ValueError('epoch_floor must be a non-negative integer')
    if capture is not None:
        _identifier(capture.session_id)
        if capture.state not in (ACTIVE, PAUSED, STOPPED): capture = replace(capture, state=UNKNOWN)
    live = capture is not None and capture.state != STOPPED
    epoch = epoch_floor + 1
    return Session(owner, epoch, epoch, epoch, epoch, mode=CAPTURE_LIVE if live else MAIN_CHAT,
                   capture=capture, quiet_capture=_known(quiet_capture), quiet_main=_known(quiet_main))


def quiet(session):
    return _advance(session, QUIET, quiet_capture=ON, quiet_main=ON)


def user_started_capture(session, owner, capture_id, verified):
    """`verified` is the integration's proof of an owner-scoped user start (proposal §7.4)."""
    _identifier(capture_id)
    if owner != session.owner: raise Denied('owner_mismatch')
    if verified is not True: raise Denied('capture_unverified')
    if session.capture is not None and session.capture.state != STOPPED: raise Denied('capture_already_bound')
    return _advance(session, CAPTURE_START, mode=CAPTURE_LIVE, capture=Capture(capture_id), quiet_capture=OFF)


def user_paused(session, owner, capture_id):
    _require_capture(session, owner, capture_id, (ACTIVE, UNKNOWN))
    return _advance(session, PAUSE, capture=replace(session.capture, state=PAUSED))


def user_resumed(session, owner, capture_id, latest_revision):
    """Cues after resume need a transcript revision newer than `latest_revision`."""
    _require_capture(session, owner, capture_id, (PAUSED, UNKNOWN))
    if not _whole(latest_revision): raise ValueError('latest_revision must be a non-negative integer')
    return _advance(session, RESUME, capture=replace(session.capture, state=ACTIVE, resume_revision=latest_revision))


def user_stopped(session, owner, capture_id):
    _require_capture(session, owner, capture_id, (ACTIVE, PAUSED, UNKNOWN))
    return _advance(session, STOP, mode=MAIN_CHAT, capture=replace(session.capture, state=STOPPED))


def backgrounded(session):
    return _advance(session, BACKGROUND, foreground=False)


def revoked(session):
    return _advance(session, REVOKE, revoked=True)


def reconnected(session):
    """Foreground return. Never changes capture state, Quiet or consent."""
    if session.revoked: raise Denied('revoked')
    return replace(session, foreground=True)


def chat_changed(session):
    """A main-chat turn was committed or invalidated."""
    return replace(session, chat_revision=session.chat_revision + 1)


def issue_reply(session, now, ttl, live_capture=None):
    if live_capture is None: binding = None
    elif session.capture is not None and live_capture == session.capture.session_id: binding = live_capture
    else: binding = UNKNOWN
    return _issue(session, REPLY, now, ttl, binding, None, {})


def issue_cue(session, now, ttl, revision, *, pending_direct_turn):
    if not _whole(revision): raise ValueError('revision must be a non-negative integer')
    binding = session.capture.session_id if session.capture is not None else None
    return _issue(session, CUE, now, ttl, binding, revision, dict(pending_direct_turn=pending_direct_turn))


def issue_followup(session, now, ttl, *, pending_direct_turn, anchor_complete):
    return _issue(session, FOLLOWUP, now, ttl, None, session.chat_revision,
                  dict(pending_direct_turn=pending_direct_turn, anchor_complete=anchor_complete))


def may_emit(session, lease, now, *, pending_direct_turn=None, anchor_complete=None):
    """Return OK or a denial reason; run before every content event and inside the commit.

    Unsolicited work needs the integration's current chat state; None means unknown
    and denies. Credential, evidence-fingerprint and budget checks remain
    integration obligations (H1b) and are not replaced by this gate.
    """
    if lease.kind not in SURVIVES: return 'kind_invalid'
    if not all(map(_finite, (now, lease.issued_at, lease.deadline))) or now < lease.issued_at: return 'clock_invalid'
    if lease.owner != session.owner: return 'owner_mismatch'
    if session.revoked: return 'revoked'
    if lease.epoch > session.epoch: return 'epoch_invalid'
    if lease.epoch < getattr(session, FLOOR_FIELDS[lease.kind]): return 'epoch_changed'
    if now > lease.deadline: return 'deadline_exceeded'
    reason = _settled(session)
    if reason != OK: return reason
    if lease.kind == REPLY:
        return OK if lease.binding is None else _active_binding(session, lease.binding)
    if lease.mode != session.mode: return 'mode_changed'
    if session.foreground is not True: return 'background'
    if pending_direct_turn is None: return 'chat_state_unknown'
    if pending_direct_turn is not False: return 'chat_busy'
    return _cue(session, lease) if lease.kind == CUE else _followup(session, lease, anchor_complete)


def _settled(session):
    """Deny every lease kind, unbound replies included, unless the session is plainly
    in main chat (no live capture) or in an active capture. Pause and unknown state
    allow no output in H1a; any exception is a reviewed H1b change."""
    capture = session.capture
    if capture is not None and capture.state not in (ACTIVE, PAUSED, STOPPED): return 'capture_unknown'
    if capture is not None and capture.state == PAUSED: return 'capture_paused'
    live = capture is not None and capture.state == ACTIVE
    if session.mode != (CAPTURE_LIVE if live else MAIN_CHAT): return 'mode_invalid'
    return OK


def _cue(session, lease):
    if session.capture is None: return 'no_capture'
    if lease.mode != CAPTURE_LIVE: return 'mode_changed'
    reason = _active_binding(session, lease.binding)
    if reason != OK: return reason
    if session.quiet_capture != OFF: return 'quiet'
    resumed = session.capture.resume_revision
    if not _whole(lease.revision) or (resumed is not None and lease.revision <= resumed): return 'stale_cutoff'
    return OK


def _followup(session, lease, anchor_complete):
    if lease.mode != MAIN_CHAT: return 'mode_changed'
    if lease.binding is not None: return 'capture_changed'
    if session.capture is not None and session.capture.state != STOPPED: return 'capture_present'
    if session.quiet_main != OFF: return 'quiet'
    if lease.revision != session.chat_revision or anchor_complete is not True: return 'chat_changed'
    return OK


def _active_binding(session, binding):
    capture = session.capture
    if capture is None or binding in (None, UNKNOWN): return 'capture_unknown'
    if capture.session_id != binding: return 'capture_changed'
    if capture.state != ACTIVE: return f'capture_{capture.state}'
    return OK


def _issue(session, kind, now, ttl, binding, revision, context):
    if not (_finite(now) and _finite(ttl) and ttl > 0): raise ValueError('finite now and positive ttl required')
    deadline = now + ttl
    if not (_finite(deadline) and deadline > now): raise ValueError('deadline must be finite and later than now')
    lease = Lease(session.owner, kind, session.epoch, session.mode, binding, now, deadline, revision)
    reason = may_emit(session, lease, now, **context)
    if reason != OK: raise Denied(reason)
    return lease


def _advance(session, transition, **changes):
    if session.revoked: raise Denied('revoked')
    epoch = session.epoch + 1
    floors = {field: epoch for kind, field in FLOOR_FIELDS.items() if transition not in SURVIVES[kind]}
    return replace(session, epoch=epoch, **floors, **changes)


def _require_capture(session, owner, capture_id, states):
    if owner != session.owner: raise Denied('owner_mismatch')
    capture = session.capture
    if capture is None or capture.session_id != capture_id: raise Denied('capture_foreign')
    if capture.state not in states: raise Denied(f'capture_{capture.state}')


def _identifier(value):
    if not isinstance(value, str) or not value or value == UNKNOWN: raise ValueError('identifier required')


def _known(value):
    return value if value in (ON, OFF) else UNKNOWN


def _whole(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _finite(value):
    if not isinstance(value, (int, float)) or isinstance(value, bool): return False
    try: return math.isfinite(value)
    except OverflowError: return False
