"""Explicit bounded synthetic QA. Canonical existing ledger; no automatic retry."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from memory_chunks import boundary_request, boundary_choices, plan
from memory_models import MemoryModels, extraction_request
from memory_store import MemoryStore
from memory_writer import MemoryWriter
from profile_budget import ProfileBudget
from admission import Rejected


async def run(directory,budget_path):
    os.umask(0o077);directory.mkdir(parents=True,exist_ok=False)
    canonical=ProfileBudget(budget_path)
    class BoundedBudget:
        count=0
        def reserve(self,key,model):
            if self.count>=10:raise Rejected('qa_call_cap')
            canonical.reserve(key,model);self.count+=1
        def finish(self,*args):canonical.finish(*args)
    budget=BoundedBudget()
    models=MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY'])
    store=MemoryStore(directory/'synthetic.sqlite')
    owner=store.owner_for('synthetic-chunk-qa')
    cases=json.loads((Path(__file__).parent/'fixtures/memory_boundaries/cases.json').read_text())
    windows={c['id']:{'left':c['left'],'right':c['right']} for c in cases}
    request=boundary_request(windows)
    from memory_models import metered
    source=dict(session_id='boundary-qa',revision=1,captured_at=1790337600.,timezone='UTC',completed=True,
                passages=[dict(id='p1',start=0.,duration=1.,text='Synthetic boundary QA.',speakers=[])])
    store.put_source(owner,source);job=store.claim_job(owner)
    result=await metered(store,budget,job,'boundary:v1',request,models.judge)
    (directory/'boundary-response.json').write_text(json.dumps({'request':request,'response':result},indent=2))
    judgments=boundary_choices(result['data'],request)
    checks={c['id']: (judgments[c['id']]['choice']=='split' and judgments[c['id']]['probabilities']['split']>=.80)==c['split'] for c in cases}
    print(json.dumps({'stage':'boundaries','checks':checks,'calls':budget.count}),flush=True)
    if not all(checks.values()):raise RuntimeError('Boundary acceptance failed; no retry')
    store.commit_claims(job,[])
    # One long utterance exercises the bounded fallback; useful whole-turn
    # semantic decisions were checked above and through local writer execution.
    text='Project Maple meets on Tuesday. '
    tail=' Project Cedar meets on Friday.'
    while True:
        source=dict(source,session_id='long-capture',passages=[dict(id='p1',start=0.,duration=60.,text=text+tail,speakers=[])])
        try:extraction_request(source)
        except Rejected:break
        text+='There was a quiet pause while everyone considered the discussion. '*5
    chunks=plan(source)
    if 1+3*len(chunks)>10:raise RuntimeError('Fixture exceeds predeclared call cap; no pipeline calls')
    store.put_source(owner,source)
    writer=MemoryWriter(store,models,budget,chunking=True,semantic_boundaries=True)
    learned=await writer.process_next(owner)
    claims=store.search(owner,limit=50)
    checks={name:any(name.lower() in c['text'].lower() and day.lower() in c['text'].lower() for c in claims)
            for name,day in [('Maple','Tuesday'),('Cedar','Friday')]}
    (directory/'pipeline-result.json').write_text(json.dumps({'source':source,'learned':learned,'claims':claims,'checks':checks},indent=2))
    print(json.dumps({'stage':'chunk_pipeline','checks':checks,'chunks':len(chunks),'calls':budget.count,'budget':canonical.report()}),flush=True)
    if not all(checks.values()):raise RuntimeError('Chunk evidence acceptance failed; no retry')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory',type=Path);parser.add_argument('--budget',type=Path,required=True)
    args=parser.parse_args();asyncio.run(run(args.directory,args.budget))
