"""Local scheduling contract. No sockets, inference, storage, or UI side effects."""
from dataclasses import dataclass, field
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
    Changing text invalidates an old result; there is no queued backlog.
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
            self.latest = digest
            if self.pending: self.invalidate()
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
                and self.generation == lease.generation and self.latest == lease.cutoff
                and 0 <= now-lease.started <= self.deadline)

    def finish(self, lease, now, connection_key=None):
        eligible = self.valid(lease, now)
        if self.pending == lease: self.pending = None
        if not eligible or connection_key is None or connection_key in self.delivered:
            return False
        self.delivered.add(connection_key)
        self.last_delivery = now
        return True
