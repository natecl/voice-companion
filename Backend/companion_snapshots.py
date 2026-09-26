"""Immutable evidence from an in-progress recording, outside durable learned memory."""
import hashlib
import json
from admission import Rejected

SCHEMA='''BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS companion_snapshot(
 owner TEXT NOT NULL REFERENCES owner(id), id TEXT NOT NULL, session TEXT NOT NULL,
 payload TEXT NOT NULL, PRIMARY KEY(owner,id));
CREATE INDEX IF NOT EXISTS companion_snapshot_session ON companion_snapshot(owner,session);
PRAGMA user_version=14; COMMIT;'''


def matches(items,source):
    passages={p['id']:p for p in source['passages']}
    return all(item['passage_id'] in passages and
        passages[item['passage_id']]['text'][item['text_start']:item['text_end']]==item['text'] for item in items)


def freeze(store,owner,source,refs):
    from memory_store import validate_source
    from memory_context import fingerprint
    validate_source(source)
    if source['completed'] or source.get('origin') is not None or len(refs)>12:raise Rejected('invalid_live_snapshot')
    items=[]
    for ref in refs:
        p=next((p for p in source['passages'] if p['id']==ref.get('passage_id')),None)
        start,end=ref.get('text_start'),ref.get('text_end')
        if (p is None or ref.get('session_id')!=source['session_id'] or ref.get('revision')!=source['revision']
                or type(start) is not int or type(end) is not int or not 0<=start<end<=len(p['text'])):
            raise Rejected('invalid_live_span')
        items.append(dict(session_id=source['session_id'],revision=source['revision'],passage_id=p['id'],
            text_start=start,text_end=end,text=p['text'][start:end],start=p['start'],speakers=p['speakers'],
            captured_at=source['captured_at'],timezone=source['timezone'],evidence_type='live_snapshot',
            origin='recording',scope='historical_capture_cutoff'))
    payload=json.dumps(items,sort_keys=True,ensure_ascii=False)
    if len(payload.encode())>9000:raise Rejected('live_snapshot_too_large')
    snapshot_id=hashlib.sha256(payload.encode()).hexdigest()
    with store.transaction() as db:
        canonical=db.execute('SELECT payload,deleted FROM source WHERE owner=? AND session=?',(owner,source['session_id'])).fetchone()
        if canonical and (canonical['deleted'] or not matches(items,json.loads(canonical['payload']))):
            raise Rejected('live_snapshot_changed')
        old=db.execute('SELECT 1 FROM companion_snapshot WHERE owner=? AND id=?',(owner,snapshot_id)).fetchone()
        if not old:
            if db.execute('SELECT count(*) FROM companion_snapshot WHERE owner=?',(owner,)).fetchone()[0]>=1000:
                raise Rejected('live_snapshot_storage_limit')
            db.execute('INSERT INTO companion_snapshot VALUES(?,?,?,?)',(owner,snapshot_id,source['session_id'],payload))
    items=[dict(item,snapshot_id=snapshot_id) for item in items]
    return dict(version='selected-evidence-v1',owner=owner,items=items,digest=fingerprint(items))


def hydrate(db,owner,ref):
    row=db.execute('SELECT payload FROM companion_snapshot WHERE owner=? AND id=?',(owner,ref['snapshot_id'])).fetchone()
    if row is None:return None
    keys=('session_id','revision','passage_id','text_start','text_end')
    return next((dict(item,snapshot_id=ref['snapshot_id']) for item in json.loads(row['payload'])
                 if all(item[k]==ref.get(k) for k in keys)),None)


def reconcile(db,owner,source):
    """Appending speech keeps answers. Rewriting used words invalidates their descendants."""
    from companion_chat import scrub
    rows=db.execute('SELECT id,payload FROM companion_snapshot WHERE owner=? AND session=?',(owner,source['session_id'])).fetchall()
    for row in rows:
        if matches(json.loads(row['payload']),source):continue
        turns=db.execute("SELECT DISTINCT turn FROM companion_dependency WHERE owner=? AND json_extract(reference,'$.snapshot_id')=?",(owner,row['id'])).fetchall()
        for turn in turns:scrub(db,owner,turn['turn'])
        db.execute('DELETE FROM companion_snapshot WHERE owner=? AND id=?',(owner,row['id']))


def release(store,owner,snapshot_id):
    """Discard unused prepared evidence after failed/cancelled generation; never referenced evidence."""
    with store.transaction() as db:
        db.execute("DELETE FROM companion_snapshot WHERE owner=? AND id=? AND NOT EXISTS(SELECT 1 FROM companion_dependency WHERE owner=? AND json_extract(reference,'$.snapshot_id')=?)",
                   (owner,snapshot_id,owner,snapshot_id))
