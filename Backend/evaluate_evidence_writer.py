"""Twelve-call cap for real extraction -> independent judgment -> atomic storage QA."""
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


async def run(directory,budget_path,cases_path=None,replay_path=None):
    os.umask(0o077);directory.mkdir(parents=True,exist_ok=False)
    canonical=ProfileBudget(budget_path,include_rework_allowance=True)
    replay={} if replay_path is None else {fingerprint(r['request']):r for r in json.loads(replay_path.read_text())}
    reused=set()
    class Budget:
        count=0
        def reserve(self,key,model):
            if key.rsplit(':',1)[-1] in replay:
                reused.add(key);return
            if self.count>=12:raise Rejected('qa_call_cap')
            canonical.reserve(key,model);self.count+=1
        def finish(self,*args):
            if args[0] not in reused:canonical.finish(*args)
    budget=Budget();models=MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY'])
    original_extract,original_judge=models.extract,models.judge
    calls=[]
    async def record(role,request,call):
        cached=replay.get(fingerprint(request))
        if cached and cached['role']!=role:raise ValueError('Replay role mismatch')
        response=cached['response'] if cached else await call(request)
        calls.append(dict(role=role,request=request,response=response,replayed=bool(cached)))
        (directory/'provider-calls.json').write_text(json.dumps(calls,indent=2))
        return response
    async def extract(request):return await record('extract',request,original_extract)
    async def judge(request):return await record('judge',request,original_judge)
    models.extract,models.judge=extract,judge
    store=MemoryStore(directory/'synthetic.sqlite',personal_learning=True);owner=store.owner_for('writer-qa')
    writer=EvidenceWriter(store,models,budget)
    cases=[('first','My daughter Maya enjoys swimming.'),
           ('correction','My daughter Maya now enjoys tennis instead of swimming.'),
           ('distinct','My other daughter Maya enjoys painting.')]
    if cases_path is not None:cases=json.loads(cases_path.read_text())
    if [c[0] for c in cases]!=['first','correction','distinct']:raise ValueError('Expected frozen three-step acceptance set')
    for index,(name,text) in enumerate(cases):
        source=dict(session_id=name,revision=1,captured_at=1790337600.+index,timezone='UTC',completed=True,origin='personal_text',
                    passages=[dict(id='p1',start=0.,duration=5.,text=text,speakers=[])])
        store.put_source(owner,source);result=await writer.process_next(owner)
        rows=store.search(owner,historical=True);unresolved=store.search(owner,unresolved_only=True)
        by_source={r['sources'][0]['session']:r for r in rows}
        checks={'no_unresolved':not unresolved,'expected_count':len(rows)==index+1}
        if index==0:checks['first_active']=by_source.get('first',{}).get('state')=='active'
        if index>=1:
            checks['old_historical']=by_source.get('first',{}).get('state')=='superseded'
            checks['correction_active']=by_source.get('correction',{}).get('state')=='active'
            checks['same_identity']=by_source.get('first',{}).get('entity_id')==by_source.get('correction',{}).get('entity_id') and by_source.get('first',{}).get('entity_id') is not None
        if index==2:
            checks['other_active']=by_source.get('distinct',{}).get('state')=='active'
            checks['different_identity']=by_source.get('distinct',{}).get('entity_id')!=by_source.get('first',{}).get('entity_id')
        (directory/(name+'.json')).write_text(json.dumps(dict(source=source,result=result,claims=rows,unresolved=unresolved,checks=checks),indent=2))
        print(json.dumps(dict(case=name,checks=checks,calls=budget.count,budget=canonical.report())),flush=True)
        if not all(checks.values()):raise RuntimeError('Writer acceptance failed; no retry')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    parser.add_argument('--budget',type=Path,required=True);parser.add_argument('--cases',type=Path);parser.add_argument('--replay',type=Path);args=parser.parse_args()
    asyncio.run(run(args.directory,args.budget,args.cases,args.replay))
