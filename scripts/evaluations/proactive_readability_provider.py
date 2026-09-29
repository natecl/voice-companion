"""Explicit five-call reallocation of remaining Cedar allowance; no retries.

Operator passes the five predeclared fictional requests as ROWS on the existing
credential host. Reserve the entire batch atomically in the shared phone ledger
before any request, so concurrent phone use cannot exceed the grant.
"""
import hashlib
import json
import os
import sqlite3
import time
import urllib.request
import urllib.error
from pathlib import Path


def run(rows, *, resume_unsent=False):
    expected = {'cedar-prerequisite', 'qualified-plan', 'fresh-changed-preference',
                'fresh-unknown-subject', 'fresh-resolved'}
    if resume_unsent:
        expected = {'fresh-changed-preference', 'fresh-unknown-subject', 'fresh-resolved'}
    assert len(rows) == len(expected) and {r['case'] for r in rows} == expected
    for row in rows:
        request = row['request']
        assert request['model'] == 'gpt-6-luna'
        assert request['max_output_tokens'] == 600 and request['tools'] == []
        assert request['store'] is False and request['reasoning'] == {'effort': 'none'}
        assert request['service_tier'] == 'default' and request['truncation'] == 'disabled'
        assert request['text']['format']['strict'] is True
        assert len(json.dumps(request).encode()) <= 20000
    root = Path('/var/data/voice-companion/cedar-phone-20260928-170')
    output = root/'readability'; output.mkdir(exist_ok=True)
    with sqlite3.connect(root/'usage.sqlite') as db:
        db.execute('BEGIN IMMEDIATE')
        count, reserved = db.execute('SELECT count(*),coalesce(sum(reserved),0) FROM attempts').fetchone()
        if resume_unsent:
            assert count == 6 and reserved == 120000, 'Existing allowance only'
            for row in rows:
                key = 'readability:'+row['case']
                prior = db.execute('SELECT state FROM attempts WHERE id=?',(key,)).fetchone()
                assert prior == ('reserved',), 'Never repeat an attempted call'
                assert not (output/(row['case']+'.json')).exists()
        else:
            assert count == 1 and reserved == 20000, 'Expected precisely five unused calls'
            for row in rows:
                request_hash = hashlib.sha256(json.dumps(row['request'],sort_keys=True).encode()).hexdigest()
                db.execute('INSERT INTO attempts VALUES(?,?,?,?,NULL)',
                           ('readability:'+row['case'],request_hash,20000,'reserved'))
        db.commit()
    for row in rows:
        key = 'readability:'+row['case']
        # Claim before transport. A crash or HTTP error cannot leave a sent call resumable.
        with sqlite3.connect(root/'usage.sqlite') as db:
            db.execute('BEGIN IMMEDIATE')
            prior = db.execute('SELECT state,hash FROM attempts WHERE id=?',(key,)).fetchone()
            assert prior and prior[0] == 'reserved'
            digest = hashlib.sha256(json.dumps(row['request'],sort_keys=True).encode()).hexdigest()
            if resume_unsent:
                audit = output/(row['case']+'-unattempted-reassignment.json')
                assert not audit.exists()
                audit.write_text(json.dumps(dict(previous_hash=prior[1],new_hash=digest,
                    reason='Founder clarified character length; reuse unsent reserved slot only')))
            db.execute('UPDATE attempts SET state=?,hash=? WHERE id=?',('sending',digest,key))
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


if __name__ == '__main__':
    run(ROWS, resume_unsent=RESUME_UNSENT)
