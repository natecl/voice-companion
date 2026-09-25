"""Approved profile QA sub-ledger, separate from the exhausted earlier memory allocation."""
from pathlib import Path
import json
import time
from admission import Rejected
from memory_budget import database

APPROVAL_ID = 'personal-profile-qa-2026-09-25-100'
ALLOCATION = 1_000_000
PER_CALL = 10_000
MODELS = ('gpt-6-luna', 'jev-1.13.0')


def provision(global_path, memory_path):
    """Explicit operator action; reserve once globally before exposing the sub-allocation."""
    with database(global_path, isolation_level=None, timeout=2) as db:
        db.execute('BEGIN IMMEDIATE')
        try:
            existing = db.execute('SELECT category,reserved FROM request WHERE id=?', (APPROVAL_ID,)).fetchone()
            if existing:
                if existing != ('ask', ALLOCATION): raise ValueError('Profile approval conflicts')
            else:
                cap = db.execute('SELECT cap FROM budget WHERE id=1').fetchone()[0]
                used = db.execute('SELECT coalesce(sum(reserved),0) FROM request').fetchone()[0]
                category_cap = db.execute("SELECT cap FROM policy WHERE category='ask'").fetchone()[0]
                category_used = db.execute("SELECT coalesce(sum(reserved),0) FROM request WHERE category='ask'").fetchone()[0]
                if used + ALLOCATION > cap or category_used + ALLOCATION > category_cap:
                    raise Rejected('budget_limit')
                credential = db.execute('SELECT id FROM credential ORDER BY rowid DESC LIMIT 1').fetchone()
                if credential is None: raise Rejected('no_internal_credential')
                db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)',
                           (APPROVAL_ID,credential[0],'ask',time.time(),ALLOCATION,'completed'))
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK'); raise
    with database(memory_path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS profile_allocation(id TEXT PRIMARY KEY, cap INTEGER NOT NULL)')
        db.execute('INSERT OR IGNORE INTO profile_allocation VALUES(?,?)',(APPROVAL_ID,ALLOCATION))
        if db.execute('SELECT id,cap FROM profile_allocation').fetchall() != [(APPROVAL_ID,ALLOCATION)]:
            raise ValueError('Profile allocation conflicts')
        db.execute('CREATE TABLE IF NOT EXISTS profile_attempt(id TEXT PRIMARY KEY, model TEXT NOT NULL, reserved INTEGER NOT NULL, state TEXT NOT NULL, usage TEXT)')
    return {'approval_id':APPROVAL_ID,'cap_microusd':ALLOCATION}


class ProfileBudget:
    def __init__(self, path):
        self.path = Path(path)
        if not self.path.exists(): raise ValueError('Provision the canonical profile allocation first')
        with database(self.path) as db:
            if db.execute('SELECT id,cap FROM profile_allocation').fetchall() != [(APPROVAL_ID,ALLOCATION)]:
                raise ValueError('Profile allocation required')

    def reserve(self, key, model):
        if model not in MODELS: raise Rejected('unapproved_profile_model')
        with database(self.path, isolation_level=None, timeout=2) as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                if db.execute('SELECT 1 FROM profile_attempt WHERE id=?',(key,)).fetchone():
                    raise Rejected('paid_retry_requires_review')
                used = db.execute('SELECT coalesce(sum(reserved),0) FROM profile_attempt').fetchone()[0]
                if used + PER_CALL > ALLOCATION: raise Rejected('profile_budget_limit')
                db.execute('INSERT INTO profile_attempt VALUES(?,?,?,?,NULL)',(key,model,PER_CALL,'reserved'))
                db.execute('COMMIT')
            except BaseException:
                db.execute('ROLLBACK'); raise

    def finish(self, key, usage=None):
        with database(self.path) as db:
            db.execute("UPDATE profile_attempt SET state=?,usage=? WHERE id=? AND state='reserved'",
                       ('completed' if usage is not None else 'failed',json.dumps(usage),key))

    def report(self):
        with database(self.path) as db:
            return [dict(zip(('model','calls','reserved_microusd'),row)) for row in db.execute('SELECT model,count(*),sum(reserved) FROM profile_attempt GROUP BY model')]
