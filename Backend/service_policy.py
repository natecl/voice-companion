"""Trial policy: startup migration holds the service lock; budget redistribution serializes with admission."""
import os
from pathlib import Path
import sqlite3
from contextlib import closing
from admission import Admission

STT = (2_000_000, 20_000, 6)
ASK = (2_500_000, 3_000, 20)
# Retains historical accounting and explicit memory allocations.
RETIRED_JEV = (500_000, 500, 64)

ROLLOUT_POLICIES = {'stt':(1_500_000,20_000,6),'ask':(2_850_000,3_000,20),'jev':(650_000,500,64)}

PREFERENCE_POLICIES = {'stt':(1_200_000,20_000,6),'ask':(2_950_000,3_000,20),'jev':(850_000,500,64)}

# Founder-approved $0.04 physical QA envelope: move $0.02 of unused Ask
# capacity to one recording reservation. Total remains $5; no old charge moves.
DICTATION_POLICIES = {'stt':(1_220_000,20_000,6),'ask':(2_930_000,3_000,20),'jev':(850_000,500,64)}
DICTATION_APPROVAL = 'dictation-physical-20260927-040'


def redistribute_dictation_policy(db):
    """Caller owns a transaction. Explicit operator action, never startup funding."""
    policies=dict((r[0],tuple(r[1:])) for r in db.execute('SELECT category,cap,reservation,daily FROM policy'))
    if db.execute('SELECT cap FROM budget WHERE id=1').fetchone()!=(5_000_000,) or policies not in (PREFERENCE_POLICIES,DICTATION_POLICIES):
        raise ValueError('Unexpected ledger policy')
    if db.execute("SELECT 1 FROM request WHERE state='active'").fetchone():
        raise ValueError('Wait for active requests before redistribution')
    for category,(cap,_,_) in DICTATION_POLICIES.items():
        used=db.execute('SELECT coalesce(sum(reserved),0) FROM request WHERE category=?',(category,)).fetchone()[0]
        if used>cap:raise ValueError('Existing usage exceeds redistributed cap')
    db.execute('CREATE TABLE IF NOT EXISTS budget_redistribution(approval_id TEXT PRIMARY KEY, policy TEXT NOT NULL)')
    import json
    policy=json.dumps(DICTATION_POLICIES,sort_keys=True)
    prior=db.execute('SELECT policy FROM budget_redistribution WHERE approval_id=?',(DICTATION_APPROVAL,)).fetchone()
    if prior is not None and prior!=(policy,):raise ValueError('Approval mismatch')
    db.execute('INSERT OR IGNORE INTO budget_redistribution VALUES(?,?)',(DICTATION_APPROVAL,policy))
    for category,(cap,_,_) in DICTATION_POLICIES.items():
        db.execute('UPDATE policy SET cap=? WHERE category=?',(cap,category))


def redistribute_preference_policy(db):
    policies=dict((r[0],tuple(r[1:])) for r in db.execute('SELECT category,cap,reservation,daily FROM policy'))
    if db.execute('SELECT cap FROM budget WHERE id=1').fetchone()!=(5_000_000,) or policies not in (ROLLOUT_POLICIES,PREFERENCE_POLICIES):
        raise ValueError('Unexpected ledger policy')
    for category,(cap,_,_) in PREFERENCE_POLICIES.items():
        used=db.execute('SELECT coalesce(sum(reserved),0) FROM request WHERE category=?',(category,)).fetchone()[0]
        if used>cap:raise ValueError('Existing usage exceeds redistributed cap')
    for category,(cap,_,_) in PREFERENCE_POLICIES.items():
        db.execute('UPDATE policy SET cap=? WHERE category=?',(cap,category))


def redistribute_rollout_policy(db):
    """Caller owns the transaction: policy and reservation either both commit or neither does."""
    policies=dict((row[0],tuple(row[1:])) for row in db.execute('SELECT category,cap,reservation,daily FROM policy'))
    if db.execute('SELECT cap FROM budget WHERE id=1').fetchone()!=(5_000_000,) or policies not in (
            {'stt':STT,'ask':ASK,'jev':RETIRED_JEV},ROLLOUT_POLICIES):
        raise ValueError('Unexpected ledger policy; redistribution refused')
    for category,(cap,_,_) in ROLLOUT_POLICIES.items():
        used=db.execute('SELECT coalesce(sum(reserved),0) FROM request WHERE category=?',(category,)).fetchone()[0]
        if used>cap:raise ValueError('Existing usage exceeds redistributed cap')
    for category,(cap,_,_) in ROLLOUT_POLICIES.items():
        db.execute('UPDATE policy SET cap=? WHERE category=?',(cap,category))


def add_ask_policy(path):
    """Add only the approved Ask allocation; never reset usage or change existing caps."""
    if not path.exists():
        return
    db = sqlite3.connect(path, isolation_level=None)
    try:
        db.execute('BEGIN IMMEDIATE')
        cap = db.execute('SELECT cap FROM budget WHERE id=1').fetchone()
        policies = dict((row[0], tuple(row[1:])) for row in db.execute('SELECT category,cap,reservation,daily FROM policy'))
        if cap != (5_000_000,) or policies not in ({'stt': STT}, {'stt': STT, 'ask': ASK}, {'stt': STT, 'ask': ASK, 'jev': RETIRED_JEV}, ROLLOUT_POLICIES, PREFERENCE_POLICIES, DICTATION_POLICIES):
            raise ValueError('Unexpected ledger policy; migration refused')
        if 'ask' not in policies:
            db.execute('INSERT INTO policy VALUES(?,?,?,?)', ('ask', *ASK))
        db.execute('COMMIT')
    except BaseException:
        db.execute('ROLLBACK')
        raise
    finally:
        db.close()


def open_ledger(*, migrate=False):
    directory = Path(os.environ['VOICE_DATA_DIR'])
    if not directory.is_dir():
        raise ValueError('Persistent data directory is unavailable')
    path = directory / 'usage.sqlite'
    enabled = os.environ.get('VOICE_ENABLE_ASK') == '1'
    if enabled and migrate:
        add_ask_policy(path)
    limits = {'stt': STT, 'ask': ASK} if enabled else {'stt': STT}
    if path.exists():
        with closing(sqlite3.connect(path)) as db:
            if db.execute("SELECT 1 FROM policy WHERE category='jev'").fetchone():
                limits['jev'] = RETIRED_JEV
            policies=dict((row[0],tuple(row[1:])) for row in db.execute('SELECT category,cap,reservation,daily FROM policy'))
            if enabled and policies in (ROLLOUT_POLICIES,PREFERENCE_POLICIES,DICTATION_POLICIES):limits=dict(policies)
    return Admission(path, total_microusd=5_000_000, limits=limits)
