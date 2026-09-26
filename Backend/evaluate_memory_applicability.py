"""One approved, bounded batch for current-state applicability; no automatic retry."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from memory_judgments import pair_questions,decisions
from memory_models import MemoryModels,metered
from memory_store import MemoryStore
from profile_budget import ProfileBudget

async def run(directory,budget_path):
    os.umask(0o077);directory.mkdir(parents=True,exist_ok=False)
    cases=json.loads((Path(__file__).parent/'fixtures/memory_judgments/applicability-cases.json').read_text())
    pairs={c['id']:c['pair'] for c in cases}
    req=pair_questions(pairs,role='applicability')
    store=MemoryStore(directory/'synthetic.sqlite');owner=store.owner_for('applicability-qa')
    source=dict(session_id='applicability',revision=1,captured_at=1790337600.,timezone='UTC',completed=True,
        passages=[dict(id='p1',start=0.,duration=1.,speakers=[],text='Synthetic applicability QA.')])
    store.put_source(owner,source);job=store.claim_job(owner)
    budget=ProfileBudget(budget_path,include_rework_allowance=True)
    models=MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY'])
    result=await metered(store,budget,job,'applicability:v6',req,models.judge)
    parsed=decisions(result['data'],req,'applicability')
    checks={c['id']:(parsed[c['id']]['accepted'] and parsed[c['id']]['label']=='current_change')==c['current'] for c in cases}
    (directory/'result.json').write_text(json.dumps(dict(cases=cases,request=req,response=result,decisions=parsed,checks=checks),indent=2))
    print(json.dumps(dict(checks=checks,budget=budget.report())),flush=True)
    if not all(checks.values()):raise RuntimeError('Applicability gate failed; no retry')
    store.commit_claims(job,[])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path)
    parser.add_argument('--budget',type=Path,required=True);args=parser.parse_args()
    asyncio.run(run(args.directory,args.budget))
