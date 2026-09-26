"""Four explicitly bounded extraction calls; no writes to production memory."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from admission import Rejected
from memory_evidence import extraction_request, parse
from memory_models import MemoryModels, metered
from memory_store import MemoryStore
from profile_budget import ProfileBudget


def checks(case,candidates):
    expected=case['expected']
    def matches(c):
        values=dict(scope=c['scope'],name=c['mention']['name'],relationship=c['mention']['relationship'],
                    change=c['change']['kind'],time=c['time']['status'])
        return all((v.casefold() in c['text'].casefold() if k=='contains' else
                    v in c['mention']['qualifiers'] if k=='qualifier' else
                    c['change']['kind'] in v if k=='change_in' else values[k]==v) for k,v in expected.items())
    return bool(candidates) and all(matches(c) for c in candidates)


async def run(directory,budget_path,selected=None):
    os.umask(0o077);directory.mkdir(parents=True,exist_ok=False)
    canonical=ProfileBudget(budget_path)
    class Budget:
        count=0
        def reserve(self,key,model):
            if self.count>=4:raise Rejected('qa_call_cap')
            canonical.reserve(key,model);self.count+=1
        def finish(self,*args):canonical.finish(*args)
    budget=Budget();models=MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY'])
    store=MemoryStore(directory/'synthetic.sqlite',personal_learning=True);owner=store.owner_for('evidence-contract-qa')
    cases=json.loads((Path(__file__).parent/'fixtures/memory_evidence/cases.json').read_text())
    if selected is not None:
        if not set(selected)<=set(c['id'] for c in cases):raise ValueError('Unknown case')
        cases=[c for c in cases if c['id'] in selected]
    for case in cases:
        source=dict(session_id=case['id'],revision=1,captured_at=1790337600.,timezone='UTC',completed=True,
                    passages=[dict(id='p1',start=0.,duration=5.,text=case['text'],speakers=[0])])
        if case['origin']=='personal_text':
            source['origin']='personal_text';source['passages'][0]['speakers']=[]
        store.put_source(owner,source);job=store.claim_job(owner)
        request=extraction_request(source)
        response=await metered(store,budget,job,'evidence:v2',request,models.extract)
        # Save raw output before validation to preserve any failure for free replay.
        (directory/(case['id']+'.json')).write_text(json.dumps(dict(source=source,request=request,response=response),indent=2))
        candidates=parse(response['data'],source);passed=checks(case,candidates)
        print(json.dumps(dict(case=case['id'],passed=passed,calls=budget.count,budget=canonical.report())),flush=True)
        if not passed:raise RuntimeError('Extraction acceptance failed; no retry')
        store.commit_claims(job,[])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    parser.add_argument('--budget',type=Path,required=True);parser.add_argument('--cases',nargs='+');args=parser.parse_args()
    asyncio.run(run(args.directory,args.budget,args.cases))
