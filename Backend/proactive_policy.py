"""Local scheduling contract. No sockets, inference, storage, or UI side effects."""
from dataclasses import dataclass, field
import copy
import hashlib
import json
import math
from admission import Rejected
from memory_store import identifier, validate_source


def cutoff(source):
    validate_source(source)
    if source['completed'] or source.get('origin') is not None:
        raise Rejected('proactive_requires_live_recording')
    return hashlib.sha256(json.dumps(source, sort_keys=True).encode()).hexdigest()


def extends(previous, current):
    """Only additive speech can retain a short-lived analysis lease."""
    if previous is None:return False
    for key in ('session_id','captured_at','timezone','completed','origin'):
        if previous.get(key)!=current.get(key):return False
    old,new=previous['passages'],current['passages']
    if len(new)<len(old):return False
    for index,p in enumerate(old):
        q=new[index]
        if p==q:continue
        if index!=len(old)-1:return False
        if any(p[k]!=q[k] for k in ('id','start','speakers')):return False
        if q['duration']<p['duration'] or not q['text'].startswith(p['text']):return False
    return True


@dataclass(frozen=True)
class Attempt:
    owner: str
    capture: str
    generation: int
    cutoff: str
    started: float


@dataclass
class ProactivePolicy:
    """Caller supplies monotonic time and only stable transcript updates.

    Quiet/background/stop invalidate a lease even if a provider cannot cancel.
    Rewriting prior text invalidates an old result; additive speech retains the
    original deadline. There is no queued backlog.
    """
    interval: float = 20.
    cooldown: float = 60.
    deadline: float = 15.
    max_attempts: int = 12
    owner: str | None = None
    capture: str | None = None
    generation: int = 0
    enabled: bool = False
    foreground: bool = True
    latest: str | None = None
    latest_source: dict | None = None
    attempted: set = field(default_factory=set)
    delivered: set = field(default_factory=set)
    pending: Attempt | None = None
    last_attempt: float = -math.inf
    last_delivery: float = -math.inf
    attempts: int = 0

    def start(self, owner, capture):
        identifier(owner); identifier(capture)
        self.owner, self.capture = owner, capture
        self.generation += 1
        self.enabled = True
        self.latest = None
        self.latest_source = None
        self.attempted.clear(); self.delivered.clear()
        self.pending = None
        self.last_attempt = self.last_delivery = -math.inf
        self.attempts = 0

    def quiet(self):
        self.enabled = False
        self.invalidate()

    def stop(self):
        self.quiet()
        self.capture = None

    def invalidate(self):
        self.generation += 1
        self.pending = None

    def background(self):
        self.foreground = False
        self.invalidate()

    def resume(self):
        # Wait for NEW context; returning never replays the previous cutoff.
        self.foreground = True
        if self.latest: self.attempted.add(self.latest)

    def observe(self, source, now):
        if not math.isfinite(now): raise ValueError('Monotonic time required')
        digest = cutoff(source)
        if source['session_id'] != self.capture:
            raise Rejected('proactive_capture_changed')
        if digest != self.latest:
            additive = extends(self.latest_source, source)
            self.latest = digest
            self.latest_source = copy.deepcopy(source)
            if self.pending and not additive: self.invalidate()
        if (not self.enabled or not self.foreground or not source['passages'] or self.pending
                or digest in self.attempted or self.attempts >= self.max_attempts
                or now-self.last_attempt < self.interval or now-self.last_delivery < self.cooldown):
            return None
        lease = Attempt(self.owner, self.capture, self.generation, digest, now)
        self.pending = lease
        self.attempted.add(digest)
        self.last_attempt = now
        self.attempts += 1
        return lease

    def valid(self, lease, now):
        return (self.pending == lease and self.enabled and self.foreground
                and self.owner == lease.owner and self.capture == lease.capture
                and self.generation == lease.generation
                and 0 <= now-lease.started <= self.deadline)

    def finish(self, lease, now, connection_key=None):
        eligible = self.valid(lease, now)
        if self.pending == lease: self.pending = None
        if not eligible or connection_key is None or connection_key in self.delivered:
            return False
        self.delivered.add(connection_key)
        self.last_delivery = now
        return True
