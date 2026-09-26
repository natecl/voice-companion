"""Four-call independent Jev QA; separate synthetic database, existing budget."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from admission import Rejected
from memory_judgments import decisions
from memory_models import MemoryModels,metered
from memory_store import MemoryStore
from profile_budget import ProfileBudget


def check(case,result):
    checks={}
    for key,wanted in case['expected'].items():
        answer=result[key]
        if wanted=='reject':passed=not answer['accepted']
        elif wanted.startswith('no_'):passed=not (answer['accepted'] and answer['label']==wanted[3:])
        else:passed=answer['accepted'] and answer['label']==wanted
        checks[key]=passed
    return checks


async def run(directory,budget_path,case_file=None):
    os.umask(0o077);directory.mkdir(parents=True,exist_ok=False)
    canonical=ProfileBudget(budget_path,include_rework_allowance=True)
    class Budget:
        count=0
        def reserve(self,key,model):
            if self.count>=4:raise Rejected('qa_call_cap')
            canonical.reserve(key,model);self.count+=1
        def finish(self,*args):canonical.finish(*args)
    budget=Budget();models=MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY'])
    store=MemoryStore(directory/'synthetic.sqlite');owner=store.owner_for('judgment-qa')
    cases=json.loads((case_file or Path(__file__).parent/'fixtures/memory_judgments/cases.json').read_text())
    for case in cases:
        source=dict(session_id=case['id'],revision=1,captured_at=1790337600.,timezone='UTC',completed=True,
                    passages=[dict(id='p1',start=0.,duration=1.,text='Synthetic judgment QA',speakers=[])])
        store.put_source(owner,source);job=store.claim_job(owner)
        response=await metered(store,budget,job,'judgment:v1',case['request'],models.judge)
        (directory/(case['id']+'.json')).write_text(json.dumps(dict(case=case,response=response),indent=2))
        checks=check(case,decisions(response['data'],case['request'],case['role']))
        print(json.dumps(dict(case=case['id'],checks=checks,calls=budget.count,budget=canonical.report())),flush=True)
        if not all(checks.values()):raise RuntimeError('Judgment acceptance failed; no retry')
        store.commit_claims(job,[])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    parser.add_argument('--budget',type=Path,required=True);parser.add_argument('--case-file',type=Path);args=parser.parse_args()
    asyncio.run(run(args.directory,args.budget,args.case_file))
