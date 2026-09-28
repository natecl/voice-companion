"""Explicit $0.165 of the approved $0.17 phone pilot. No provider calls.

Run after backup on the compatible deployed backend. Re-entry never replenishes funding.
Fictional evidence is excluded from learning; no generated note is requested for the seed.
"""
import json,os,sqlite3,time
from pathlib import Path
from memory_store import MemoryStore
from proactive_phone_qa import CEDAR_APPROVAL
from service_policy import extend_cedar_phone_policy

SEED_ID='cedar-fictional-pilot-20260928'
SEED_TEXT=('For the Cedar pilot, '
    'the team agreed to test the basic recording flow with five people before adding features. '
    'Those tests have not happened yet. Calendar integration should wait until afterward.')

def provision(root):
    root=Path(root);config=root/'proactive-phone-qa.json'
    old=json.loads(config.read_text())
    if old['approval']==CEDAR_APPROVAL:raise ValueError('Already provisioned; do not reset the window')
    if old['approval']!='proactive-phone-20260928-090':raise ValueError('Unexpected prior experiment')
    now=time.time();owner=old['owner']
    with sqlite3.connect(root/'memory.sqlite') as memory,sqlite3.connect(root/'usage.sqlite') as db:
        credentials=memory.execute('SELECT credential FROM credential_owner WHERE owner=?',(owner,)).fetchall()
        active=[c[0] for c in credentials if db.execute('SELECT 1 FROM credential WHERE id=? AND revoked=0 AND expires>?',(c[0],now)).fetchone()]
        if not active:raise ValueError('No active account credential')
        if memory.execute("SELECT 1 FROM recording_notes WHERE state IN ('pending','generating')").fetchone():raise ValueError('Pending notes')
        if memory.execute("SELECT 1 FROM job WHERE state IN ('queued','running','leased')").fetchone():raise ValueError('Pending learning')
        db.execute('ATTACH DATABASE ? AS notes',(str(root/'notes-budget.sqlite'),))
        db.execute('BEGIN IMMEDIATE');extend_cedar_phone_policy(db)
        prior=db.execute('SELECT reserved FROM request WHERE id=?',(CEDAR_APPROVAL,)).fetchone()
        if prior and prior!=(25000,):raise ValueError('Allocation conflict')
        db.execute('INSERT OR IGNORE INTO request VALUES(?,?,?,?,?,?)',(CEDAR_APPROVAL,active[0],'ask',now,25000,'completed'))
        db.execute('INSERT OR IGNORE INTO allocation_request VALUES(?)',(CEDAR_APPROVAL,))
        db.execute('INSERT OR IGNORE INTO notes.notes_allocation VALUES(?,?,?)',(CEDAR_APPROVAL,25000,1))
        db.commit()
    folder=root/CEDAR_APPROVAL;folder.mkdir(exist_ok=True)
    with sqlite3.connect(folder/'usage.sqlite') as db:
        db.execute('CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,hash TEXT,reserved INTEGER,state TEXT,usage TEXT)')
    with sqlite3.connect(root/'cedar-phone-qa.sqlite') as db:
        db.execute('CREATE TABLE IF NOT EXISTS capture(id TEXT PRIMARY KEY)')
        db.execute('INSERT OR IGNORE INTO capture VALUES(?)',(SEED_ID,))
    store=MemoryStore(root/'memory.sqlite')
    store.put_source(owner,dict(session_id=SEED_ID,revision=1,captured_at=now,timezone='America/New_York',completed=True,
        passages=[dict(id='p1',start=0.,duration=20.,text=SEED_TEXT,speakers=[])]),learn=False,generate_notes=False)
    # Retain old config for auditing; final atomic switch selects the new allowance.
    archived=root/'proactive-phone-qa-before-cedar.json'
    if not archived.exists():archived.write_text(json.dumps(old));archived.chmod(0o600)
    temp=config.with_suffix('.tmp')
    temp.write_text(json.dumps(dict(approval=CEDAR_APPROVAL,owner=owner,starts=now,expires=now+86400)))
    temp.chmod(0o600);temp.replace(config)
    return dict(seed_id=SEED_ID,recordings=1,notes=1,proactive_calls=6,reserved_limit_microusd=165000,expires=now+86400)

if __name__=='__main__':print(json.dumps(provision(os.environ['VOICE_DATA_DIR'])))
