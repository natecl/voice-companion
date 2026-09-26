"""Frozen five-answer real socket gate. Six paid calls maximum; no retries."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from admission import Admission,Rejected
from ask import Luna,instructions
from companion_service import CompanionService
from companion_chat import CompanionChat
from indexed_recall import IndexedMemoryRecall
from memory_store import MemoryStore
from memory_models import MemoryModels,LUNA
from profile_budget import ProfileBudget
from test_memory import source,candidate
from test_companion_service import question


async def run(directory,budget_path):
    directory.mkdir(parents=True,exist_ok=False)
    canonical=ProfileBudget(budget_path,include_rework_allowance=True,include_consolidation_allowance=True,include_multisource_allowance=True)
    calls=[];outputs=[];counter=0
    class Budget:
        def reserve(self,key,model):
            nonlocal counter
            if counter>=6:raise Rejected('frozen_qa_call_limit')
            canonical.reserve(key,model);counter+=1
        def finish(self,*args):canonical.finish(*args)
    budget=Budget();models=MemoryModels(os.environ['OPENAI_API_KEY'],os.environ['TYPESAFE_API_KEY'])
    class Judgments:
        async def judge(self,req):
            result=await models.judge(req);calls.append(dict(kind='jev',request=req,response=result));return result
    class Answers:
        async def stream(self,data):
            key='companion-service-v1:'+str(counter)
            budget.reserve(key,LUNA);usage=None;answer=''
            try:
                async for event in Luna(os.environ['OPENAI_API_KEY']).stream(data):
                    if event['type']=='delta':answer+=event['text']
                    if event['type']=='completed':usage=event
                    yield event
            finally:
                budget.finish(key,usage)
                calls.append(dict(kind='luna',data=data,instructions=instructions(data),answer=answer,usage=usage))
    admission=Admission(directory/'usage.sqlite',total_microusd=30000,limits={'ask':(30000,3000,20)})
    credential,token=admission.enroll();store=MemoryStore(directory/'memory.sqlite');owner=store.owner_for(credential)
    handler=CompanionService(admission,store,Answers(),IndexedMemoryRecall(store,Judgments(),budget,multi_source=True))
    async def call(url,key,req):
        async with connect(url,additional_headers={'Authorization':'Bearer '+key}) as ws:
            await ws.send(json.dumps(req));events=[json.loads(event) async for event in ws]
        outputs.append(dict(request=req,events=events));(directory/'socket-events.json').write_text(json.dumps(outputs,indent=2))
        assert events[-1]['type']=='done',events[-1]
        return ''.join(event['text'] for event in events if event['type']=='delta'),next(event['sources'] for event in events if event['type']=='context'),events[-1]['references']
    try:
        async with serve(handler.handle,'127.0.0.1',0,max_size=64000) as server:
            url=f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}'
            live=source('recording',text='Maya enjoys swimming.');live['completed']=False
            text,_,refs=await call(url,token,question('live',live=live))
            assert 'swim' in text.casefold() and refs
            store.put_source(owner,source('recording',text='Maya enjoys swimming. We finished the conversation.'))
            text,_,_=await call(url,token,question('followup',question='Does that hobby need a pool?'))
            assert any(word in text.casefold() for word in ('pool','water'))
            # Synthetic established transitions exercise recall, not the separately validated writer model.
            store.commit_claims(store.claim_job(owner),[candidate('Maya enjoys swimming.')]);old=store.search(owner)[0]['id']
            store.put_source(owner,source('correction',text='Maya now enjoys tennis instead of swimming.'))
            store.commit_claims(store.claim_job(owner),[candidate('Maya enjoys tennis.',relation='supersedes',target=old)])
            text,sources,refs=await call(url,token,question('correction',question='What sport does Maya enjoy now?'))
            assert 'tennis' in text.casefold()
            assert any(s['session_id']=='correction' and s['id'] in refs for s in sources)
            _,empty=admission.enroll()
            text,sources,refs=await call(url,empty,question('general',question='What is 2 plus 2?'))
            assert ('4' in text or 'four' in text.casefold()) and not sources and not refs
            _,anonymous=admission.enroll()
            unknown=source('anonymous',text='I am an endurance runner.');unknown['completed']=False
            text,_,refs=await call(url,anonymous,question('unknown',question='Am I an endurance runner?',live=unknown))
            assert any(word in text.casefold() for word in ('speaker','who said','was you','were you','your voice')), 'Must explain uncertain speaker identity, not just temporal uncertainty'
            assert any(word in text.casefold() for word in ('unknown','cannot',"can't",'can’t','unclear',"don't know",'doesn’t identify','does not identify','not clear',"can't tell",'can’t tell','not enough','unidentified'))
            assert refs
            assert len(CompanionChat(store).page(owner)['turns'])==3
        print(json.dumps(dict(paid_calls=counter,budget=canonical.report(),cases=5)),flush=True)
    finally:
        admission.close();(directory/'provider-calls.json').write_text(json.dumps(calls,indent=2))
        print(json.dumps(dict(budget=canonical.report())),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--budget',type=Path,required=True)
    a=p.parse_args();asyncio.run(run(a.directory,a.budget))
