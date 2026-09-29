"""Approved current-focus screen: $0.12 / six calls, no retries."""
import hashlib,json,os,sqlite3,time,urllib.request,urllib.error
from pathlib import Path

def run(rows):
    expected={'choir-unrelated', 'club-spending-limit', 'trail-unrelated', 'club-topic-only', 'trail-relevant', 'choir-relevant'}
    assert len(rows)==6 and {r["case"] for r in rows}==expected
    for row in rows:
        request = row['request']
        assert request['model'] == 'gpt-6-luna'
        assert request['max_output_tokens'] == 600 and request['tools'] == []
        assert request['store'] is False and request['reasoning'] == {'effort': 'none'}
        assert request['service_tier'] == 'default' and request['truncation'] == 'disabled'
        assert request['text']['format']['strict'] is True
        assert len(json.dumps(request).encode()) <= 20000

    root=Path('/var/data/voice-companion/proactive-focus-20260929-120')
    root.mkdir(exist_ok=True)
    output=root
    with sqlite3.connect(root/'usage.sqlite') as db:
        db.execute('CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,hash TEXT,reserved INTEGER,state TEXT,usage TEXT)')
    for row in rows:
        key=row['case']
        with sqlite3.connect(root/'usage.sqlite') as db:
            db.execute('BEGIN IMMEDIATE')
            count,total=db.execute('SELECT count(*),coalesce(sum(reserved),0) FROM attempts').fetchone()
            assert count<6 and total+20000<=120000,'Allowance exhausted'
            assert not db.execute('SELECT 1 FROM attempts WHERE id=?',(key,)).fetchone(),'No retry'
            digest=hashlib.sha256(json.dumps(row['request'],sort_keys=True).encode()).hexdigest()
            db.execute('INSERT INTO attempts VALUES(?,?,?,?,NULL)',(key,digest,20000,'sending'))
            db.commit()
        started = time.monotonic()
        try:
            request = urllib.request.Request('https://api.openai.com/v1/responses',
                data=json.dumps(row['request']).encode(), headers={
                    'Authorization':'Bearer '+os.environ['OPENAI_API_KEY'],
                    'Content-Type':'application/json'})
            with urllib.request.urlopen(request,timeout=15) as response:
                raw = json.load(response)
            saved = dict(case=row['case'],request=row['request'],raw=raw,seconds=time.monotonic()-started)
            path = output/(row['case']+'.json')
            path.write_text(json.dumps(saved)); path.chmod(0o600)
            with sqlite3.connect(root/'usage.sqlite') as db:
                db.execute('UPDATE attempts SET state=?,usage=? WHERE id=?',
                           ('completed',json.dumps(raw.get('usage')),key))
            print(json.dumps(saved),flush=True)
        except Exception as error:
            with sqlite3.connect(root/'usage.sqlite') as db:
                db.execute('UPDATE attempts SET state=? WHERE id=?',('uncertain',key))
            # Persist only safe API error identifiers, never body prose or credentials.
            code = None
            if isinstance(error, urllib.error.HTTPError):
                try:
                    code = json.loads(error.read()).get('error',{}).get('code')
                except (ValueError, AttributeError): pass
            print(json.dumps(dict(case=row['case'],error=type(error).__name__,
                                  status=getattr(error,'code',None),provider_code=code)),flush=True)
            break  # Keep remaining reservations; an operator must inspect before any new work.


if __name__=='__main__':
    import sys
    run(json.load(sys.stdin))
