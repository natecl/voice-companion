"""Isolated operator QA; $0.25 approval, no app enablement, no paid retries."""
import hashlib,json,math,os,sqlite3,sys,time,urllib.request
from pathlib import Path
ROOT=Path('/var/data/voice-companion')
ID='independent-verification-20260926-025'
CAP=250000

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
        db.commit()
    with sqlite3.connect(ROOT/(ID+'.sqlite')) as db:
        db.execute('CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY, model TEXT, reserved INTEGER,state TEXT,usage TEXT)')
    return {'approval':ID,'reserved_microusd':CAP,'funding_category':'stt','runtime_policy_unchanged':True}

def run(req):
    model=req.get('model');size=len(json.dumps(req,ensure_ascii=False).encode())
    assert size<=40000
    if model=='jev-1.13.0':
        assert set(req)=={'model','state','questions'}
        bound=10000;endpoint='https://api.typesafe.ai/v1/systemone';secret='TYPESAFE_API_KEY'
    else:
        assert model in ('gpt-6-sol','gpt-6-luna')
        assert req.get('store') is False and req.get('tools')==[] and req.get('service_tier')=='default'
        assert req.get('reasoning') in ({'effort':'none'},{'effort':'low'})
        maximum=req['max_output_tokens'];assert 1<=maximum<=3000
        if model=='gpt-6-sol':
            assert req['reasoning']=={'effort':'low'} and maximum<=1300
            bound=math.ceil((size+2048)*2.5+maximum*10)
        else:bound=math.ceil((size+2048)*.25+maximum*.75)
        endpoint='https://api.openai.com/v1/responses';secret='OPENAI_API_KEY'
    assert bound<=45000
    key=hashlib.sha256(json.dumps(req,sort_keys=True).encode()).hexdigest()
    directory=ROOT/ID;directory.mkdir(exist_ok=True)
    output=directory/(key+'.json')
    if output.exists():
        saved=json.loads(output.read_text());assert saved['request']==req;return saved
    db=sqlite3.connect(ROOT/(ID+'.sqlite'),isolation_level=None)
    db.execute('BEGIN IMMEDIATE')
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
