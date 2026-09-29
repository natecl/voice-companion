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


PRIVATE_DICTATION_APPROVAL = 'private-dictation-20260927-050'
PRIVATE_DICTATION_POLICIES = {'stt':(1_240_000,20_000,6),'ask':(2_960_000,3_000,20),'jev':(850_000,500,64)}

def private_dictation_funded(db, cap, policies):
    if cap != (5_050_000,) or policies != PRIVATE_DICTATION_POLICIES:return False
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='qa_budget_extension'").fetchone():return False
    return db.execute('SELECT amount FROM qa_budget_extension WHERE id=?',(PRIVATE_DICTATION_APPROVAL,)).fetchone()==(50_000,)

def extend_private_dictation_policy(db):
    """Explicit operator transaction; never called by startup. Preserves old charges."""
    cap=db.execute('SELECT cap FROM budget WHERE id=1').fetchone()
    policies=dict((r[0],tuple(r[1:])) for r in db.execute('SELECT * FROM policy'))
    if private_dictation_funded(db,cap,policies):return
    if cap!=(5_000_000,) or policies!=DICTATION_POLICIES:raise ValueError('Unexpected QA baseline')
    if db.execute("SELECT 1 FROM request WHERE state='active'").fetchone():raise ValueError('Active request')
    db.execute('CREATE TABLE IF NOT EXISTS qa_budget_extension(id TEXT PRIMARY KEY,amount INTEGER NOT NULL)')
    db.execute('INSERT INTO qa_budget_extension VALUES(?,?)',(PRIVATE_DICTATION_APPROVAL,50_000))
    db.execute('UPDATE budget SET cap=5050000 WHERE id=1')
    for category,(limit,_,_) in PRIVATE_DICTATION_POLICIES.items():
        db.execute('UPDATE policy SET cap=? WHERE category=?',(limit,category))


PROACTIVE_PHONE_APPROVAL = 'proactive-phone-20260928-090'
PROACTIVE_PHONE_POLICIES = {'stt':(1_280_000,20_000,6),'ask':(3_010_000,3_000,20),'jev':(850_000,500,64)}

def proactive_phone_funded(db,cap,policies):
    if cap!=(5_140_000,) or policies!=PROACTIVE_PHONE_POLICIES:return False
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='qa_budget_extension'").fetchone():return False
    return db.execute('SELECT amount FROM qa_budget_extension WHERE id=?',(PROACTIVE_PHONE_APPROVAL,)).fetchone()==(90_000,)

def extend_proactive_phone_policy(db):
    """Explicit approved operator transaction; idempotent, never startup funding."""
    cap=db.execute('SELECT cap FROM budget WHERE id=1').fetchone()
    policies=dict((r[0],tuple(r[1:])) for r in db.execute('SELECT * FROM policy'))
    if proactive_phone_funded(db,cap,policies):return
    if not private_dictation_funded(db,cap,policies):raise ValueError('Unexpected QA baseline')
    if db.execute("SELECT 1 FROM request WHERE state='active'").fetchone():raise ValueError('Active request')
    db.execute('INSERT INTO qa_budget_extension VALUES(?,?)',(PROACTIVE_PHONE_APPROVAL,90_000))
    db.execute('UPDATE budget SET cap=5140000 WHERE id=1')
    for category,(limit,_,_) in PROACTIVE_PHONE_POLICIES.items():
        db.execute('UPDATE policy SET cap=? WHERE category=?',(limit,category))


CEDAR_PHONE_APPROVAL = 'cedar-phone-20260928-170'
CEDAR_PHONE_POLICIES = {'stt':(1_300_000,20_000,6),'ask':(3_035_000,3_000,20),'jev':(850_000,500,64)}

def cedar_phone_funded(db,cap,policies):
    if cap!=(5_185_000,) or policies!=CEDAR_PHONE_POLICIES:return False
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='qa_budget_extension'").fetchone():return False
    return db.execute('SELECT amount FROM qa_budget_extension WHERE id=?',(CEDAR_PHONE_APPROVAL,)).fetchone()==(45_000,)

def extend_cedar_phone_policy(db):
    """One recording plus one note; six proactive calls have a separate $0.12 ledger."""
    cap=db.execute('SELECT cap FROM budget WHERE id=1').fetchone()
    policies=dict((r[0],tuple(r[1:])) for r in db.execute('SELECT * FROM policy'))
    if cedar_phone_funded(db,cap,policies):return
    if not proactive_phone_funded(db,cap,policies):raise ValueError('Unexpected QA baseline')
    if db.execute("SELECT 1 FROM request WHERE state='active'").fetchone():raise ValueError('Active request')
    db.execute('INSERT INTO qa_budget_extension VALUES(?,?)',(CEDAR_PHONE_APPROVAL,45_000))
    db.execute('UPDATE budget SET cap=5185000 WHERE id=1')
    for category,(limit,_,_) in CEDAR_PHONE_POLICIES.items():
        db.execute('UPDATE policy SET cap=? WHERE category=?',(limit,category))


TWO_TOPIC_PHONE_APPROVAL = 'two-topic-phone-20260928-210'
TWO_TOPIC_PHONE_POLICIES = {'stt':(1_320_000,20_000,6),'ask':(3_060_000,3_000,20),'jev':(850_000,500,64)}

def two_topic_phone_funded(db,cap,policies):
    if cap!=(5_230_000,) or policies!=TWO_TOPIC_PHONE_POLICIES:return False
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='qa_budget_extension'").fetchone():return False
    return db.execute('SELECT amount FROM qa_budget_extension WHERE id=?',(TWO_TOPIC_PHONE_APPROVAL,)).fetchone()==(45_000,)

def extend_two_topic_phone_policy(db):
    """One recording plus one note; eight proactive calls have a separate $0.16 ledger."""
    cap=db.execute('SELECT cap FROM budget WHERE id=1').fetchone()
    policies=dict((r[0],tuple(r[1:])) for r in db.execute('SELECT * FROM policy'))
    if two_topic_phone_funded(db,cap,policies):return
    if not cedar_phone_funded(db,cap,policies):raise ValueError('Unexpected QA baseline')
    if db.execute("SELECT 1 FROM request WHERE state='active'").fetchone():raise ValueError('Active request')
    db.execute('INSERT INTO qa_budget_extension VALUES(?,?)',(TWO_TOPIC_PHONE_APPROVAL,45_000))
    db.execute('UPDATE budget SET cap=5230000 WHERE id=1')
    for category,(limit,_,_) in TWO_TOPIC_PHONE_POLICIES.items():
        db.execute('UPDATE policy SET cap=? WHERE category=?',(limit,category))


TWO_TOPIC_RESUME_APPROVAL = 'two-topic-resume-20260929-050'
TWO_TOPIC_RESUME_POLICIES = {'stt':(1_340_000,20_000,6),'ask':(3_085_000,3_000,20),'jev':(850_000,500,64)}

def two_topic_resume_funded(db,cap,policies):
    if cap!=(5_275_000,) or policies!=TWO_TOPIC_RESUME_POLICIES:return False
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='qa_budget_extension'").fetchone():return False
    return db.execute('SELECT amount FROM qa_budget_extension WHERE id=?',(TWO_TOPIC_RESUME_APPROVAL,)).fetchone()==(45_000,)

def extend_two_topic_resume_policy(db):
    """Explicit one-capture extension; no new proactive inference funding."""
    cap=db.execute('SELECT cap FROM budget WHERE id=1').fetchone()
    policies=dict((r[0],tuple(r[1:])) for r in db.execute('SELECT * FROM policy'))
    if two_topic_resume_funded(db,cap,policies):return
    if not two_topic_phone_funded(db,cap,policies):raise ValueError('Unexpected QA baseline')
    if db.execute("SELECT 1 FROM request WHERE state='active'").fetchone():raise ValueError('Active request')
    db.execute('INSERT INTO qa_budget_extension VALUES(?,?)',(TWO_TOPIC_RESUME_APPROVAL,45_000))
    db.execute('UPDATE budget SET cap=5275000 WHERE id=1')
    for category,(limit,_,_) in TWO_TOPIC_RESUME_POLICIES.items():
        db.execute('UPDATE policy SET cap=? WHERE category=?',(limit,category))


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
        if not two_topic_resume_funded(db,cap,policies) and not two_topic_phone_funded(db,cap,policies) and not cedar_phone_funded(db,cap,policies) and not proactive_phone_funded(db,cap,policies) and not private_dictation_funded(db,cap,policies) and (cap != (5_000_000,) or policies not in ({'stt': STT}, {'stt': STT, 'ask': ASK}, {'stt': STT, 'ask': ASK, 'jev': RETIRED_JEV}, ROLLOUT_POLICIES, PREFERENCE_POLICIES, DICTATION_POLICIES)):
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
    total=5_000_000
    if path.exists():
        with closing(sqlite3.connect(path)) as db:
            if db.execute("SELECT 1 FROM policy WHERE category='jev'").fetchone():
                limits['jev'] = RETIRED_JEV
            policies=dict((row[0],tuple(row[1:])) for row in db.execute('SELECT category,cap,reservation,daily FROM policy'))
            if enabled and policies in (ROLLOUT_POLICIES,PREFERENCE_POLICIES,DICTATION_POLICIES):limits=dict(policies)
            if enabled and private_dictation_funded(db,db.execute('SELECT cap FROM budget WHERE id=1').fetchone(),policies):
                limits=dict(policies);total=5_050_000
            if enabled and proactive_phone_funded(db,db.execute('SELECT cap FROM budget WHERE id=1').fetchone(),policies):
                limits=dict(policies);total=5_140_000
            if enabled and cedar_phone_funded(db,db.execute('SELECT cap FROM budget WHERE id=1').fetchone(),policies):
                limits=dict(policies);total=5_185_000
            if enabled and two_topic_phone_funded(db,db.execute('SELECT cap FROM budget WHERE id=1').fetchone(),policies):
                limits=dict(policies);total=5_230_000
            if enabled and two_topic_resume_funded(db,db.execute('SELECT cap FROM budget WHERE id=1').fetchone(),policies):
                limits=dict(policies);total=5_275_000
    return Admission(path, total_microusd=total, limits=limits)
