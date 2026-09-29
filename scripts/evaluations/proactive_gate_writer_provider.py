"""Isolated approved six-call/$0.06 screen. Run once per stage; never retry."""
import hashlib,json,os,sqlite3,sys,time,urllib.request
from pathlib import Path


def run(rows, stage):
    assert stage in ('gate','writer')
    assert len(rows)==6 and len({row['case'] for row in rows})==6
    assert sum(row['stage']=='gate' for row in rows)==4
    for row in rows:
        req=row['request']
        assert len(json.dumps(req).encode())<=16000
        if row['stage']=='gate':
            assert req['model']=='jev-1.13.0' and set(req)=={'model','state','questions'}
            assert set(req['questions'])=={'connection','novelty'}
        else:
            assert row['stage']=='writer' and req['model']=='gpt-6-luna'
            assert req['max_output_tokens']==600 and req['tools']==[] and req['store'] is False
            assert req['reasoning']=={'effort':'none'} and req['service_tier']=='default'
            assert req['truncation']=='disabled' and req['text']['format']['strict'] is True
    root=Path('/var/data/voice-companion/jev-writer-20260929-060')
    root.mkdir(exist_ok=True)
    with sqlite3.connect(root.parent/'usage.sqlite') as db:
        assert not db.execute("SELECT 1 FROM request WHERE state='active'").fetchone(), 'Capture must be stopped'
    with sqlite3.connect(root/'usage.sqlite') as db:
        db.execute('CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,hash TEXT,reserved INTEGER,state TEXT,usage TEXT)')
        db.execute('BEGIN IMMEDIATE')
        if db.execute('SELECT count(*) FROM attempts').fetchone()[0]==0:
            for row in rows:
                digest=hashlib.sha256(json.dumps(row['request'],sort_keys=True).encode()).hexdigest()
                db.execute('INSERT INTO attempts VALUES(?,?,?,?,NULL)',(row['case'],digest,5000 if row['stage']=='gate' else 20000,'reserved'))
        assert db.execute('SELECT count(*),sum(reserved) FROM attempts').fetchone()==(6,60000)
        db.commit()
    for row in rows:
        if row['stage']!=stage:continue
        req=row['request'];key=row['case']
        digest=hashlib.sha256(json.dumps(req,sort_keys=True).encode()).hexdigest()
        with sqlite3.connect(root/'usage.sqlite') as db:
            db.execute('BEGIN IMMEDIATE')
            assert db.execute('SELECT hash,state FROM attempts WHERE id=?',(key,)).fetchone()==(digest,'reserved'), 'No paid retry'
            db.execute("UPDATE attempts SET state='sending' WHERE id=?",(key,));db.commit()
        url,secret=('https://api.typesafe.ai/v1/systemone','TYPESAFE_API_KEY') if stage=='gate' else ('https://api.openai.com/v1/responses','OPENAI_API_KEY')
        started=time.monotonic()
        try:
            request=urllib.request.Request(url,data=json.dumps(req).encode(),headers={'Authorization':'Bearer '+os.environ[secret],'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=20) as response:raw=json.load(response)
            saved=dict(case=key,request=req,raw=raw,seconds=time.monotonic()-started)
            path=root/(key+'.json');path.write_text(json.dumps(saved));path.chmod(0o600)
            with sqlite3.connect(root/'usage.sqlite') as db:
                db.execute("UPDATE attempts SET state='completed',usage=? WHERE id=?",(json.dumps(raw.get('usage')),key))
            print(json.dumps(saved),flush=True)
        except Exception as error:
            with sqlite3.connect(root/'usage.sqlite') as db:db.execute("UPDATE attempts SET state='uncertain' WHERE id=?",(key,))
            print(json.dumps(dict(case=key,error=type(error).__name__)),flush=True)
            break


if __name__=='__main__':
    payload=json.load(sys.stdin);run(payload['rows'],payload['stage'])
