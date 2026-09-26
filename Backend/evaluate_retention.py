"""Actual local companion sockets + retained-memory recall, bounded operator transport.

Provider credentials and the six-call/$0.05 ledger stay in the operator transport.
Responses are saved for exact-request replay. Never fall back to paid requests in
replay mode. Answer transport is non-streaming; this tests context/answer behavior,
not streaming latency or physical capture.
"""
import argparse
import asyncio
import json
from pathlib import Path
import shlex
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from admission import Admission
from ask import MODEL,instructions,input_fits
from companion_service import CompanionService
from indexed_recall import IndexedMemoryRecall
from memory_models import fingerprint
from memory_store import MemoryStore
from retention_fixture import seed

QUESTIONS=[
    'Where does Project Juniper meet now?',
    'Can you quote the exact words from the deleted recording?',
    'Does Project Juniper preferring morning meetings establish that I personally prefer morning meetings?']

class Transport:
    def __init__(self,directory,command=None,replay=None):
        self.directory,self.command=directory,command
        self.saved={fingerprint(c['request']):c for c in json.loads(replay.read_text())} if replay else {}
        self.calls=[];self.process=None;self.errors=None
    async def start(self):
        if self.command:
            self.errors=(self.directory/'transport.log').open('w')
            self.process=await asyncio.create_subprocess_exec(*shlex.split(self.command),stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,stderr=self.errors)
            assert json.loads(await self.process.stdout.readline())=={'ready':True}
    async def call(self,request):
        if self.command:
            self.process.stdin.write((json.dumps(request)+'\n').encode());await self.process.stdin.drain()
            line=await self.process.stdout.readline()
            if not line:raise RuntimeError('Transport ended; no automatic retry')
            value=json.loads(line)
            if 'error' in value:raise RuntimeError(value['error'])
            assert value['request']==request
        else:
            key=fingerprint(request)
            if key not in self.saved:raise AssertionError('Missing exact response; external calls forbidden')
            value=self.saved[key]
        self.calls.append(value)
        (self.directory/'calls.json').write_text(json.dumps(self.calls,indent=2))
        return value['raw']
    async def judge(self,request):
        raw=await self.call(request)
        return dict(data=raw,usage=raw.get('usage',{}))
    async def stream(self,data):
        assert input_fits(data)
        request=dict(model=MODEL,reasoning={'effort':'none'},service_tier='default',instructions=instructions(data),
            input=json.dumps(data,ensure_ascii=False),max_output_tokens=1000,store=False,tools=[],truncation='disabled')
        raw=await self.call(request)
        if raw.get('status')!='completed':raise RuntimeError('Provider response incomplete')
        text=''.join(c['text'] for o in raw['output'] if o['type']=='message' for c in o['content'] if c['type']=='output_text')
        yield dict(type='delta',text=text)
        yield dict(type='completed',input_tokens=raw.get('usage',{}).get('input_tokens'),output_tokens=raw.get('usage',{}).get('output_tokens'))
    async def close(self):
        if self.process:
            self.process.stdin.close();await self.process.wait()
        if self.errors:self.errors.close()

class TransportBudget:
    # The remote operator transport reserves each real call before network access.
    def reserve(self,*args):pass
    def finish(self,*args):pass

async def run(directory,command=None,replay=None):
    directory.mkdir(parents=True,exist_ok=False)
    store=MemoryStore(directory/'memory.sqlite',retain_recording_memories=True)
    ledger=Admission(directory/'local-socket-ledger.sqlite',total_microusd=9000,limits={'ask':(9000,3000,3)})
    credential,token=ledger.enroll()
    if replay:
        state=json.loads((replay.parent/'state.json').read_text())
        with store.transaction() as db:
            db.execute('PRAGMA defer_foreign_keys=ON')
            for table,rows in state.items():
                if table not in {'owner','source','claim','support','memory_entity','memory_mention',
                    'memory_identity_link','memory_identity_support','memory_correction','memory_correction_link',
                    'claim_relation_proposal','memory_fact_evidence','retained_recording'}:raise ValueError('Unexpected fixture table')
                for row in rows:
                    columns=[r[1] for r in db.execute('PRAGMA table_info('+table+')')]
                    if set(row)!=set(columns):raise ValueError('Unexpected fixture columns')
                    db.execute('INSERT INTO '+table+' VALUES('+','.join('?' for _ in columns)+')',[row[c] for c in columns])
        owner=store.owner_for(credential,existing_owner=state['owner'][0]['id'])
    else:
        owner=store.owner_for(credential)
        await seed(store,owner,directory/'seed')
    # Discard only the synthetic fixture answer from this isolated QA database.
    with store.transaction() as db:
        for table in ('companion_dependency','companion_request','companion_turn'):
            db.execute('DELETE FROM '+table+' WHERE owner=?',(owner,))
    transport=Transport(directory,command,replay);results=[]
    try:
        await transport.start()
        recall=IndexedMemoryRecall(store,transport,TransportBudget(),multi_source=True)
        service=CompanionService(ledger,store,transport,recall)
        async with serve(service.handle,'127.0.0.1',0,max_size=64000) as server:
            url=f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/companion'
            async def exchange(payload):
                async with connect(url,additional_headers={'Authorization':'Bearer '+token}) as socket:
                    await socket.send(json.dumps(payload));return [json.loads(raw) async for raw in socket]
            for index,question in enumerate(QUESTIONS):
                events=await exchange(dict(operation='ask',question_id=f'retention-{index}',question=question,memory=True,attachment=None,live=None))
                result=dict(question=question,events=events)
                results.append(result);(directory/'results.json').write_text(json.dumps(results,indent=2))
                assert events[-1].get('saved') is True,events[-1]
                context=next(e for e in events if e['type']=='context')
                assert context['memory_status']!='unavailable','Retrieval failed; do not accept degraded QA'
                answer=''.join(e['text'] for e in events if e['type']=='delta')
                print(json.dumps(dict(case=index,answer=answer,memory_status=context['memory_status'])),flush=True)
                if index==0:assert 'community center' in answer.lower(),'Corrected location missing'
                page=await exchange(dict(operation='history',before=None))
                assert page[0]['turns'][-1]['state']=='complete'
                for citation in page[0]['turns'][-1]['citations']:
                    assert 'retained_claim_id' in citation['source']
                    unavailable=await exchange(dict(operation='source',turn_id=f'retention-{index}',citation_id=citation['id']))
                    assert unavailable==[dict(type='error',message='source_unavailable')]
        from companion_chat import CompanionChat
        reopened=CompanionChat(MemoryStore(directory/'memory.sqlite')).page(owner)
        assert len(reopened['turns'])==3 and all(t['state']=='complete' for t in reopened['turns'])
        summary=dict(calls=len(transport.calls),new_paid_calls=len(transport.calls) if command else 0,
            recorded_reservation_microusd=sum(c['reserved_microusd'] for c in transport.calls),
            reopened=True,answers=[t['answer'] for t in reopened['turns']],manual_semantic_review_required=True)
        (directory/'summary.json').write_text(json.dumps(summary,indent=2))
    finally:
        await transport.close();ledger.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path)
    mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--transport');mode.add_argument('--replay',type=Path)
    args=parser.parse_args();asyncio.run(run(args.directory,args.transport,args.replay))
