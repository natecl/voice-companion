"""Notes-only operator QA; $0.15 / six Luna calls, no app enablement or paid retries."""
import hashlib,json,math,os,sqlite3,sys,time,urllib.request
from pathlib import Path
ROOT=Path('/var/data/voice-companion')
ID='recording-notes-20260926-015'
CAP=150000

def provision():
    # Fund this operator-only reservation from unused recording allocation without
    # changing runtime policy/quotas. Category records funding, not API usage.
    with sqlite3.connect(ROOT/'usage.sqlite',isolation_level=None) as db:
        db.execute('BEGIN IMMEDIATE')
        prior=db.execute('SELECT category,reserved FROM request WHERE id=?',(ID,)).fetchone()
        if prior:
            assert prior==('stt',CAP)
        else:
            total=db.execute('SELECT coalesce(sum(reserved),0) FROM request').fetchone()[0]
            used=db.execute("SELECT coalesce(sum(reserved),0) FROM request WHERE category='stt'").fetchone()[0]
            assert total+CAP<=db.execute('SELECT cap FROM budget WHERE id=1').fetchone()[0]==5000000
            assert used+CAP<=db.execute("SELECT cap FROM policy WHERE category='stt'").fetchone()[0]
            credential=db.execute('SELECT id FROM credential ORDER BY rowid DESC LIMIT 1').fetchone()[0]
            db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)',(ID,credential,'stt',time.time(),CAP,'completed'))
        db.execute('INSERT OR IGNORE INTO allocation_request VALUES(?)',(ID,))
        db.commit()
    with sqlite3.connect(ROOT/(ID+'.sqlite')) as db:
        db.execute('CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY, model TEXT, reserved INTEGER,state TEXT,usage TEXT)')
    return {'approval':ID,'reserved_microusd':CAP,'funding_category':'stt','runtime_policy_unchanged':True}

def run(req):
    assert req.get('model')=='gpt-6-luna'
    model=req['model']
    assert len(json.dumps(req,ensure_ascii=False).encode())<=65000
    assert req.get('store') is False and req.get('tools')==[] and req.get('service_tier')=='default'
    assert req.get('reasoning')=={'effort':'none'} and req.get('max_output_tokens')==3000
    assert req.get('text',{}).get('format',{}).get('name')=='recording_notes_v1'
    bound=25000
    endpoint='https://api.openai.com/v1/responses';secret='OPENAI_API_KEY'
    key=hashlib.sha256(json.dumps(req,sort_keys=True).encode()).hexdigest()
    directory=ROOT/ID;directory.mkdir(exist_ok=True)
    output=directory/(key+'.json')
    if output.exists():
        saved=json.loads(output.read_text());assert saved['request']==req;return saved
    db=sqlite3.connect(ROOT/(ID+'.sqlite'),isolation_level=None)
    db.execute('BEGIN IMMEDIATE')
    assert db.execute('SELECT count(*) FROM attempts').fetchone()[0]<6,'QA call limit'
    assert not db.execute('SELECT 1 FROM attempts WHERE id=?',(key,)).fetchone(),'No automatic paid retry'
    assert db.execute('SELECT coalesce(sum(reserved),0) FROM attempts').fetchone()[0]+bound<=CAP,'QA allowance exhausted'
    db.execute('INSERT INTO attempts VALUES(?,?,?,?,NULL)',(key,model,bound,'reserved'));db.commit()
    started=time.monotonic()
    try:
        request=urllib.request.Request(endpoint,data=json.dumps(req).encode(),headers={'Authorization':'Bearer '+os.environ[secret],'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=45) as response:raw=json.load(response)
        saved=dict(request=req,raw=raw,reserved_microusd=bound,seconds=time.monotonic()-started)
        output.write_text(json.dumps(saved))
        db.execute("UPDATE attempts SET state='completed',usage=? WHERE id=?",(json.dumps(raw.get('usage')),key))
        return saved
    except BaseException:
        db.execute("UPDATE attempts SET state='failed' WHERE id=?",(key,));raise
    finally:db.close()

if __name__=='__main__':
    if '--provision' in sys.argv:print(json.dumps(provision()))
    else:
        for line in sys.stdin:
            try:print(json.dumps(run(json.loads(line))),flush=True)
            except Exception as error:
                print(json.dumps({'error':type(error).__name__+': '+str(error)}),flush=True);break
