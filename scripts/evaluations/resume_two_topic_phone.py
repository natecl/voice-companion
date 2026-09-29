"""One approved additional recording/note; reuse existing seven model calls and expiry."""
import json,os,sqlite3,time
from pathlib import Path
from proactive_phone_qa import TWO_TOPIC_APPROVAL
from service_policy import extend_two_topic_resume_policy,TWO_TOPIC_RESUME_APPROVAL

SEEDS = ('two-topic-pilot-cedar','two-topic-pilot-harbor')

def provision(root):
    root=Path(root);config=root/'proactive-phone-qa.json'
    old=json.loads(config.read_text())
    if old['approval']!=TWO_TOPIC_APPROVAL:raise ValueError('Unexpected prior experiment or already resumed')
    now=time.time();owner=old['owner']
    if not old['starts']<=now<old['expires']:raise ValueError('Original test window expired')
    with sqlite3.connect(root/TWO_TOPIC_APPROVAL/'usage.sqlite') as usage:
        if usage.execute('SELECT count(*) FROM attempts').fetchone()[0]!=1:raise ValueError('Expected one consumed proactive call')
    with sqlite3.connect(root/'memory.sqlite') as memory,sqlite3.connect(root/'usage.sqlite') as db:
        credentials=memory.execute('SELECT credential FROM credential_owner WHERE owner=?',(owner,)).fetchall()
        active=[c[0] for c in credentials if db.execute('SELECT 1 FROM credential WHERE id=? AND revoked=0 AND expires>?',(c[0],now)).fetchone()]
        if not active:raise ValueError('No active account credential')
        if memory.execute("SELECT 1 FROM recording_notes WHERE state IN ('pending','generating')").fetchone():raise ValueError('Pending notes')
        if memory.execute("SELECT 1 FROM job WHERE state IN ('queued','running','leased')").fetchone():raise ValueError('Pending learning')
        db.execute('ATTACH DATABASE ? AS notes',(str(root/'notes-budget.sqlite'),))
        db.execute('BEGIN IMMEDIATE');extend_two_topic_resume_policy(db)
        prior=db.execute('SELECT reserved FROM request WHERE id=?',(TWO_TOPIC_RESUME_APPROVAL,)).fetchone()
        if prior and prior!=(25000,):raise ValueError('Allocation conflict')
        db.execute('INSERT OR IGNORE INTO request VALUES(?,?,?,?,?,?)',(TWO_TOPIC_RESUME_APPROVAL,active[0],'ask',now,25000,'completed'))
        db.execute('INSERT OR IGNORE INTO allocation_request VALUES(?)',(TWO_TOPIC_RESUME_APPROVAL,))
        db.execute('INSERT OR IGNORE INTO notes.notes_allocation VALUES(?,?,?)',(TWO_TOPIC_RESUME_APPROVAL,25000,1))
        db.commit()
    with sqlite3.connect(root/'two-topic-resume-qa.sqlite') as db:
        db.execute('CREATE TABLE IF NOT EXISTS capture(id TEXT PRIMARY KEY)')
        db.executemany('INSERT OR IGNORE INTO capture VALUES(?)',[(key,) for key in SEEDS])
    # Retain old config for auditing; final atomic switch selects the new allowance.
    archived=root/'proactive-phone-qa-before-resume.json'
    if not archived.exists():archived.write_text(json.dumps(old));archived.chmod(0o600)
    temp=config.with_suffix('.tmp')
    temp.write_text(json.dumps(dict(approval=TWO_TOPIC_RESUME_APPROVAL,owner=owner,starts=old['starts'],expires=old['expires'])))
    temp.chmod(0o600);temp.replace(config)
    return dict(seed_ids=list(SEEDS),recordings=1,notes=1,remaining_proactive_calls=7,new_reserved_microusd=45000,expires=old['expires'])

if __name__=='__main__':print(json.dumps(provision(os.environ['VOICE_DATA_DIR'])))
