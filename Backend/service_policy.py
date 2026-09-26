"""Approved founder trial policy; migration requires the service's exclusive process lock."""
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
        if cap != (5_000_000,) or policies not in ({'stt': STT}, {'stt': STT, 'ask': ASK}, {'stt': STT, 'ask': ASK, 'jev': RETIRED_JEV}, ROLLOUT_POLICIES):
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
            if enabled and policies==ROLLOUT_POLICIES:limits=dict(ROLLOUT_POLICIES)
    return Admission(path, total_microusd=5_000_000, limits=limits)
