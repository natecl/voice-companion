"""Bounded synthetic long-recording integration. No automatic provider retries."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from admission import Rejected
from memory_evidence_writer import EvidenceWriter
from memory_models import MemoryModels,fingerprint
from memory_store import MemoryStore
from profile_budget import ProfileBudget

async def run(directory,budget_path,source_path,replay_path=None):
    os.umask(0o077);directory.mkdir(parents=True,exist_ok=False)
    canonical=ProfileBudget(budget_path,include_rework_allowance=True)
    print(json.dumps(dict(initial_budget=canonical.report())),flush=True)
    replay={} if replay_path is None else {fingerprint(c['request']):c for c in json.loads(replay_path.read_text())}
    reused=set()
    class Budget:
        count=0
        def reserve(self,*args):
            if args[0].rsplit(':',1)[-1] in replay:reused.add(args[0]);return
            if self.count>=16:raise Rejected('qa_call_cap')
            canonical.reserve(*args);self.count+=1
        def finish(self,*args):
            if args[0] not in reused:canonical.finish(*args)
    budget=Budget();models=MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY']);calls=[]
    async def record(role,request,call):
        cached=replay.get(fingerprint(request))
        if cached and cached['role']!=role:raise ValueError('Replay role mismatch')
        response=cached['response'] if cached else await call(request)
        calls.append(dict(role=role,request=request,response=response,replayed=bool(cached)))
        (directory/'provider-calls.json').write_text(json.dumps(calls,indent=2))
        return response
    extract,judge=models.extract,models.judge
    async def ex(request):return await record('extract',request,extract)
    async def ju(request):return await record('judge',request,judge)
    models.extract,models.judge=ex,ju
    store=MemoryStore(directory/'synthetic.sqlite');owner=store.owner_for('chunk-qa')
    writer=EvidenceWriter(store,models,budget,chunking=True,semantic_boundaries=True)
    source=json.loads(source_path.read_text());store.put_source(owner,source)
    result=await writer.process_next(owner)
    rows=store.search(owner,historical=True);unresolved=store.search(owner,unresolved_only=True)
    with store.connect() as db:
        plans=[json.loads(r[0]) for r in db.execute('SELECT plan FROM memory_chunk ORDER BY ordinal')]
    old=[r for r in rows if r['state']=='superseded' and 'swimming' in r['text'].lower()]
    new=[r for r in rows if r['state']=='active' and 'tennis' in r['text'].lower()]
    checks=dict(multiple_chunks=len(plans)>1,semantic_plan=all(p['strategy']=='jev_boundary_overlap' for p in plans),
        correction=len(old)==1 and len(new)==1 and new[0]['replaces']==old[0]['id'],
        same_person=len(old)==1 and len(new)==1 and old[0]['entity_id']==new[0]['entity_id'] and old[0]['entity_id'] is not None,
        no_unresolved=not unresolved,no_owner_inference=all(r['subject']!='user' and not r['profile_link'] for r in rows),
        original_refs=all(ref['passage'] in {p['id'] for p in source['passages']} for r in rows for ref in r['sources']),
        source_unchanged=store.source(owner,source['session_id'])==source)
    (directory/'result.json').write_text(json.dumps(dict(source=source,result=result,claims=rows,unresolved=unresolved,plans=plans,checks=checks,budget=canonical.report()),indent=2))
    print(json.dumps(dict(checks=checks,budget=canonical.report(),new_calls=budget.count)),flush=True)
    if not all(checks.values()):raise RuntimeError('Chunk writer acceptance failed; no retry')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    parser.add_argument('--budget',type=Path,required=True);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--replay',type=Path);args=parser.parse_args()
    asyncio.run(run(args.directory,args.budget,args.source,args.replay))
