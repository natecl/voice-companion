"""One metered recording-subject identity comparison; no automatic retry."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from memory_recording_identity import request,decisions
from memory_models import MemoryModels,metered
from memory_store import MemoryStore
from profile_budget import ProfileBudget

async def run(directory,budget_path):
    os.umask(0o077);directory.mkdir(parents=True,exist_ok=False)
    cases=json.loads((Path(__file__).parent/'fixtures/memory_evidence_chunks/recording-identity-cases.json').read_text())
    req=request([c['proposal'] for c in cases]);store=MemoryStore(directory/'synthetic.sqlite');owner=store.owner_for('qa')
    store.put_source(owner,dict(session_id='identity',revision=1,captured_at=100.,timezone='UTC',completed=True,passages=[]))
    job=store.claim_job(owner);budget=ProfileBudget(budget_path,include_rework_allowance=True)
    models=MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY'])
    response=await metered(store,budget,job,'recording-identity-qa',req,models.extract)
    parsed=decisions(response['data'],req)
    checks={c['id']:parsed[f'subject_{i}']['accepted']==c['accept'] for i,c in enumerate(cases)}
    (directory/'result.json').write_text(json.dumps(dict(cases=cases,request=req,response=response,checks=checks),indent=2))
    print(json.dumps(dict(checks=checks,budget=budget.report())),flush=True)
    if not all(checks.values()):raise RuntimeError('Recording identity comparison failed; no retry')
    store.commit_claims(job,[])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('directory',type=Path);p.add_argument('--budget',type=Path,required=True);a=p.parse_args()
    asyncio.run(run(a.directory,a.budget))
