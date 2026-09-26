"""One frozen, batched Jev role comparison. No retries; preserve response before assertions."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from memory_models import MemoryModels, JEV, parse_judgments
from memory_ranking import question
from profile_budget import ProfileBudget


async def run(output, budget_path):
    if output.exists(): raise ValueError('Use a new evidence output; do not overwrite prior runs')
    root=Path(__file__).parent/'fixtures'
    positives=json.loads((root/'memory_semantic/cases.json').read_text())
    cases=json.loads((root/'memory_reranking/cases.json').read_text())
    texts=[case['text'] for case in positives]+cases['distractors']
    queries=[case['query'] for case in positives]+cases['irrelevant_queries']
    req=dict(model=JEV,state={},questions={f'q{i}':question(q,texts) for i,q in enumerate(queries)})
    assert len(json.dumps(req).encode())<28000
    budget=ProfileBudget(budget_path,include_rework_allowance=True,include_consolidation_allowance=True)
    attempt='memory-ranking-role-v1'
    budget.reserve(attempt,JEV)
    try:
        models=MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY'])
        result=await models.judge(req)
        budget.finish(attempt,result['usage'])
    except BaseException:
        budget.finish(attempt);raise
    output.write_text(json.dumps(dict(request=req,response=result),indent=2))
    answers=parse_judgments(result['data'],req)
    checks={key:answers[key]['choice']==(f'p{i}' if i<len(positives) else 'none')
            for i,key in enumerate(req['questions'])}
    print(json.dumps(dict(checks=checks,budget=budget.report())))
    assert all(checks.values()), 'Jev role gate failed; no automatic retry'

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('output',type=Path);p.add_argument('--budget',type=Path,required=True)
    a=p.parse_args();asyncio.run(run(a.output,a.budget))
