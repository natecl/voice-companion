"""One bounded Luna identity comparison against frozen source-only cases."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from memory_models import MemoryModels,metered
from memory_store import MemoryStore
from profile_budget import ProfileBudget
from memory_identity_model import evidence_request,decisions

async def run(directory,budget_path,case_file=None):
    os.umask(0o077)
    directory.mkdir(parents=True,exist_ok=False)
    cases=json.loads((case_file or Path(__file__).parent/'fixtures/memory_judgments/luna-identity-cases-targeted.json').read_text())
    request=evidence_request(cases['pairs'])
    store=MemoryStore(directory/'synthetic.sqlite');owner=store.owner_for('identity-model-qa')
    store.put_source(owner,dict(session_id='identity',revision=1,captured_at=1790337600.,timezone='UTC',completed=True,passages=[]))
    job=store.claim_job(owner);budget=ProfileBudget(budget_path,include_rework_allowance=True)
    models=MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY'])
    response=await metered(store,budget,job,'identity-model:v1',request,models.extract)
    (directory/'result.json').write_text(json.dumps(dict(cases=cases,request=request,response=response),indent=2))
    parsed=decisions(response['data'],request)
    checks={k:(parsed[k]['label']!='same' if v=='no_same' else parsed[k]['label']==v) for k,v in cases['expected'].items()}
    print(json.dumps(dict(checks=checks,budget=budget.report())),flush=True)
    if not all(checks.values()):raise RuntimeError('Identity comparison failed; no retry')
    store.commit_claims(job,[])

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('directory',type=Path);parser.add_argument('--budget',type=Path,required=True);parser.add_argument('--case-file',type=Path);args=parser.parse_args()
    asyncio.run(run(args.directory,args.budget,args.case_file))
