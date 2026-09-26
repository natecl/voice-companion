"""Three frozen actual recall-to-Luna cases. At most six calls, no retries."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import time
from ask import Luna,references,instructions
from indexed_recall import IndexedMemoryRecall
from memory_models import MemoryModels,LUNA
from memory_store import MemoryStore
from profile_budget import ProfileBudget
from test_memory import source,candidate

CASES=[
 dict(id='correction',old='Maya enjoys swimming.',new='Maya now enjoys tennis instead of swimming.',
      relation='supersedes',query='What sport does Maya enjoy now?'),
 dict(id='unknown',old='I am an endurance runner.',query='Am I an endurance runner?'),
 dict(id='conflict',old="Maya's favorite sport is swimming.",
      new="Another speaker says Maya's favorite sport is tennis; it is unclear whether this is the same Maya.",
      relation='unresolved',query="What is Maya's favorite sport now?")]


async def run(directory,budget_path):
    directory.mkdir(parents=True,exist_ok=False)
    budget=ProfileBudget(budget_path,include_rework_allowance=True,include_consolidation_allowance=True)
    models=MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY'])
    calls=[]
    class Recorded:
        async def judge(self,req):
            result=await models.judge(req);calls.append(dict(request=req,response=result));return result
    outputs=[]
    try:
        for case in CASES:
            store=MemoryStore(directory/(case['id']+'.sqlite'),clock=lambda:1790438400.)
            owner=store.owner_for('synthetic-ranking-answer')
            old=source('old',text=case['old']);old['captured_at']=1790438300.
            store.put_source(owner,old);store.commit_claims(store.claim_job(owner),[candidate(case['old'])])
            old_id=store.search(owner)[0]['id']
            if 'new' in case:
                new=source('new',text=case['new']);new['captured_at']=1790438390.
                store.put_source(owner,new)
                change=dict(relation=case['relation'])
                if case['relation']=='supersedes':change['target']=old_id
                else:change['proposed_targets']=[old_id]
                store.commit_claims(store.claim_job(owner),[candidate(case['new'],**change)])
            data=dict(question=case['query'],passages=[dict(id='p1',start=0,text='That is the end of this note.')],
                      memory=True,session_id='current')
            recall=IndexedMemoryRecall(store,Recorded(),budget)
            started=time.monotonic();manifest=await recall.prepare('synthetic-ranking-answer',data)
            recall_seconds=time.monotonic()-started
            assert manifest['sources'], 'Expected supplied evidence for this frozen case'
            assert recall_seconds<3., 'Existing Ask recall deadline exceeded'
            data.update(past_sources=manifest['sources'],memory_status=manifest['status'],
                        memory_contract=manifest['contract'],memory_coverage=manifest['coverage'])
            attempt='indexed-answer-v1:'+case['id'];budget.reserve(attempt,LUNA)
            text='';usage=None
            try:
                async for event in Luna(os.environ['OPENAI_API_KEY']).stream(data):
                    if event['type']=='delta':text+=event['text']
                    elif event['type']=='completed':usage=event
                assert usage is not None and text.strip()
                budget.finish(attempt,usage)
            except BaseException:
                budget.finish(attempt);raise
            await recall.validate(manifest)
            refs=references(text,data['passages']+data['past_sources'])
            output=dict(case=case['id'],data=data,instructions=instructions(data),answer=text,
                        references=refs,recall_seconds=recall_seconds,usage=usage)
            outputs.append(output)
            (directory/'answers.json').write_text(json.dumps(outputs,indent=2))
            assert any(ref.startswith('m') for ref in refs), 'Memory answer must cite evidence'
            if case['id']=='correction':assert 'tennis' in text.casefold()
            if case['id']=='unknown':assert any(word in text.casefold() for word in ('unknown','cannot','can’t',"can't",'unclear','not identify',"don't know",'doesn’t identify','does not identify'))
            if case['id']=='conflict':assert any(word in text.casefold() for word in ('unclear','conflict','uncertain','not clear','can’t tell',"can't tell"))
        print(json.dumps(dict(cases=[o['case'] for o in outputs],budget=budget.report())))
    finally:
        (directory/'ranking-calls.json').write_text(json.dumps(calls,indent=2))
        print(json.dumps(dict(budget=budget.report())),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--budget',type=Path,required=True)
    a=p.parse_args();asyncio.run(run(a.directory,a.budget))
