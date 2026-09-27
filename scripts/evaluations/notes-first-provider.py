"""Notes-first operator QA; $0.15 / six Jev and six Luna calls, no app enablement or paid retries."""
import hashlib,json,math,os,sqlite3,sys,time,urllib.request
from pathlib import Path
from contextlib import closing
ROOT=Path('/var/data/voice-companion')
ID='notes-first-20260927-015'
CAP=150000

def provision():
    # Fund this operator-only reservation from unused recording allocation without
    # changing runtime policy/quotas. Category records funding, not API usage.
    with closing(sqlite3.connect(ROOT/'usage.sqlite',isolation_level=None)) as db, db:
        db.execute('BEGIN IMMEDIATE')
        total=db.execute('SELECT coalesce(sum(reserved),0) FROM request').fetchone()[0]
        grants=[('stt',70000),('jev',80000)]
        missing=sum(amount for category,amount in grants if not db.execute('SELECT 1 FROM request WHERE id=?',(ID+'-'+category,)).fetchone())
        assert total+missing<=db.execute('SELECT cap FROM budget WHERE id=1').fetchone()[0]==5000000
        for category,amount in grants:
            key=ID+'-'+category
            prior=db.execute('SELECT category,reserved FROM request WHERE id=?',(key,)).fetchone()
            if prior:assert prior==(category,amount)
            else:
                used=db.execute('SELECT coalesce(sum(reserved),0) FROM request WHERE category=?',(category,)).fetchone()[0]
                assert used+amount<=db.execute('SELECT cap FROM policy WHERE category=?',(category,)).fetchone()[0]
                credential=db.execute('SELECT id FROM credential ORDER BY rowid DESC LIMIT 1').fetchone()[0]
                db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)',(key,credential,category,time.time(),amount,'completed'))
            db.execute('INSERT OR IGNORE INTO allocation_request VALUES(?)',(key,))
        db.commit()
    with closing(sqlite3.connect(ROOT/(ID+'.sqlite'))) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY, model TEXT, reserved INTEGER,state TEXT,usage TEXT)')
    return {'approval':ID,'reserved_microusd':CAP,'funding_categories':{'stt':70000,'jev':80000},'runtime_policy_unchanged':True}

def run(req):
    with closing(sqlite3.connect('file:'+str(ROOT/'usage.sqlite')+'?mode=ro',uri=True)) as ledger:
        for category,amount in [('stt',70000),('jev',80000)]:
            assert ledger.execute('SELECT category,reserved FROM request WHERE id=?',(ID+'-'+category,)).fetchone()==(category,amount)
            assert ledger.execute('SELECT 1 FROM allocation_request WHERE id=?',(ID+'-'+category,)).fetchone()
    model=req.get('model')
    size=len(json.dumps(req,ensure_ascii=False).encode())
    if model=='jev-1.13.0':
        assert set(req)=={'model','state','questions'} and 1<=len(req['questions'])<=12 and size<=28000
        bound=5000;endpoint='https://api.typesafe.ai/v1/systemone';secret='TYPESAFE_API_KEY'
    else:
        assert model=='gpt-6-luna' and size<=40000
        assert req.get('store') is False and req.get('tools')==[] and req.get('service_tier')=='default'
        assert req.get('reasoning')=={'effort':'none'} and req.get('max_output_tokens')==1000
        bound=20000;endpoint='https://api.openai.com/v1/responses';secret='OPENAI_API_KEY'
    key=hashlib.sha256(json.dumps(req,sort_keys=True).encode()).hexdigest()
    directory=ROOT/ID;directory.mkdir(exist_ok=True)
    output=directory/(key+'.json')
    if output.exists():
        saved=json.loads(output.read_text());assert saved['request']==req;return saved
    db=sqlite3.connect(ROOT/(ID+'.sqlite'),isolation_level=None)
    try:
        db.execute('BEGIN IMMEDIATE')
        assert db.execute('SELECT count(*) FROM attempts WHERE model=?',(model,)).fetchone()[0]<6,'QA model call limit'
        assert not db.execute('SELECT 1 FROM attempts WHERE id=?',(key,)).fetchone(),'No automatic paid retry'
        assert db.execute('SELECT coalesce(sum(reserved),0) FROM attempts').fetchone()[0]+bound<=CAP,'QA allowance exhausted'
        db.execute('INSERT INTO attempts VALUES(?,?,?,?,NULL)',(key,model,bound,'reserved'));db.commit()
    except BaseException:
        db.rollback();db.close();raise
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
        print(json.dumps({'ready':True}),flush=True)
        for line in sys.stdin:
            try:print(json.dumps(run(json.loads(line))),flush=True)
            except Exception as error:
                print(json.dumps({'error':type(error).__name__+': '+str(error)}),flush=True);break
