"""Isolated founder-approved proactive QA: $0.25, 12 total calls, no retries.

Runs on the operator host using existing credentials. Never changes runtime quotas.
"""
import hashlib,json,os,sqlite3,sys,time,urllib.request
from pathlib import Path
ROOT=Path('/var/data/voice-companion/proactive-20260928-025')
CAP=250000


def run(payload):
    key=payload['id'];req=payload['request'];model=req.get('model')
    allowed = {f'{case}:{route}:{kind}' for case in ('sleep-relevant','already-addressed','wrong-person')
        for route in ('llm','jev') for kind in ('judge','draft')}
    allowed.update(f'semantic-{case}:llm:draft' for case in ('wrong-person','fictional','instruction'))
    assert key in allowed
    assert len(json.dumps(req,ensure_ascii=False).encode())<=16000
    if model=='gpt-6-luna':
        assert key.endswith(':draft')
        assert req.get('max_output_tokens')==600 and req.get('tools')==[] and req.get('store') is False
        assert req.get('reasoning')=={'effort':'none'} and req.get('service_tier')=='default'
        assert req.get('truncation')=='disabled' and req.get('text',{}).get('format',{}).get('strict') is True
        bound=20000;url='https://api.openai.com/v1/responses';secret='OPENAI_API_KEY'
    else:
        assert model=='jev-1.13.0' and key.endswith(':jev:judge')
        assert set(req)=={'model','state','questions'} and set(req['questions'])=={'connection','novelty'}
        bound=5000;url='https://api.typesafe.ai/v1/systemone';secret='TYPESAFE_API_KEY'
    ROOT.mkdir(exist_ok=True)
    path=ROOT/(key+'.json')
    if path.exists():
        saved=json.loads(path.read_text());assert saved['request']==req;return dict(saved,cached=True)
    db=sqlite3.connect(ROOT/'usage.sqlite',isolation_level=None)
    db.execute('CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,hash TEXT,reserved INTEGER,state TEXT,usage TEXT)')
    db.execute('BEGIN IMMEDIATE')
    try:
        assert not db.execute('SELECT 1 FROM attempts WHERE id=?',(key,)).fetchone(),'No paid retry'
        count,reserved=db.execute('SELECT count(*),coalesce(sum(reserved),0) FROM attempts').fetchone()
        assert count<12 and reserved+bound<=CAP,'Allowance exhausted'
        db.execute('INSERT INTO attempts VALUES(?,?,?,?,NULL)',(key,hashlib.sha256(json.dumps(req,sort_keys=True).encode()).hexdigest(),bound,'reserved'))
        db.commit()
    except BaseException:db.rollback();db.close();raise
    start=time.monotonic()
    try:
        request=urllib.request.Request(url,data=json.dumps(req).encode(),headers={'Authorization':'Bearer '+os.environ[secret],'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=15) as response:raw=json.load(response)
        saved=dict(id=key,request=req,raw=raw,seconds=time.monotonic()-start,reserved_microusd=bound)
        path.write_text(json.dumps(saved));path.chmod(0o600)
        db.execute("UPDATE attempts SET state='completed',usage=? WHERE id=?",(json.dumps(raw.get('usage')),key))
        return saved
    except BaseException:
        db.execute("UPDATE attempts SET state='failed' WHERE id=?",(key,));raise
    finally:db.close()


if __name__=='__main__':
    for line in sys.stdin:
        try:print(json.dumps(run(json.loads(line))),flush=True)
        except Exception as error:
            print(json.dumps({'error':type(error).__name__}),flush=True);break
