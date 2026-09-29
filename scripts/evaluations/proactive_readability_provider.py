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
from pathlib import Path


def run(rows):
    expected = {'cedar-prerequisite', 'qualified-plan', 'fresh-changed-preference',
                'fresh-unknown-subject', 'fresh-resolved'}
    assert len(rows) == 5 and {r['case'] for r in rows} == expected
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
        assert count == 1 and reserved == 20000, 'Expected precisely five unused calls; never retry batch'
        for row in rows:
            request_hash = hashlib.sha256(json.dumps(row['request'],sort_keys=True).encode()).hexdigest()
            db.execute('INSERT INTO attempts VALUES(?,?,?,?,NULL)',
                       ('readability:'+row['case'],request_hash,20000,'reserved'))
        db.commit()
    for row in rows:
        key = 'readability:'+row['case']
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
            # Retain a safe status for diagnosis without logging provider bodies or credentials.
            print(json.dumps(dict(case=row['case'],error=type(error).__name__,
                                  status=getattr(error,'code',None))),flush=True)
            break  # Keep remaining reservations; an operator must inspect before any new work.


if __name__ == '__main__':
    run(ROWS)
