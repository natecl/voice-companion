"""Durable admission for the internal trial. No provider calls or payload storage.

Reservations remain charged, even on failure. The service must hold an exclusive
process lock before recovering interrupted requests or accepting connections.
"""
from contextlib import contextmanager
import hashlib
import secrets
import sqlite3
import time
import uuid


class Rejected(Exception):
    """A safe, content-free reason for denying a request."""


class Admission:
    def __init__(self, path, *, total_microusd, limits, clock=time.time):
        # limits: category -> (lifetime budget, reservation per call, daily calls).
        if type(total_microusd) is not int or total_microusd <= 0 or not limits:
            raise ValueError('Positive integer budgets required')
        for category, values in limits.items():
            if not category or len(values) != 3 or any(type(v) is not int or v <= 0 for v in values):
                raise ValueError('Invalid category policy')
            if values[1] > values[0]:
                raise ValueError('Reservation exceeds category budget')
        self.clock = clock
        self.db = sqlite3.connect(path, timeout=2, isolation_level=None)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA synchronous=FULL')
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS budget (id INTEGER PRIMARY KEY CHECK(id=1), cap INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS policy (
                category TEXT PRIMARY KEY, cap INTEGER NOT NULL,
                reservation INTEGER NOT NULL, daily INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS credential (
                id TEXT PRIMARY KEY, digest TEXT UNIQUE NOT NULL,
                expires REAL NOT NULL, revoked INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS request (
                id TEXT PRIMARY KEY, credential_id TEXT NOT NULL REFERENCES credential(id),
                category TEXT NOT NULL REFERENCES policy(category), started REAL NOT NULL,
                reserved INTEGER NOT NULL, state TEXT NOT NULL
                    CHECK(state IN ('active','completed','failed','interrupted')));
            CREATE UNIQUE INDEX IF NOT EXISTS one_active_category
                ON request(category) WHERE state='active';
            CREATE TABLE IF NOT EXISTS recording_qa_day (
                day_start INTEGER PRIMARY KEY, approved_at REAL NOT NULL);
        ''')
        try:
            with self.transaction():
                if 'attempts' not in {row[1] for row in self.db.execute('PRAGMA table_info(recording_qa_day)')}:
                    self.db.execute('ALTER TABLE recording_qa_day ADD COLUMN attempts INTEGER NOT NULL DEFAULT 1 CHECK(attempts BETWEEN 1 AND 2)')
                saved = self.db.execute('SELECT cap FROM budget WHERE id=1').fetchone()
                if saved is None:
                    self.db.execute('INSERT INTO budget VALUES(1, ?)', (total_microusd,))
                    self.db.executemany('INSERT INTO policy VALUES(?,?,?,?)',
                                        [(k, *v) for k, v in sorted(limits.items())])
                elif saved[0] != total_microusd or self.db.execute(
                        'SELECT category,cap,reservation,daily FROM policy ORDER BY category').fetchall() != [
                            (k, *v) for k, v in sorted(limits.items())]:
                    raise ValueError('Budget policy changed; explicit migration required')
        except Exception:
            self.db.close()
            raise

    @contextmanager
    def transaction(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def close(self):
        self.db.close()

    @staticmethod
    def digest(token):
        if not isinstance(token, str) or not 32 <= len(token) <= 256:
            raise Rejected('unauthorized')
        return hashlib.sha256(token.encode('utf-8')).hexdigest()

    def enroll(self, *, lifetime_seconds=86400):
        if type(lifetime_seconds) is not int or not 0 < lifetime_seconds <= 30 * 86400:
            raise ValueError('Credential lifetime must be at most 30 days')
        token, identifier = secrets.token_urlsafe(32), str(uuid.uuid4())
        self.db.execute('INSERT INTO credential(id,digest,expires) VALUES(?,?,?)',
                        (identifier, self.digest(token), self.clock() + lifetime_seconds))
        return identifier, token

    def authorized(self, token):
        row = self.db.execute('SELECT id FROM credential WHERE digest=? AND revoked=0 AND expires>?',
                              (self.digest(token), self.clock())).fetchone()
        if row is None:
            raise Rejected('unauthorized')
        return row[0]

    def revoke(self, identifier):
        self.db.execute('UPDATE credential SET revoked=1 WHERE id=?', (identifier,))

    def allow_one_recording_today(self, day_start, *, replace_consumed=False):
        """Date-scoped extra attempt; replacing a consumed grant requires separate approval."""
        now = self.clock()
        if day_start != int(now // 86400) * 86400:
            raise ValueError('Allowance must name the current UTC day')
        with self.transaction():
            row = self.db.execute('SELECT attempts FROM recording_qa_day WHERE day_start=?', (day_start,)).fetchone()
            if replace_consumed:
                base = self.db.execute("SELECT daily FROM policy WHERE category='stt'").fetchone()
                used = self.db.execute("SELECT count(*) FROM request WHERE category='stt' AND started>=?", (day_start,)).fetchone()[0]
                active = self.db.execute("SELECT 1 FROM request WHERE category='stt' AND state='active'").fetchone()
                if row != (1,) or base is None or used != base[0] + 1 or active:
                    raise ValueError('Replacement requires exactly one consumed allowance and no active recording')
                self.db.execute('UPDATE recording_qa_day SET attempts=2 WHERE day_start=?', (day_start,))
            else:
                if row:
                    raise ValueError('This day already has its one recording allowance')
                self.db.execute('INSERT INTO recording_qa_day(day_start,approved_at) VALUES(?,?)', (day_start, now))

    def reserve(self, token, category):
        with self.transaction():
            owner = self.authorized(token)
            policy = self.db.execute('SELECT cap,reservation,daily FROM policy WHERE category=?',
                                     (category,)).fetchone()
            if policy is None:
                raise Rejected('unsupported_category')
            cap, amount, daily = policy
            if self.db.execute("SELECT 1 FROM request WHERE category=? AND state='active'", (category,)).fetchone():
                raise Rejected('busy')
            now = self.clock()
            day_start = int(now // 86400) * 86400
            if category == 'stt':
                allowance = self.db.execute('SELECT attempts FROM recording_qa_day WHERE day_start=?', (day_start,)).fetchone()
                if allowance:
                    daily += allowance[0]
            if self.db.execute('SELECT count(*) FROM request WHERE category=? AND started>=?',
                               (category, day_start)).fetchone()[0] >= daily:
                raise Rejected('daily_limit')
            category_used = self.db.execute('SELECT coalesce(sum(reserved),0) FROM request WHERE category=?',
                                           (category,)).fetchone()[0]
            total_used = self.db.execute('SELECT coalesce(sum(reserved),0) FROM request').fetchone()[0]
            total_cap = self.db.execute('SELECT cap FROM budget WHERE id=1').fetchone()[0]
            if category_used + amount > cap or total_used + amount > total_cap:
                raise Rejected('budget_limit')
            identifier = str(uuid.uuid4())
            self.db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)',
                            (identifier, owner, category, now, amount, 'active'))
            return identifier

    def finish(self, identifier, *, completed):
        # Idempotent; never refunds a reservation or changes a finished outcome.
        self.db.execute("UPDATE request SET state=? WHERE id=? AND state='active'",
                        ('completed' if completed else 'failed', identifier))

    def recover_interrupted(self):
        # Caller MUST own the exclusive service lock. No lease timeout can allow
        # a second provider call while an old process is still alive.
        self.db.execute("UPDATE request SET state='interrupted' WHERE state='active'")

    def usage(self):
        return self.db.execute('SELECT category,count(*),coalesce(sum(reserved),0) FROM request GROUP BY category').fetchall()
