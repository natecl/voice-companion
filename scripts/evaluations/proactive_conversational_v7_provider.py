"""Founder-approved isolated $0.20 / ten-call conversational screen. Bounded batches; no retries."""
import hashlib,json,os,sqlite3,time,urllib.request,urllib.error
from pathlib import Path

def run(rows):
    assert 1 <= len(rows) <= 10
    assert len({r['case'] for r in rows}) == len(rows)
    assert all(r['case'].replace('-', '').isalnum() for r in rows)
    for row in rows:
        request = row['request']
        assert request['model'] == 'gpt-6-luna'
        assert request['max_output_tokens'] == 600 and request['tools'] == []
        assert request['store'] is False and request['reasoning'] == {'effort': 'none'}
        assert request['service_tier'] == 'default' and request['truncation'] == 'disabled'
        assert request['text']['format']['strict'] is True
        assert len(json.dumps(request).encode()) <= 20000

    root=Path('/var/data/voice-companion/conversational-v7-20260929-200')
    root.mkdir(exist_ok=True)
    with sqlite3.connect(root.parent/'usage.sqlite') as db:
        assert not db.execute("SELECT 1 FROM request WHERE state='active'").fetchone(), 'Capture must be stopped'
    output=root
    with sqlite3.connect(root/'usage.sqlite') as db:
        db.execute('CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,hash TEXT,reserved INTEGER,state TEXT,usage TEXT)')
    with sqlite3.connect(root/'usage.sqlite') as db:
        db.execute('BEGIN IMMEDIATE')
        count, reserved = db.execute('SELECT count(*),coalesce(sum(reserved),0) FROM attempts').fetchone()
        assert count + len(rows) <= 10 and reserved + 20000 * len(rows) <= 200000, 'Allowance exhausted'
        assert not db.execute("SELECT 1 FROM attempts WHERE state != 'completed'").fetchone(), 'Inspect incomplete batch; never retry'
        assert not any(db.execute('SELECT 1 FROM attempts WHERE hash=?', (hashlib.sha256(json.dumps(r['request'],sort_keys=True).encode()).hexdigest(),)).fetchone() for r in rows), 'Identical request already consumed'
        for row in rows:
            key='conversational-v7:'+row['case']
            digest=hashlib.sha256(json.dumps(row['request'],sort_keys=True).encode()).hexdigest()
            db.execute('INSERT INTO attempts VALUES(?,?,?,?,NULL)',(key,digest,20000,'reserved'))
        db.commit()
    for row in rows:
        key='conversational-v7:'+row['case']
        with sqlite3.connect(root/'usage.sqlite') as db:
            db.execute('BEGIN IMMEDIATE')
            assert db.execute('SELECT state FROM attempts WHERE id=?',(key,)).fetchone()==('reserved',)
            db.execute("UPDATE attempts SET state='sending' WHERE id=?",(key,))
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


if __name__=='__main__':run(ROWS)
