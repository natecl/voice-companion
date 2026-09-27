"""Companion style QA; $0.20 / ten Luna calls, no app enablement or paid retries."""
import hashlib,json,math,os,sqlite3,sys,time,urllib.request
from pathlib import Path
from contextlib import closing
ROOT=Path('/var/data/voice-companion')
ID='companion-style-20260927-020'
CAP=200000

def provision():
    # Approved extension is operator-only. Do not change the application's $5
    # startup contract or runtime quotas. Combined envelopes are capped at $5.75.
    with closing(sqlite3.connect('file:'+str(ROOT/'usage.sqlite')+'?mode=ro',uri=True)) as db:
        assert db.execute('SELECT cap FROM budget WHERE id=1').fetchone()[0]==5000000
        prior=db.execute('SELECT coalesce(sum(reserved),0) FROM request').fetchone()[0]
    with closing(sqlite3.connect('file:'+str(ROOT/'matched-recall-20260927-030.sqlite')+'?mode=ro',uri=True)) as db:
        previous=db.execute('SELECT cap FROM allocation WHERE id=?',('matched-recall-20260927-030',)).fetchone()[0]
        assert previous==300000
    with closing(sqlite3.connect('file:'+str(ROOT/'unified-recall-20260927-025.sqlite')+'?mode=ro',uri=True)) as db:
        unified=db.execute('SELECT cap FROM allocation WHERE id=?',('unified-recall-20260927-025',)).fetchone()[0]
        assert unified==250000
    assert 5000000+previous+unified+CAP<=5750000
    with closing(sqlite3.connect(ROOT/(ID+'.sqlite'))) as db, db:
        db.execute('CREATE TABLE IF NOT EXISTS allocation(id TEXT PRIMARY KEY,cap INTEGER,combined_cap INTEGER)')
        db.execute('INSERT OR IGNORE INTO allocation VALUES(?,?,?)',(ID,CAP,5750000))
        assert db.execute('SELECT * FROM allocation').fetchall()==[(ID,CAP,5750000)]
        db.execute('CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,model TEXT,reserved INTEGER,state TEXT,usage TEXT)')
    return dict(approval=ID,allocated_microusd=CAP,combined_cap=5750000,
                combined_reserved=prior+previous+unified+CAP,runtime_envelope_unchanged=5000000)


def run(req):
    with closing(sqlite3.connect('file:'+str(ROOT/(ID+'.sqlite'))+'?mode=ro',uri=True)) as ledger:
        assert ledger.execute('SELECT * FROM allocation').fetchall()==[(ID,CAP,5750000)]
    model=req.get('model')
    size=len(json.dumps(req,ensure_ascii=False).encode())
    assert model=='gpt-6-luna' and size<=16000
    assert req.get('store') is False and req.get('tools')==[] and req.get('service_tier')=='default'
    assert req.get('reasoning')=={'effort':'none'} and req.get('max_output_tokens')==1000
    assert req.get('truncation')=='disabled' and req.get('stream') is False
    bound=20000;endpoint='https://api.openai.com/v1/responses';secret='OPENAI_API_KEY'
    key=hashlib.sha256(json.dumps(req,sort_keys=True).encode()).hexdigest()
    directory=ROOT/ID;directory.mkdir(exist_ok=True)
    output=directory/(key+'.json')
    if output.exists():
        saved=json.loads(output.read_text());assert saved['request']==req;return saved
    db=sqlite3.connect(ROOT/(ID+'.sqlite'),isolation_level=None)
    try:
        db.execute('BEGIN IMMEDIATE')
        assert db.execute('SELECT count(*) FROM attempts WHERE model=?',(model,)).fetchone()[0]<10,'QA model call limit'
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
