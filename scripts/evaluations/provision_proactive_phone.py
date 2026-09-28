"""Operator-only $0.09 extension approved September 28. No provider calls.

Run from Backend import path on the existing service, after a data backup.
Atomic accounting across usage and notes DBs; never invoked by hosted startup.
"""
import json,os,sqlite3,time
from pathlib import Path
from service_policy import extend_proactive_phone_policy
from proactive_phone_qa import APPROVAL


def provision(root):
    root=Path(root)
    config=root/'proactive-phone-qa.json'
    if config.exists():raise ValueError('Phone QA already provisioned; do not reset its window')
    now=time.time()
    with sqlite3.connect(root/'memory.sqlite') as memory,sqlite3.connect(root/'usage.sqlite') as db:
        active=[r[0] for r in db.execute('SELECT id FROM credential WHERE revoked=0 AND expires>?',(now,))]
        owners=memory.execute('SELECT DISTINCT owner FROM credential_owner WHERE credential IN (%s)'%','.join('?'*len(active)),active).fetchall()
        if len(owners)!=1:raise ValueError('Expected one enrolled account')
        owner=owners[0][0]
        credential=memory.execute('SELECT credential FROM credential_owner WHERE owner=?',(owner,)).fetchone()[0]
        if memory.execute("SELECT 1 FROM recording_notes WHERE state IN ('pending','generating')").fetchone():raise ValueError('Pending notes must be resolved first')
        if memory.execute("SELECT 1 FROM job WHERE state IN ('queued','running','leased')").fetchone():raise ValueError('Pending learning must be resolved first')
        db.execute('ATTACH DATABASE ? AS notes',(str(root/'notes-budget.sqlite'),))
        db.execute('BEGIN IMMEDIATE')
        extend_proactive_phone_policy(db)
        prior=db.execute('SELECT reserved FROM request WHERE id=?',(APPROVAL,)).fetchone()
        if prior and prior!=(50000,):raise ValueError('Allocation conflict')
        db.execute('INSERT OR IGNORE INTO request VALUES(?,?,?,?,?,?)',(APPROVAL,credential,'ask',now,50000,'completed'))
        db.execute('INSERT OR IGNORE INTO allocation_request VALUES(?)',(APPROVAL,))
        db.execute('INSERT OR IGNORE INTO notes.notes_allocation VALUES(?,?,?)',(APPROVAL,50000,2))
        db.commit()
    with sqlite3.connect(root/'proactive-phone-qa.sqlite') as db:
        db.execute('CREATE TABLE IF NOT EXISTS capture(id TEXT PRIMARY KEY)')
    config.write_text(json.dumps(dict(approval=APPROVAL,owner=owner,starts=now,expires=now+86400)))
    config.chmod(0o600)
    print(json.dumps(dict(provisioned=True,extra_microusd=90000,recordings=2,notes=2,proactive_calls_remaining=5,expires=now+86400)))

if __name__=='__main__':provision(os.environ['VOICE_DATA_DIR'])
