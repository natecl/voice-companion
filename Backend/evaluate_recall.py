"""Explicit synthetic recall QA; shares the existing memory allocation, never creates a grant."""
import asyncio
from contextlib import aclosing
from datetime import datetime
import json
import os
from pathlib import Path
from ask import Luna, references
from memory_budget import MemoryBudget
from memory_models import MemoryModels
from memory_recall import MemoryRecall
from memory_store import MemoryStore
from memory_writer import MemoryWriter

ROOT = Path(__file__).resolve().parents[1]


class FixtureBudget:
    def reserve(self, *args): pass
    def finish(self, *args): pass


async def main():
    os.umask(0o077)
    directory = ROOT/'work/memory-learning-qa'
    values = {}
    for line in (ROOT/'.env').read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            key, value = line.split('=', 1)
            if key in ('OPENAI_API_KEY', 'TYPESAFE_API_KEY'):
                values[key] = value.strip().strip('\"\'')
    budget = MemoryBudget(directory/'budget.sqlite', json.loads((directory/'allocation.json').read_text()))
    now = datetime.fromisoformat('2026-09-25T12:00:00+00:00').timestamp()
    # Exclusive results file prevents accidental paid repeats.
    with (directory/'recall-results.jsonl').open('x') as output:
        store = MemoryStore(directory/'recall.sqlite', clock=lambda:now)
        owner = store.owner_for('synthetic-recall')
        cached = {c['session']:c['responses'] for c in json.loads((ROOT/'Fixtures/memory-provider-responses.json').read_text())}
        async def extract(request): return cached[json.loads(request['input'])['session_id']]['extract']
        async def verify(request):
            # Storage setup only: deterministic support double, not a provider quality claim.
            candidates=json.loads(request['input'])['candidates']
            return {'data':{str(i):'supported' for i in range(len(candidates))},'usage':{}}
        async def judge(request):
            old=cached[request['state']['source']['session_id']]['judge']
            return {**old,'data':{**old['data'],'answers':{k:v for k,v in old['data']['answers'].items() if k in request['questions']}}}
        writer = MemoryWriter(store, MemoryModels('', '', luna_call=extract, jev_call=judge, support_call=verify), FixtureBudget())
        for c in json.loads((ROOT/'Fixtures/memory-learning-cases.json').read_text()):
            if c['suite'] != 'heldout-v3': continue
            now += 60
            store.put_source(owner, dict(session_id=c['id'],revision=1,captured_at=now,timezone='UTC',completed=True,
                passages=[dict(id='p1',start=0.,duration=3.,text=c['text'],speakers=[])]))
            await writer.process_next(owner)
        models = MemoryModels(values['OPENAI_API_KEY'], values['TYPESAFE_API_KEY'])
        original_judge = models.judge
        async def capture_judgment(request):
            response = await original_judge(request)
            output.write(json.dumps({'stage':'judge','request':request,'response':response})+'\n');output.flush()
            return response
        models.judge = capture_judgment
        recall = MemoryRecall(store, models, budget)
        for case in json.loads((ROOT/'Fixtures/memory-recall-cases.json').read_text()):
            data = dict(question=case['question'],passages=[dict(id='p1',start=0.,text='We are planning the upcoming meeting.')],session_id='current')
            manifest = await recall.prepare('synthetic-recall', data)
            if not manifest['sources']: raise RuntimeError('No relevant sources; stopped before answer call')
            data.update(past_sources=manifest['sources'], memory_status=manifest['status'])
            await recall.validate(manifest)
            attempt = 'recall-qa-'+case['id']+'-answer'
            budget.reserve(attempt, 'gpt-6-luna')
            answer, usage = '', None
            try:
                async with aclosing(Luna(values['OPENAI_API_KEY']).stream(data)) as events:
                    async for event in events:
                        if event['type'] == 'delta': answer += event['text']
                        if event['type'] == 'completed': usage = {k:event[k] for k in ('input_tokens','output_tokens')}
                budget.finish(attempt, usage)
            except BaseException:
                budget.finish(attempt)
                raise
            refs = references(answer, data['passages']+manifest['sources'])
            checks = {'cited_past':any(r.startswith('m') for r in refs),
                      'required':case['required'].casefold() in answer.casefold(),
                      'forbidden':not case['forbidden'] or case['forbidden'].casefold() not in answer.casefold()}
            output.write(json.dumps({'id':case['id'],'answer':answer,'checks':checks,'sources':manifest['sources'],'usage':usage})+'\n');output.flush()
            print(json.dumps({'id':case['id'],'checks':checks}), flush=True)
            if not all(checks.values()): raise RuntimeError('Recall gate failed; no automatic retry')
        print(json.dumps({'budget':budget.report()}))


if __name__ == '__main__': asyncio.run(main())
