"""Source-scoped learning QA; reallocated $0.05 / two Jev and two Luna calls, no app enablement or paid retries."""
import hashlib,json,math,os,sqlite3,sys,time,urllib.request
from pathlib import Path
from contextlib import closing
ROOT=Path('/var/data/voice-companion')
ID='source-scoped-learning-20260927-005'
PARENT='unified-recall-20260927-025'
CAP=50000

def provision():
    # Reserve the child envelope inside the existing grant before creating it.
    # A failed setup can be retried, but cannot release or duplicate that reserve.
    with closing(sqlite3.connect(ROOT/(PARENT+'.sqlite'),isolation_level=None)) as db:
        db.execute('BEGIN IMMEDIATE')
        assert db.execute('SELECT * FROM allocation').fetchall()==[(PARENT,250000,5550000)]
        previous=db.execute('SELECT model,reserved,state FROM attempts WHERE id=?',(ID,)).fetchone()
        if previous is None:
            assert db.execute('SELECT coalesce(sum(reserved),0) FROM attempts').fetchone()[0]+CAP<=250000
            db.execute('INSERT INTO attempts VALUES(?,?,?,?,NULL)',(ID,'allocation',CAP,'allocated'))
        else:assert previous==('allocation',CAP,'allocated')
        db.commit()
    with closing(sqlite3.connect(ROOT/(ID+'.sqlite'))) as db,db:
        db.execute('CREATE TABLE IF NOT EXISTS allocation(id TEXT PRIMARY KEY,cap INTEGER,combined_cap INTEGER)')
        db.execute('INSERT OR IGNORE INTO allocation VALUES(?,?,?)',(ID,CAP,5550000))
        assert db.execute('SELECT * FROM allocation').fetchall()==[(ID,CAP,5550000)]
        db.execute('CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,model TEXT,reserved INTEGER,state TEXT,usage TEXT)')
    return dict(approval=ID,parent=PARENT,reallocated_microusd=CAP,combined_cap=5550000,
                additional_global_allocation=0,runtime_quotas_unchanged=True)


def run(req):
    with closing(sqlite3.connect('file:'+str(ROOT/(ID+'.sqlite'))+'?mode=ro',uri=True)) as ledger:
        assert ledger.execute('SELECT * FROM allocation').fetchall()==[(ID,CAP,5550000)]
    model=req.get('model')
    size=len(json.dumps(req,ensure_ascii=False).encode())
    if model=='jev-1.13.0':
        assert set(req)=={'model','state','questions'} and 1<=len(req['questions'])<=12 and size<=28000
        bound=5000;endpoint='https://api.typesafe.ai/v1/systemone';secret='TYPESAFE_API_KEY'
    else:
        assert model=='gpt-6-luna' and size<=40000
        assert req.get('store') is False and req.get('tools')==[] and req.get('service_tier')=='default'
        assert req.get('reasoning')=={'effort':'low'} and req.get('max_output_tokens')==3000
        assert req.get('text',{}).get('format',{}).get('name')=='identity_resolution'
        bound=20000;endpoint='https://api.openai.com/v1/responses';secret='OPENAI_API_KEY'
    key=hashlib.sha256(json.dumps(req,sort_keys=True).encode()).hexdigest()
    directory=ROOT/ID;directory.mkdir(exist_ok=True)
    output=directory/(key+'.json')
    if output.exists():
        saved=json.loads(output.read_text());assert saved['request']==req;return saved
    db=sqlite3.connect(ROOT/(ID+'.sqlite'),isolation_level=None)
    try:
        db.execute('BEGIN IMMEDIATE')
        assert db.execute('SELECT count(*) FROM attempts WHERE model=?',(model,)).fetchone()[0]<2,'QA model call limit'
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
        for line in sys.stdin:
            try:print(json.dumps(run(json.loads(line))),flush=True)
            except Exception as error:
                print(json.dumps({'error':type(error).__name__+': '+str(error)}),flush=True);break
