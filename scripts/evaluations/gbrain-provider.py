"""Operator-only paid transport. Run on credential host; never emits credentials.

Each new request reserves its conservative bound in the canonical global ledger.
The $0.50 comparison allowance does not enlarge application quotas or the $5 cap.
Completed identical requests replay for free; failed/reserved requests cannot retry.
"""
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import sys
import time
import urllib.request

PREFIX = 'gbrain-comparison-2026-09-26:'
ALLOWANCE = 500_000


def validate(request):
    kind = request['kind']
    body = request['body']
    size = len(json.dumps(body, ensure_ascii=False).encode())
    if size > 40_000:
        raise ValueError('Request too large')
    if kind == 'chat':
        if (body.get('model') != 'gpt-6-luna' or body.get('store') is not False
                or body.get('tools') != [] or body.get('service_tier') != 'default'
                or body.get('reasoning') != {'effort': 'none'}
                or not 1 <= body.get('max_output_tokens', 0) <= 4000):
            raise ValueError('Unapproved chat configuration')
        # Conservative $0.25/M input (including cache write), $0.75/M output.
        # UTF-8 bytes upper-bound text tokens; include framing room.
        bound = math.ceil((size + 2048) * .25 + body['max_output_tokens'] * .75)
        endpoint = 'responses'
    elif kind == 'embed':
        if (body.get('model') != 'text-embedding-3-small' or body.get('dimensions') != 1536
                or not isinstance(body.get('input'), list) or not 1 <= len(body['input']) <= 16
                or any(not isinstance(t, str) or len(t.encode()) > 8000 for t in body['input'])):
            raise ValueError('Unapproved embedding configuration')
        bound = math.ceil((size + 512) * .02)
        endpoint = 'embeddings'
    else:
        raise ValueError('Unapproved operation')
    return endpoint, bound


def reserve(db, key, bound):
    db.execute('BEGIN IMMEDIATE')
    try:
        if db.execute('SELECT 1 FROM request WHERE id=?', (key,)).fetchone():
            raise ValueError('Retry requires review: reservation already exists')
        evaluation_used = db.execute('SELECT coalesce(sum(reserved),0) FROM request WHERE id LIKE ?', (PREFIX+'%',)).fetchone()[0]
        total = db.execute('SELECT coalesce(sum(reserved),0) FROM request').fetchone()[0]
        category = db.execute("SELECT coalesce(sum(reserved),0) FROM request WHERE category='ask'").fetchone()[0]
        cap = db.execute('SELECT cap FROM budget WHERE id=1').fetchone()[0]
        category_cap = db.execute("SELECT cap FROM policy WHERE category='ask'").fetchone()[0]
        if evaluation_used + bound > ALLOWANCE or total + bound > cap or category + bound > category_cap:
            raise ValueError('Evaluation/global/category cap reached')
        credential = db.execute('SELECT id FROM credential ORDER BY rowid DESC LIMIT 1').fetchone()[0]
        db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)', (key, credential, 'ask', time.time(), bound, 'active'))
        db.commit()
    except BaseException:
        db.rollback()
        raise


def run(request, directory):
    endpoint, bound = validate(request)
    digest = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    key = PREFIX + digest
    output = directory / 'gbrain-comparison' / (digest + '.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(directory / 'usage.sqlite', isolation_level=None, timeout=5)
    if output.exists():
        saved = json.loads(output.read_text())
        if saved['request'] != request:
            raise ValueError('Cache mismatch')
        db.close()
        return saved
    reserve(db, key, bound)
    started = time.monotonic()
    try:
        req = urllib.request.Request('https://api.openai.com/v1/' + endpoint,
            data=json.dumps(request['body']).encode(), headers={
                'Authorization': 'Bearer ' + os.environ['OPENAI_API_KEY'], 'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=45) as response:
            result = json.load(response)
        saved = dict(request=request, response=result, reserved_microusd=bound,
                     seconds=time.monotonic()-started)
        temporary = output.with_suffix('.tmp')
        temporary.write_text(json.dumps(saved))
        temporary.replace(output)
        db.execute("UPDATE request SET state='completed' WHERE id=?", (key,))
        return saved
    except BaseException:
        db.execute("UPDATE request SET state='failed' WHERE id=?", (key,))
        raise
    finally:
        db.close()


if __name__ == '__main__':
    inputs = sys.stdin if '--stream' in sys.argv else [sys.stdin.read()]
    for line in inputs:
        try:
            print(json.dumps(run(json.loads(line), Path('/var/data/voice-companion'))), flush=True)
        except Exception as error:
            print(json.dumps({'transport_error': type(error).__name__ + ': ' + str(error)}), flush=True)
            sys.exit(1)
