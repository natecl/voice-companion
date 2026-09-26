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
REWORK_APPROVAL_ID = 'memory-rework-additional-2026-09-25-100'
REWORK_ALLOWANCE = 1_000_000
CONSOLIDATION_APPROVAL_ID = 'memory-consolidation-additional-2026-09-26-020'
CONSOLIDATION_ALLOWANCE = 200_000


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
    def __init__(self, path, *, include_rework_allowance=False, include_consolidation_allowance=False):
        self.path = Path(path)
        self.cap = ALLOCATION
        if not self.path.exists(): raise ValueError('Provision the canonical profile allocation first')
        with database(self.path) as db:
            if db.execute('SELECT id,cap FROM profile_allocation').fetchall() != [(APPROVAL_ID,ALLOCATION)]:
                raise ValueError('Profile allocation required')
            if include_rework_allowance:
                if db.execute('SELECT id,cap FROM profile_rework_allowance').fetchall() != [(REWORK_APPROVAL_ID,REWORK_ALLOWANCE)]:
                    raise ValueError('Explicit rework allowance required')
                self.cap += REWORK_ALLOWANCE
            if include_consolidation_allowance:
                if not include_rework_allowance:
                    raise ValueError('Rework allowance required first')
                if db.execute('SELECT id,cap FROM profile_consolidation_allowance').fetchall() != [(CONSOLIDATION_APPROVAL_ID,CONSOLIDATION_ALLOWANCE)]:
                    raise ValueError('Explicit consolidation allowance required')
                self.cap += CONSOLIDATION_ALLOWANCE

    def reserve(self, key, model):
        if model not in MODELS: raise Rejected('unapproved_profile_model')
        with database(self.path, isolation_level=None, timeout=2) as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                if db.execute('SELECT 1 FROM profile_attempt WHERE id=?',(key,)).fetchone():
                    raise Rejected('paid_retry_requires_review')
                used = db.execute('SELECT coalesce(sum(reserved),0) FROM profile_attempt').fetchone()[0]
                if used + PER_CALL > self.cap: raise Rejected('profile_budget_limit')
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


def provision_rework_allowance(global_path, memory_path):
    """Explicit founder-approved additional $1; idempotent and never called at startup."""
    ProfileBudget(memory_path) # Require the existing canonical ledger.
    with database(global_path, isolation_level=None, timeout=2) as db:
        db.execute('BEGIN IMMEDIATE')
        try:
            existing=db.execute('SELECT category,reserved FROM request WHERE id=?',(REWORK_APPROVAL_ID,)).fetchone()
            if existing:
                if existing!=('ask',REWORK_ALLOWANCE):raise ValueError('Rework approval conflicts')
            else:
                cap=db.execute('SELECT cap FROM budget WHERE id=1').fetchone()[0]
                used=db.execute('SELECT coalesce(sum(reserved),0) FROM request').fetchone()[0]
                category_cap=db.execute("SELECT cap FROM policy WHERE category='ask'").fetchone()[0]
                category_used=db.execute("SELECT coalesce(sum(reserved),0) FROM request WHERE category='ask'").fetchone()[0]
                if used+REWORK_ALLOWANCE>cap or category_used+REWORK_ALLOWANCE>category_cap:raise Rejected('budget_limit')
                credential=db.execute('SELECT id FROM credential ORDER BY rowid DESC LIMIT 1').fetchone()
                if credential is None:raise Rejected('no_internal_credential')
                db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)',
                    (REWORK_APPROVAL_ID,credential[0],'ask',time.time(),REWORK_ALLOWANCE,'completed'))
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK');raise
    # Global reservation precedes local exposure; interruption cannot duplicate either.
    with database(memory_path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS profile_rework_allowance(id TEXT PRIMARY KEY,cap INTEGER NOT NULL)')
        db.execute('INSERT OR IGNORE INTO profile_rework_allowance VALUES(?,?)',(REWORK_APPROVAL_ID,REWORK_ALLOWANCE))
        if db.execute('SELECT id,cap FROM profile_rework_allowance').fetchall()!=[(REWORK_APPROVAL_ID,REWORK_ALLOWANCE)]:
            raise ValueError('Rework approval conflicts')
    return dict(approval_id=REWORK_APPROVAL_ID,total_cap_microusd=ALLOCATION+REWORK_ALLOWANCE)


def provision_consolidation_allowance(global_path, memory_path):
    """Explicit founder-approved additional $0.20; idempotent and never called at startup."""
    ProfileBudget(memory_path,include_rework_allowance=True) # Require the existing canonical ledger.
    with database(global_path, isolation_level=None, timeout=2) as db:
        db.execute('BEGIN IMMEDIATE')
        try:
            existing=db.execute('SELECT category,reserved FROM request WHERE id=?',(CONSOLIDATION_APPROVAL_ID,)).fetchone()
            if existing:
                if existing!=('ask',CONSOLIDATION_ALLOWANCE):raise ValueError('Rework approval conflicts')
            else:
                cap=db.execute('SELECT cap FROM budget WHERE id=1').fetchone()[0]
                used=db.execute('SELECT coalesce(sum(reserved),0) FROM request').fetchone()[0]
                category_cap=db.execute("SELECT cap FROM policy WHERE category='ask'").fetchone()[0]
                category_used=db.execute("SELECT coalesce(sum(reserved),0) FROM request WHERE category='ask'").fetchone()[0]
                if used+CONSOLIDATION_ALLOWANCE>cap or category_used+CONSOLIDATION_ALLOWANCE>category_cap:raise Rejected('budget_limit')
                credential=db.execute('SELECT id FROM credential ORDER BY rowid DESC LIMIT 1').fetchone()
                if credential is None:raise Rejected('no_internal_credential')
                db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)',
                    (CONSOLIDATION_APPROVAL_ID,credential[0],'ask',time.time(),CONSOLIDATION_ALLOWANCE,'completed'))
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK');raise
    # Global reservation precedes local exposure; interruption cannot duplicate either.
    with database(memory_path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS profile_consolidation_allowance(id TEXT PRIMARY KEY,cap INTEGER NOT NULL)')
        db.execute('INSERT OR IGNORE INTO profile_consolidation_allowance VALUES(?,?)',(CONSOLIDATION_APPROVAL_ID,CONSOLIDATION_ALLOWANCE))
        if db.execute('SELECT id,cap FROM profile_consolidation_allowance').fetchall()!=[(CONSOLIDATION_APPROVAL_ID,CONSOLIDATION_ALLOWANCE)]:
            raise ValueError('Rework approval conflicts')
    return dict(approval_id=CONSOLIDATION_APPROVAL_ID,total_cap_microusd=ALLOCATION+REWORK_ALLOWANCE+CONSOLIDATION_ALLOWANCE)
