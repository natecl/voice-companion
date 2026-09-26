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
MULTISOURCE_APPROVAL_ID = 'memory-multisource-additional-2026-09-26-020'
MULTISOURCE_ALLOWANCE = 200_000
ROLLOUT_APPROVAL_ID = 'companion-rollout-qa-2026-09-26-050'
ROLLOUT_ALLOWANCE = 500_000
PREFERENCE_APPROVAL_ID = "preference-verification-qa-2026-09-26-030"
PREFERENCE_ALLOWANCE = 300_000


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
    def __init__(self, path, *, include_rework_allowance=False, include_consolidation_allowance=False, include_multisource_allowance=False, include_rollout_allowance=False, include_preference_allowance=False):
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
            if include_multisource_allowance:
                if not include_consolidation_allowance:
                    raise ValueError('Consolidation allowance required first')
                if db.execute('SELECT id,cap FROM profile_multisource_allowance').fetchall()!=[(MULTISOURCE_APPROVAL_ID,MULTISOURCE_ALLOWANCE)]:
                    raise ValueError('Explicit multisource allowance required')
                self.cap += MULTISOURCE_ALLOWANCE
            if include_rollout_allowance:
                if not include_multisource_allowance:
                    raise ValueError('Multisource allowance required first')
                if db.execute('SELECT id,cap FROM profile_rollout_allowance').fetchall()!=[(ROLLOUT_APPROVAL_ID,ROLLOUT_ALLOWANCE)]:
                    raise ValueError('Explicit rollout allowance required')
                self.cap += ROLLOUT_ALLOWANCE
            if include_preference_allowance:
                if not include_rollout_allowance:raise ValueError('Rollout allowance required first')
                if db.execute('SELECT id,cap FROM profile_preference_allowance').fetchall()!=[(PREFERENCE_APPROVAL_ID,PREFERENCE_ALLOWANCE)]:
                    raise ValueError('Explicit preference allowance required')
                self.cap += PREFERENCE_ALLOWANCE

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


def _provision_additional(global_path,memory_path,approval,amount,table,total,allocations=None,redistribute=False):
    if table not in ('profile_rework_allowance','profile_consolidation_allowance','profile_multisource_allowance','profile_rollout_allowance','profile_preference_allowance'):
        raise ValueError('Unknown allowance')
    allocations={'ask':amount} if allocations is None else allocations
    if (not allocations or set(allocations)-{'ask','jev'} or sum(allocations.values())!=amount
            or any(type(value) is not int or value<=0 for value in allocations.values())):
        raise ValueError('Invalid approved allocation split')
    with database(global_path,isolation_level=None,timeout=2) as db:
        db.execute('BEGIN IMMEDIATE')
        try:
            if redistribute=='preference':
                from service_policy import redistribute_preference_policy
                redistribute_preference_policy(db)
            elif redistribute:
                from service_policy import redistribute_rollout_policy
                redistribute_rollout_policy(db)
            missing=[]
            for category,value in allocations.items():
                key=approval if len(allocations)==1 else approval+':'+category
                existing=db.execute('SELECT category,reserved FROM request WHERE id=?',(key,)).fetchone()
                if existing:
                    if existing!=(category,value):raise ValueError('Allowance conflicts')
                else:
                    policy=db.execute('SELECT cap FROM policy WHERE category=?',(category,)).fetchone()
                    used=db.execute('SELECT coalesce(sum(reserved),0) FROM request WHERE category=?',(category,)).fetchone()[0]
                    if policy is None or used+value>policy[0]:raise Rejected('budget_limit')
                    missing.append((key,category,value))
            cap=db.execute('SELECT cap FROM budget WHERE id=1').fetchone()[0]
            used=db.execute('SELECT coalesce(sum(reserved),0) FROM request').fetchone()[0]
            if used+sum(item[2] for item in missing)>cap:raise Rejected('budget_limit')
            credential=db.execute('SELECT id FROM credential ORDER BY rowid DESC LIMIT 1').fetchone()
            if credential is None:raise Rejected('no_internal_credential')
            for key,category,value in missing:
                db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)',
                           (key,credential[0],category,time.time(),value,'completed'))
            db.execute('COMMIT')
        except BaseException:
            db.execute('ROLLBACK');raise
    # Global reservation precedes local exposure; retries never grant extra spend.
    with database(memory_path) as db:
        db.execute(f'CREATE TABLE IF NOT EXISTS {table}(id TEXT PRIMARY KEY,cap INTEGER NOT NULL)')
        db.execute(f'INSERT OR IGNORE INTO {table} VALUES(?,?)',(approval,amount))
        if db.execute(f'SELECT id,cap FROM {table}').fetchall()!=[(approval,amount)]:
            raise ValueError('Allowance conflicts')
    return dict(approval_id=approval,total_cap_microusd=total)


def provision_rework_allowance(global_path,memory_path):
    ProfileBudget(memory_path)
    return _provision_additional(global_path,memory_path,REWORK_APPROVAL_ID,REWORK_ALLOWANCE,
                                 'profile_rework_allowance',ALLOCATION+REWORK_ALLOWANCE)


def provision_consolidation_allowance(global_path,memory_path):
    ProfileBudget(memory_path,include_rework_allowance=True)
    return _provision_additional(global_path,memory_path,CONSOLIDATION_APPROVAL_ID,CONSOLIDATION_ALLOWANCE,
                                 'profile_consolidation_allowance',ALLOCATION+REWORK_ALLOWANCE+CONSOLIDATION_ALLOWANCE)


def provision_multisource_allowance(global_path,memory_path):
    """Founder-approved additional $0.20 on September 26; never called at startup."""
    ProfileBudget(memory_path,include_rework_allowance=True,include_consolidation_allowance=True)
    return _provision_additional(global_path,memory_path,MULTISOURCE_APPROVAL_ID,MULTISOURCE_ALLOWANCE,
        'profile_multisource_allowance',ALLOCATION+REWORK_ALLOWANCE+CONSOLIDATION_ALLOWANCE+MULTISOURCE_ALLOWANCE,
        allocations={'ask':100_000,'jev':100_000})


def provision_rollout_allowance(global_path,memory_path):
    """Approved $0.50 redistribution within $5; operator-only, never startup."""
    ProfileBudget(memory_path,include_rework_allowance=True,include_consolidation_allowance=True,
                  include_multisource_allowance=True)
    return _provision_additional(global_path,memory_path,ROLLOUT_APPROVAL_ID,ROLLOUT_ALLOWANCE,
        'profile_rollout_allowance',2_900_000,allocations={'ask':350_000,'jev':150_000},redistribute=True)


def provision_preference_allowance(global_path,memory_path):
    """Founder approved $0.30; operator-only, not exposed to hosted callers."""
    ProfileBudget(memory_path,include_rework_allowance=True,include_consolidation_allowance=True,
                  include_multisource_allowance=True,include_rollout_allowance=True)
    return _provision_additional(global_path,memory_path,PREFERENCE_APPROVAL_ID,PREFERENCE_ALLOWANCE,
        'profile_preference_allowance',3_200_000,allocations={'ask':100_000,'jev':200_000},redistribute='preference')
