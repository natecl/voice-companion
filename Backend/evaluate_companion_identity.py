"""Three targeted Luna calls; unchanged Jev correction ranking is replayed exactly."""
import argparse
import asyncio
import json
import os
from pathlib import Path
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from admission import Admission
from ask import Luna,instructions
from companion_service import CompanionService
from companion_chat import CompanionChat
from companion_context import assemble
from indexed_recall import IndexedMemoryRecall
from memory_store import MemoryStore
from memory_models import LUNA,JEV
from profile_budget import ProfileBudget
from test_memory import source,candidate
from test_companion_service import question

async def run(directory,budget_path,recorded):
    directory.mkdir(parents=True,exist_ok=False)
    budget=ProfileBudget(budget_path,include_rework_allowance=True,include_consolidation_allowance=True,include_multisource_allowance=True)
    judgment=next(c for c in json.loads(recorded.read_text()) if c['kind']=='jev')
    outputs=[];counter=0;replays=0
    class ReplayBudget:
        def reserve(self,key,model):assert model==JEV
        def finish(self,*args):pass
    class Replay:
        async def judge(self,req):
            nonlocal replays
            assert req==judgment['request'],'Changed Jev input requires separate validation'
            replays+=1;return judgment['response']
    class Answers:
        async def stream(self,data):
            nonlocal counter
            assert counter<3
            if data['question']=='What sport does Maya enjoy now?':assert any(s['session_id']=='correction' for s in data['sources'])
            key='companion-identity-v2:'+str(counter);budget.reserve(key,LUNA);counter+=1
            text='';usage=None
            try:
                async for event in Luna(os.environ['OPENAI_API_KEY']).stream(data):
                    if event['type']=='delta':text+=event['text']
                    if event['type']=='completed':usage=event
                    yield event
            finally:
                budget.finish(key,usage);outputs.append(dict(data=data,instructions=instructions(data),answer=text,usage=usage))
                (directory/'answers.json').write_text(json.dumps(outputs,indent=2))
    admission=Admission(directory/'usage.sqlite',total_microusd=30000,limits={'ask':(30000,3000,20)})
    memory=MemoryStore(directory/'memory.sqlite')
    handler=CompanionService(admission,memory,Answers(),IndexedMemoryRecall(memory,Replay(),ReplayBudget(),multi_source=True))
    try:
        async with serve(handler.handle,'127.0.0.1',0,max_size=64000) as server:
            url=f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}'
            async def call(token,req):
                async with connect(url,additional_headers={'Authorization':'Bearer '+token}) as ws:
                    await ws.send(json.dumps(req));events=[json.loads(e) async for e in ws]
                assert events[-1]['type']=='done',events[-1]
                return ''.join(e['text'] for e in events if e['type']=='delta'),events
            for i,(text,query) in enumerate([('I am an endurance runner.','Am I an endurance runner?'),('My daughter Iris enjoys swimming.','Do I have a daughter named Iris?')]):
                _,token=admission.enroll();live=source('anonymous',text=text);live['completed']=False
                answer,events=await call(token,question('identity'+str(i),question=query,live=live))
                lower=answer.casefold()
                assert any(word in lower for word in ('speaker','who said','was you','were you','your voice'))
                assert any(word in lower for word in ('unknown','unidentified','not identified','cannot',"can't",'can’t','unclear',"don't know",'not establish','doesn’t identify','does not identify'))
                assert events[-1]['references']
            credential,token=admission.enroll();owner=memory.owner_for(credential);chat=CompanionChat(memory)
            live=source('recording',text='Maya enjoys swimming.');live['completed']=False
            chat.start(owner,'earlier','What does Maya enjoy?');prepared=assemble(memory,owner,'What does Maya enjoy?',live=live)
            chat.complete(owner,'earlier','Maya enjoys swimming. [[p1]]',packets=prepared['packets'],citations=[dict(id='p1',source=prepared['data']['sources'][0])])
            memory.put_source(owner,source('recording',text='Maya enjoys swimming. We finished the conversation.'))
            memory.commit_claims(memory.claim_job(owner),[candidate('Maya enjoys swimming.')]);old=memory.search(owner)[0]['id']
            memory.put_source(owner,source('correction',text='Maya now enjoys tennis instead of swimming.'))
            memory.commit_claims(memory.claim_job(owner),[candidate('Maya enjoys tennis.',relation='supersedes',target=old)])
            answer,events=await call(token,question('correction',question='What sport does Maya enjoy now?'))
            assert 'tennis' in answer.casefold()
            sources=next(e['sources'] for e in events if e['type']=='context')
            assert any(s['session_id']=='correction' and s['id'] in events[-1]['references'] for s in sources)
        print(json.dumps(dict(paid_calls=counter,replayed_jev=replays,budget=budget.report())),flush=True)
    finally:
        admission.close();print(json.dumps(dict(budget=budget.report())),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('directory',type=Path);p.add_argument('--budget',type=Path,required=True);p.add_argument('--recorded',type=Path,required=True)
    a=p.parse_args();asyncio.run(run(a.directory,a.budget,a.recorded))
