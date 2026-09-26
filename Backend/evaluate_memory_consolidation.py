"""One bounded live consolidation sequence; canonical ledger, no retries."""
import copy
import argparse
import asyncio
import json
import os
from pathlib import Path
from memory_models import MemoryModels, fingerprint
from memory_store import MemoryStore
from memory_evidence_writer import EvidenceWriter
from profile_budget import ProfileBudget
from evaluate_memory_expiry import source

TEXTS=[('first','My daughter Maya enjoys swimming.'),
       ('repeat','To repeat what I told you before, my daughter Maya enjoys swimming.'),
       ('distinct','My other daughter Maya enjoys painting.'),
       ('correction','My daughter Maya now enjoys tennis instead of swimming.')]


async def run(directory,budget_path,replay=None):
    directory.mkdir(parents=True,exist_ok=False)
    budget=ProfileBudget(budget_path,include_rework_allowance=True,include_consolidation_allowance=True)
    models=MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY'])
    cached={fingerprint(c['request']):c for c in json.loads(replay.read_text())} if replay else {}
    calls=[];snapshots=[];checks={};sources=[]
    class ReplayStore(MemoryStore):
        def cached_result(self,job,stage,key):
            if key in cached:
                record=copy.deepcopy(cached[key]);calls.append(record)
                return record['response']
            return super().cached_result(job,stage,key)
    class Recorded:
        async def extract(self,req):
            result=await models.extract(req);calls.append(dict(role='extract',request=req,response=result));return result
        async def judge(self,req):
            result=await models.judge(req);calls.append(dict(role='judge',request=req,response=result));return result
    store=ReplayStore(directory/'evidence.sqlite',personal_learning=True,clock=lambda:1790424100.)
    owner=store.owner_for('synthetic-consolidation');writer=EvidenceWriter(store,Recorded(),budget,consolidation=True)
    try:
        for i,(name,text) in enumerate(TEXTS):
            original=source(text);original.update(session_id=name,captured_at=1790424000.+i)
            sources.append(original);store.put_source(owner,original)
            result=await writer.process_next(owner)
            rows=store.search(owner,historical=True);unresolved=store.search(owner,unresolved_only=True)
            snapshots.append(dict(name=name,result=result,rows=rows,unresolved=unresolved))
            expected=1 if i<2 else 2 if i==2 else 3
            checks[name]=len(rows)==expected and not unresolved
            if i==1:checks['two_sources']=len(rows)==1 and len(rows[0]['sources'])==2
            if i==3:checks['corrected_once']=sorted(r['state'] for r in rows)==['active','active','superseded']
            if not all(checks.values()):raise RuntimeError('Consolidation gate failed; no retry')
    finally:
        (directory/'provider-calls.json').write_text(json.dumps(calls,indent=2))
        (directory/'result.json').write_text(json.dumps(dict(sources=sources,snapshots=snapshots,checks=checks),indent=2))
        print(json.dumps(dict(checks=checks,budget=budget.report())),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--budget',type=Path,required=True);p.add_argument('--replay',type=Path);a=p.parse_args()
    asyncio.run(run(a.directory,a.budget,a.replay))
