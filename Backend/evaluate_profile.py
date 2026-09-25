"""Synthetic profile QA; explicit run, canonical budget, stop on the first failed gate."""
import argparse
import asyncio
import json
import os
import sqlite3
from contextlib import closing
from pathlib import Path
from profile_budget import ProfileBudget
from memory_models import MemoryModels
from memory_store import MemoryStore
from memory_writer import MemoryWriter


async def main(cases_path, directory, budget_path, suite, seed=None):
    os.umask(0o077)
    directory.mkdir(parents=True,exist_ok=False)
    budget = ProfileBudget(budget_path)
    if seed:
        with closing(sqlite3.connect(seed)) as old, closing(sqlite3.connect(directory/'evidence.sqlite')) as new:
            old.backup(new)
    now = [1790338600. if seed else 1790337600.]
    store = MemoryStore(directory/'evidence.sqlite', clock=lambda:now[0], personal_learning=True)
    owner = store.owner_for('synthetic-profile')
    models = MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY'])
    writer = MemoryWriter(store,models,budget)
    cases = [c for c in json.loads(cases_path.read_text()) if c['suite']==suite]
    with (directory/'results.jsonl').open('x') as output:
        for case in cases:
            now[0] += 60
            source = dict(session_id=case['id'],revision=1,captured_at=now[0],timezone='UTC',completed=True,
                          passages=[dict(id='p1',start=0.,duration=0.,text=case['text'],speakers=[])])
            if case.get('origin') != 'recording': source['origin']='personal_text'
            store.put_source(owner,source)
            result = await writer.process_next(owner)
            claims = [c for c in store.search(owner,historical=True,limit=50) if any(s['session']==case['id'] for s in c['sources'])]
            users = [c for c in claims if c['subject']=='user']
            linked = [c for c in claims if c['profile_link']]
            checks = {
                'count':case['min']<=result['accepted']<=case.get('max',8),
                'user_content':all(any(term.casefold() in c['text'].casefold() for c in users) for term in case.get('expect_user',[])),
                'related_content':all(any(term.casefold() in c['text'].casefold() for c in linked) for term in case.get('expect_related',[])),
                'no_wrong_user':not any(term.casefold() in c['text'].casefold() for term in case.get('forbid_user',[]) for c in users),
                'tentative':all(any(term in c['text'].casefold() and c['basis']=='tentative' for c in users) for term in case.get('tentative',[])),
                'supersedes':not case.get('supersedes') or any(c['replaces'] is not None for c in users),
                'related_update':not case.get('related_update') or any(c['replaces'] is not None for c in linked),
                'new_person':not case.get('new_person') or all(c['replaces'] is None for c in linked),
                'unknown':not case.get('expect_unknown') or all(c['subject'] is None for c in claims),
                'ambiguous_separate':not case.get('no_related_merge') or not linked,
            }
            record={'id':case['id'],'result':result,'checks':checks,'claims':claims}
            output.write(json.dumps(record)+'\n');output.flush()
            print(json.dumps({'id':case['id'],'checks':checks,'accepted':result['accepted'],'budget':budget.report()}),flush=True)
            if not all(checks.values()): raise RuntimeError('Profile acceptance failed; stopped without retry')
    print(json.dumps({'suite':suite,'result':'passed','budget':budget.report()}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('cases',type=Path);parser.add_argument('directory',type=Path)
    parser.add_argument('--budget',type=Path,required=True)
    parser.add_argument('--suite',choices=['development','heldout','extension'],required=True)
    parser.add_argument('--seed',type=Path)
    a=parser.parse_args()
    asyncio.run(main(a.cases,a.directory,a.budget,a.suite,a.seed))
