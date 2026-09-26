"""Four real Ask integrations against copied synthetic profile evidence; no microphone."""
import argparse
import asyncio
from contextlib import closing
import json
import os
import re
from pathlib import Path
import sqlite3
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from admission import Admission
from ask import AskService, Luna
from memory_models import MemoryModels
from memory_store import MemoryStore
from memory_recall import MemoryRecall, combined_shortlist
from profile_budget import ProfileBudget

CASES=[
    ('paraphrase','Suggest a relaxing creative activity for my weekend.','bird','student'),
    ('current','What sport does my daughter enjoy now?','tennis','family-update'),
    ('history','What did my daughter enjoy before the correction?','swimming','family'),
    ('irrelevant','What is two plus two?','4',None),
]

def content_matches(name, expected, text):
    if name == 'irrelevant':
        return re.search(r'\b(?:4|four)\b', text.casefold()) is not None
    return expected in text.casefold()


async def main(seed,directory,budget_path,case=None):
    os.umask(0o077)
    directory.mkdir(parents=True,exist_ok=False)
    with closing(sqlite3.connect(seed)) as old, closing(sqlite3.connect(directory/'memory.sqlite')) as new: old.backup(new)
    store=MemoryStore(directory/'memory.sqlite',clock=lambda:1790340000.,personal_recall=True)
    with store.connect() as db: owner=db.execute("SELECT owner FROM credential_owner WHERE credential='synthetic-profile'").fetchone()[0]
    admission=Admission(directory/'usage.sqlite',total_microusd=12000,limits={'ask':(12000,3000,4)})
    credential,token=admission.enroll()
    store.owner_for(credential,existing_owner=owner)
    for i in range(20):
        store.put_source(owner,dict(session_id=f'noise-{i}',revision=1,captured_at=1790339900.,timezone='UTC',completed=True,
                                    passages=[dict(id='p1',start=0.,duration=1.,text='Work agenda and schedule updates.',speakers=[])]))
    budget=ProfileBudget(budget_path)
    models=MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY'])
    service=AskService(admission,Luna(os.environ['OPENAI_API_KEY']),MemoryRecall(store,models,budget),qa_budget=budget)
    try:
        async with serve(service.handle,'127.0.0.1',0) as server:
            url=f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}'
            with (directory/'answers.jsonl').open('x') as output:
                for name,question,expected,expected_source in CASES:
                    if case and name != case: continue
                    data={'question':question,'passages':[{'id':'p1','start':0.,'text':"Let's take a short break."}], 'memory':True,'session_id':'current-session'}
                    events=[]
                    async with connect(url,additional_headers={'Authorization':'Bearer '+token}) as socket:
                        await socket.send(json.dumps(data))
                        while True:
                            event=json.loads(await socket.recv());events.append(event)
                            if event['type'] in ('done','error'):break
                    text=''.join(e['text'] for e in events if e['type']=='delta')
                    context=next((e for e in events if e['type']=='context'),{'sources':[]})
                    references=events[-1].get('references',[])
                    used=[s for s in context['sources'] if s['id'] in references]
                    checks={'completed':events[-1]['type']=='done','content':content_matches(name,expected,text),
                            'source':expected_source is None or any(s['session_id']==expected_source for s in used),
                            'no_irrelevant_profile':name!='irrelevant' or not any(s.get('origin')=='personal_text' for s in context['sources'])}
                    output.write(json.dumps({'case':name,'question':question,'events':events,'checks':checks})+'\n');output.flush()
                    print(json.dumps({'case':name,'text':text,'checks':checks,'budget':budget.report()}),flush=True)
                    if not all(checks.values()):raise RuntimeError('Profile Ask failed; stopped without retry')
        store.delete_source(owner,'family-update')
        assert not any(c['session_id']=='family-update' for c in combined_shortlist(store.recall_snapshot(owner),data))
        print(json.dumps({'deletion':'passed','budget':budget.report()}))
    finally: admission.close()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('seed',type=Path);p.add_argument('directory',type=Path);p.add_argument('--budget',type=Path,required=True)
    p.add_argument('--case',choices=[c[0] for c in CASES],help='Explicitly run only one reviewed case; never retries automatically')
    a=p.parse_args();asyncio.run(main(a.seed,a.directory,a.budget,a.case))
