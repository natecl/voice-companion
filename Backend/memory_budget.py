"""A local sub-ledger spends only an allocation already reserved in the global ledger."""
from contextlib import contextmanager, closing
import json
from pathlib import Path
import sqlite3
import time
from admission import Rejected

APPROVAL_ID = 'memory-qa-2026-09-25-025'
ALLOCATION = 250_000  # micro-USD, within the existing $5 global ceiling
JEV_GRANT_ID = 'memory-jev-fix-2026-09-25-003'
JEV_GRANT = 30_000
JEV_MODEL = 'jev-1.13.0'
PER_CALL = 5_000    # conservative ceiling for the bounded provider payloads


@contextmanager
def database(path, **kwargs):
    with closing(sqlite3.connect(path, **kwargs)) as db:
        with db:
            yield db


def reserve_global_allocation(path):
    """Administrative operation, explicitly approved Sep 25. Old service reads this same row."""
    with database(path, isolation_level=None, timeout=2) as db:
        db.execute('BEGIN IMMEDIATE')
        try:
            existing = db.execute('SELECT category,reserved FROM request WHERE id=?', (APPROVAL_ID,)).fetchone()
            if existing:
                if existing != ('jev', ALLOCATION): raise ValueError('Allocation ID conflicts')
            else:
                total_cap = db.execute('SELECT cap FROM budget WHERE id=1').fetchone()[0]
                used = db.execute('SELECT coalesce(sum(reserved),0) FROM request').fetchone()[0]
                category_cap = db.execute("SELECT cap FROM policy WHERE category='jev'").fetchone()[0]
                category_used = db.execute("SELECT coalesce(sum(reserved),0) FROM request WHERE category='jev'").fetchone()[0]
                if total_cap != 5_000_000 or used + ALLOCATION > total_cap or category_used + ALLOCATION > category_cap:
                    raise Rejected('budget_limit')
                credential = db.execute('SELECT id FROM credential ORDER BY rowid DESC LIMIT 1').fetchone()
                if credential is None: raise Rejected('no_internal_credential')
                db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)', (APPROVAL_ID, credential[0], 'jev', time.time(), ALLOCATION, 'completed'))
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK')
            raise
        return {'approval_id': APPROVAL_ID, 'reserved_microusd': ALLOCATION,
                'global_reserved_microusd': db.execute('SELECT sum(reserved) FROM request').fetchone()[0]}


def add_jev_qa_grant(global_path, memory_path):
    """Explicit operator operation: founder approved six Jev calls, Sep 25. Never startup code."""
    with database(global_path, isolation_level=None, timeout=2) as db:
        db.execute('BEGIN IMMEDIATE')
        try:
            existing = db.execute('SELECT category,reserved FROM request WHERE id=?',(JEV_GRANT_ID,)).fetchone()
            if existing:
                if existing != ('jev',JEV_GRANT): raise ValueError('Grant ID conflicts')
            else:
                cap=db.execute('SELECT cap FROM budget WHERE id=1').fetchone()[0]
                used=db.execute('SELECT coalesce(sum(reserved),0) FROM request').fetchone()[0]
                category_cap=db.execute("SELECT cap FROM policy WHERE category='jev'").fetchone()[0]
                category_used=db.execute("SELECT coalesce(sum(reserved),0) FROM request WHERE category='jev'").fetchone()[0]
                if cap != 5_000_000 or used+JEV_GRANT > cap or category_used+JEV_GRANT > category_cap:
                    raise Rejected('budget_limit')
                credential=db.execute('SELECT id FROM credential ORDER BY rowid DESC LIMIT 1').fetchone()
                if credential is None: raise Rejected('no_internal_credential')
                db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)',
                           (JEV_GRANT_ID,credential[0],'jev',time.time(),JEV_GRANT,'completed'))
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK');raise
    # Reserve globally before exposing local spend. Both steps are idempotent after interruption.
    with database(memory_path) as db:
        if db.execute('SELECT id,cap FROM allocation').fetchall() != [(APPROVAL_ID,ALLOCATION)]:
            raise ValueError('Existing canonical memory ledger required')
        db.execute('CREATE TABLE IF NOT EXISTS grant(id TEXT PRIMARY KEY, cap INTEGER NOT NULL, model TEXT NOT NULL)')
        db.execute('INSERT OR IGNORE INTO grant VALUES(?,?,?)',(JEV_GRANT_ID,JEV_GRANT,JEV_MODEL))
        if db.execute('SELECT cap,model FROM grant WHERE id=?',(JEV_GRANT_ID,)).fetchone() != (JEV_GRANT,JEV_MODEL):
            raise ValueError('Grant ID conflicts')
    return {'approval_id':JEV_GRANT_ID,'reserved_microusd':JEV_GRANT,'model':JEV_MODEL}


class MemoryBudget:
    def __init__(self, path, receipt):
        if receipt.get('approval_id') != APPROVAL_ID or receipt.get('reserved_microusd') != ALLOCATION:
            raise ValueError('Global allocation receipt required')
        self.path = Path(path)
        with database(self.path) as db:
            db.execute('CREATE TABLE IF NOT EXISTS allocation(id TEXT PRIMARY KEY, cap INTEGER NOT NULL)')
            db.execute('INSERT OR IGNORE INTO allocation VALUES(?,?)', (APPROVAL_ID, ALLOCATION))
            if db.execute('SELECT id,cap FROM allocation').fetchall() != [(APPROVAL_ID, ALLOCATION)]:
                raise ValueError('Unexpected memory budget; do not reset')
            db.execute('CREATE TABLE IF NOT EXISTS grant(id TEXT PRIMARY KEY, cap INTEGER NOT NULL, model TEXT NOT NULL)')
            db.execute('CREATE TABLE IF NOT EXISTS attempt(id TEXT PRIMARY KEY, model TEXT NOT NULL, reserved INTEGER NOT NULL, state TEXT NOT NULL, usage TEXT)')
        self.path.chmod(0o600)

    def reserve(self, key, model):
        with database(self.path, isolation_level=None) as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                if db.execute('SELECT 1 FROM attempt WHERE id=?', (key,)).fetchone():
                    raise Rejected('paid_retry_requires_review')
                used = db.execute('SELECT coalesce(sum(reserved),0) FROM attempt').fetchone()[0]
                extra = db.execute('SELECT coalesce(sum(cap),0) FROM grant WHERE model=?',(model,)).fetchone()[0]
                if used + PER_CALL > ALLOCATION + extra: raise Rejected('memory_budget_limit')
                db.execute('INSERT INTO attempt VALUES(?,?,?,?,NULL)', (key, model, PER_CALL, 'reserved'))
                db.execute('COMMIT')
            except BaseException:
                db.execute('ROLLBACK')
                raise

    def finish(self, key, usage=None):
        with database(self.path) as db:
            db.execute("UPDATE attempt SET state=?,usage=? WHERE id=? AND state='reserved'", ('completed' if usage is not None else 'failed', json.dumps(usage), key))

    def report(self):
        with database(self.path) as db:
            return [dict(zip(('model','attempts','reserved_microusd'), r)) for r in db.execute('SELECT model,count(*),sum(reserved) FROM attempt GROUP BY model')]
