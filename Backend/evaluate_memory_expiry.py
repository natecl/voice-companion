"""Bounded expiry-role batch then actual writer; canonical ledger, no retries."""
import argparse
import asyncio
import json
import os
from pathlib import Path
import memory_expiry
from memory_models import MemoryModels, metered
from memory_store import MemoryStore
from memory_evidence_writer import EvidenceWriter
from profile_budget import ProfileBudget


def fixture(case):
    return dict(text=case['claim'],basis='stated',time=dict(status='current',expression='through 2026-09-30'),
                evidence=[dict(passage='p1',quote=case['text'])])


def source(text):
    return dict(session_id='expiry',revision=1,origin='personal_text',captured_at=1790424000.,
        timezone='America/New_York',completed=True,
        passages=[dict(id='p1',start=0.,duration=1.,speakers=[],text=text)])


async def run(directory,budget_path):
    directory.mkdir(parents=True,exist_ok=False)
    cases=json.loads((Path(__file__).parent/'fixtures/memory_expiry/cases.json').read_text())
    requests=[memory_expiry.request(source(c['text']),fixture(c)) for c in cases]
    batch=dict(model=requests[0]['model'],state={},questions={c['id']:dict(r['questions']['expiry'],
        instructions=dict(task=r['questions']['expiry']['instructions'],evidence=r['state'])) for c,r in zip(cases,requests)})
    budget=ProfileBudget(budget_path,include_rework_allowance=True)
    print(json.dumps(dict(initial_budget=budget.report())),flush=True)
    models=MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY'])
    store=MemoryStore(directory/'evidence.sqlite',personal_learning=True,clock=lambda:1790424001.)
    owner=store.owner_for('synthetic-expiry-qa');store.put_source(owner,source('Synthetic expiry role check.'))
    job=store.claim_job(owner)
    response=await metered(store,budget,job,'expiry-role:v1',batch,models.judge)
    decisions={}
    for case,req in zip(cases,requests):
        remapped=dict(response['data'],answers={'expiry':response['data']['answers'][case['id']]})
        decisions[case['id']]=memory_expiry.decision(remapped,req)
    checks={c['id']:decisions[c['id']]['accepted']==c['accept'] for c in cases}
    (directory/'role.json').write_text(json.dumps(dict(request=batch,response=response,decisions=decisions,checks=checks),indent=2))
    if not all(checks.values()):raise RuntimeError('Expiry role gate failed; no retry')
    store.commit_claims(job,[])
    calls=[]
    class Recorded:
        async def extract(self,req):
            result=await models.extract(req);calls.append(dict(role='extract',request=req,response=result));return result
        async def judge(self,req):
            result=await models.judge(req);calls.append(dict(role='judge',request=req,response=result));return result
    original=source('I am staying in Boston through 2026-09-30.');original['session_id']='writer'
    store.put_source(owner,original)
    try:
        result=await EvidenceWriter(store,Recorded(),budget,expiry=True).process_next(owner)
        rows=store.search(owner,historical=True)
        end=1790827200. # October 1, midnight America/New_York
        checks['writer_expiry']=len(rows)==1 and rows[0]['valid_until']==end
        store.clock=lambda:end
        checks['expired_current']=not store.search(owner)
        checks['historical_preserved']=len(store.search(owner,historical=True))==1
        checks['source_preserved']=store.source(owner,'writer')==original
        (directory/'writer.json').write_text(json.dumps(dict(source=original,result=result,rows=rows,checks=checks),indent=2))
    finally:
        (directory/'provider-calls.json').write_text(json.dumps(calls,indent=2))
        print(json.dumps(dict(checks=checks,budget=budget.report())),flush=True)
    if not all(checks.values()):raise RuntimeError('Expiry writer gate failed; no retry')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--budget',type=Path,required=True);a=p.parse_args()
    asyncio.run(run(a.directory,a.budget))
