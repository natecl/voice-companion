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

CASES=[case for case in json.loads((Path(__file__).parent/'fixtures/multi_source/cases.json').read_text()) if case['id'] in ('two_topics','comparison','no_match')]


async def run(directory,budget_path):
    directory.mkdir(parents=True,exist_ok=False)
    budget=ProfileBudget(budget_path,include_rework_allowance=True,include_consolidation_allowance=True,include_multisource_allowance=True)
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
            for i,text in enumerate(case['texts']):
                store.put_source(owner,source(f's{i}',text=text))
            data=dict(question=case['query'],passages=[dict(id='p1',start=0,text='That is the end of this note.')],
                      memory=True,session_id='current')
            recall=IndexedMemoryRecall(store,Recorded(),budget,multi_source=True)
            started=time.monotonic();manifest=await recall.prepare('synthetic-ranking-answer',data)
            recall_seconds=time.monotonic()-started
            assert {s['session_id'] for s in manifest['sources']}=={f's{i}' for i in case['expected']}, 'Wrong source selection'
            assert recall_seconds<3., 'Existing Ask recall deadline exceeded'
            data.update(past_sources=manifest['sources'],memory_status=manifest['status'],
                        memory_contract=manifest['contract'],memory_coverage=manifest['coverage'])
            attempt='multisource-answer-v4:'+case['id'];budget.reserve(attempt,LUNA)
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
            memory_refs={ref for ref in refs if ref.startswith('m')}
            assert memory_refs=={s['id'] for s in manifest['sources']}, 'Cite every requested source and no invented sources'
            if case['id']=='two_topics':
                assert 'peanut' in text.casefold() and any(word in text.casefold() for word in ('twelve','12'))
            if case['id']=='comparison':assert 'violin' in text.casefold() and 'soccer' in text.casefold()
            if case['id']=='no_match':assert not any(word in text.casefold() for word in ('lena','marco','biscuit'))
        print(json.dumps(dict(cases=[o['case'] for o in outputs],budget=budget.report())))
    finally:
        (directory/'ranking-calls.json').write_text(json.dumps(calls,indent=2))
        print(json.dumps(dict(budget=budget.report())),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--budget',type=Path,required=True)
    a=p.parse_args();asyncio.run(run(a.directory,a.budget))
