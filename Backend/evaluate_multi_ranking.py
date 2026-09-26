"""One live frozen multi-source role batch. Preserve failures; no automatic retry."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from memory_models import MemoryModels,JEV
from memory_multi_ranking import request,order
from profile_budget import ProfileBudget


async def run(output,budget_path,heldout=False):
    if output.exists():raise ValueError('Do not overwrite evidence')
    cases=json.loads((Path(__file__).parent/'fixtures/multi_source'/('heldout.json' if heldout else 'cases.json')).read_text())
    requests={case['id']:request(case['query'],case['texts'],case['id']) for case in cases}
    batch=dict(model=JEV,state={'contexts':{key:value for req in requests.values() for key,value in req['state']['contexts'].items()}},questions={case+'_'+key:q for case,req in requests.items() for key,q in req['questions'].items()})
    assert len(json.dumps(batch).encode())<28000
    budget=ProfileBudget(budget_path,include_rework_allowance=True,include_consolidation_allowance=True,include_multisource_allowance=True)
    attempt='multisource-role-v4'+('-heldout' if heldout else '');budget.reserve(attempt,JEV)
    try:
        response=await MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY']).judge(batch)
        budget.finish(attempt,response['usage'])
    except BaseException:
        budget.finish(attempt);raise
    output.write_text(json.dumps(dict(request=batch,response=response),indent=2))
    checks={};selected={}
    for case in cases:
        req=requests[case['id']]
        data=dict(model=JEV,answers={key:response['data']['answers'][case['id']+'_'+key] for key in req['questions']})
        ranking=order(data,req)['order'];selected[case['id']]=sorted(int(key[1:]) for key in ranking[:ranking.index('none')])
        checks[case['id']]=selected[case['id']]==case['expected']
    print(json.dumps(dict(checks=checks,selected=selected,budget=budget.report())),flush=True)
    assert all(checks.values()),'Role gate failed; preserve result and stop live sequence'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--budget',type=Path,required=True)
    p.add_argument('--heldout',action='store_true');a=p.parse_args();asyncio.run(run(a.output,a.budget,a.heldout))
