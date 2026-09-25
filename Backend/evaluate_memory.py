"""Bounded synthetic learning evaluation; requires a pre-reserved global allocation."""
import argparse
import asyncio
from datetime import datetime
import json
import os
import sqlite3
from pathlib import Path
from memory_budget import MemoryBudget
from memory_models import MemoryModels, fingerprint
from memory_store import MemoryStore
from memory_writer import MemoryWriter

ROOT = Path(__file__).resolve().parents[1]


async def main(suite, directory, run_name=None, reuse_extraction=None):
    os.umask(0o077)
    directory.mkdir(parents=True,exist_ok=True)
    # Load only known provider keys; never print their values or upload unrelated .env fields.
    values = {}
    for line in (ROOT/'.env').read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key,value=line.split('=',1)
            if key in ('OPENAI_API_KEY','TYPESAFE_API_KEY'):values[key]=value.strip().strip('\"\'')
    if not all(values.get(k) for k in ('OPENAI_API_KEY','TYPESAFE_API_KEY')):raise ValueError('Missing provider credentials')
    receipt=json.loads((directory/'allocation.json').read_text())
    budget=MemoryBudget(directory/'budget.sqlite',receipt)
    clock=[datetime.fromisoformat('2026-09-25T12:00:00+00:00').timestamp()]
    run_name = run_name or suite
    store=MemoryStore(directory/(run_name+'.sqlite'),clock=lambda:clock[0])
    owner=store.owner_for('synthetic-'+suite)
    models=MemoryModels(values['OPENAI_API_KEY'],values['TYPESAFE_API_KEY'])
    if reuse_extraction:
        with sqlite3.connect(reuse_extraction) as db:
            saved = {(stage,key):json.loads(response) for stage,key,response in db.execute("SELECT stage,request_hash,response FROM job_result")}
        def replay(stage, live):
            async def call(request):
                cached = saved.get((stage,fingerprint(request)))
                if cached is not None: return cached
                return await live(request)
            return call
        models.extract = replay('extract', models.extract)
        models.judge = replay('judge', models.judge)
        # Exact-request replay bypasses both the provider and a new paid reservation.
        original_reserve = budget.reserve
        def reserve(key, model):
            _,stage,digest = key.split(':')
            if (stage,digest) in saved: return
            original_reserve(key, model)
        budget.reserve = reserve
    writer=MemoryWriter(store,models,budget)
    cases=[c for c in json.loads((ROOT/'Fixtures/memory-learning-cases.json').read_text()) if c['suite']==suite]
    # Refuse accidental replay. Cached DB results remain available for offline analysis.
    with (directory/(run_name+'-results.jsonl')).open('x') as output:
        for i,c in enumerate(cases):
            clock[0]+=60
            source=dict(session_id=c['id'],revision=1,captured_at=clock[0],timezone='UTC',completed=True,
                passages=[dict(id='p1',start=0.,duration=3.,text=c['text'],speakers=[])])
            store.put_source(owner,source)
            result=await writer.process_next(owner)
            claims=store.search(owner,historical=True,limit=50)
            related=[m for m in claims if any(s['session']==c['id'] for s in m['sources'])]
            checks={
                'count':c['accepted_min']<=result['accepted']<=c.get('accepted_max',8),
                'content':not c.get('expect') or any(c['expect'].casefold() in m['text'].casefold() for m in related),
                'unknown':not c.get('unknown') or all(m['subject'] is None for m in related),
                'supersedes':not c.get('supersedes') or any(m['replaces'] is not None for m in related),
                'duplicate':not c.get('duplicate') or any(len(m['sources'])>1 for m in related),
                'expiry':not c.get('expiry') or any(m['valid_until']==datetime.fromisoformat(c['expiry']).timestamp() for m in related),
            }
            record=dict(id=c['id'],result=result,checks=checks,claims=related)
            output.write(json.dumps(record)+'\n');output.flush()
            print(json.dumps({'id':c['id'],'checks':checks,'accepted':result['accepted']}),flush=True)
            if not all(checks.values()):raise RuntimeError('Acceptance failed; stopped without retries')
        clock[0]=datetime.fromisoformat('2026-10-01T12:00:00+00:00').timestamp()
        store.maintain()
        if any(c.get('expiry') for c in cases):
            assert not any(m['valid_until'] is not None and m['valid_until']<=clock[0] for m in store.search(owner))
            assert any(m['state']=='expired' for m in store.search(owner,historical=True,limit=50))
        print(json.dumps({'suite':suite,'lifecycle':'passed','budget':budget.report()}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('suite',choices=['development','heldout','heldout-v3'])
    parser.add_argument('--directory',type=Path,default=ROOT/'work/memory-learning-qa')
    parser.add_argument('--run-name', help='Explicit new development attempt; preserves earlier results and shared budget')
    parser.add_argument('--reuse-extraction',type=Path)
    args=parser.parse_args()
    asyncio.run(main(args.suite,args.directory,args.run_name,args.reuse_extraction))
