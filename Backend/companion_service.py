"""Opt-in persistent chat socket service. No production route is enabled here."""
import asyncio
from contextlib import aclosing
import json
import time
from admission import Rejected
from ask import input_fits,references
from companion_chat import CompanionChat
from companion_context import assemble
from companion_snapshots import release
from indexed_recall import memory_disabled
from memory_context import valid
from memory_store import identifier,validate_source


def validate_request(raw):
    if not isinstance(raw,str) or len(raw.encode())>64000:raise Rejected('context_too_large')
    try:
        data=json.loads(raw)
        if not isinstance(data,dict):raise ValueError()
        if data.get('operation')=='source':
            if set(data)!={'operation','turn_id','citation_id'}:raise ValueError()
            identifier(data['turn_id']);identifier(data['citation_id'])
            return data
        if data.get('operation')=='history':
            if set(data)!={'operation','before'} or (data['before'] is not None and (type(data['before']) is not int or data['before']<1)):
                raise ValueError()
            return data
        if set(data)!={'operation','question_id','question','memory','attachment','live'} or data['operation']!='ask':raise ValueError()
        identifier(data['question_id'])
        if not isinstance(data['question'],str) or not data['question'].strip() or len(data['question'])>1000 or type(data['memory']) is not bool:raise ValueError()
        if data['attachment'] is not None:
            ref=data['attachment']
            if not isinstance(ref,dict) or set(ref)!={'session_id','revision'} or type(ref['revision']) is not int or ref['revision']<1:raise ValueError()
            identifier(ref['session_id'])
        if data['live'] is not None:
            validate_source(data['live'])
            if data['live']['completed'] or data['live'].get('origin') is not None:raise ValueError()
        return data
    except (ValueError,KeyError,TypeError):raise Rejected('invalid_chat_request') from None


class CompanionService:
    def __init__(self,admission,memory,provider,recall=None):
        self.admission,self.memory,self.provider,self.recall=admission,memory,provider,recall
        self.chat=CompanionChat(memory)

    async def handle(self,socket):
        token=socket.request.headers.get('Authorization','').removeprefix('Bearer ')
        started_at=time.monotonic();first_text=None;usage={}
        owner=None;request=None;created=False;completed=False;reservation=None;prepared=None
        async def send(event):await socket.send(json.dumps(event))
        try:
            credential=self.admission.authorized(token)
            async with asyncio.timeout(5):request=validate_request(await socket.recv())
            owner=await asyncio.to_thread(self.memory.owner_for,credential)
            if request['operation']=='source':
                item=await asyncio.to_thread(self.chat.citation,owner,request['turn_id'],request['citation_id'])
                await send(dict(type='source',turn_id=request['turn_id'],source=item));return
            if request['operation']=='history':
                await send(dict(type='history',**await asyncio.to_thread(self.chat.page,owner,before=request['before'])))
                return
            context={k:request[k] for k in ('memory','attachment','live')}
            started=await asyncio.to_thread(self.chat.start,owner,request['question_id'],request['question'],context=context)
            created=started['created']
            if not created:
                turn=dict(started['turn']);turn.pop('owner');turn['citations']=json.loads(turn['citations'])
                await send(dict(type='existing',conversation_id=started['conversation_id'],turn=turn));return
            reservation=self.admission.reserve(token,'ask')
            await send(dict(type='accepted',question_id=request['question_id'],conversation_id=started['conversation_id']))
            async def check():
                self.admission.authorized(token)
                if prepared:
                    for packet in prepared['packets']:
                        if not await asyncio.to_thread(valid,self.memory,owner,packet):raise Rejected('memory_context_changed')
                    await asyncio.to_thread(self.chat.evidence,owner,prepared['history_ids'])

            async def generate():
                nonlocal prepared,completed,first_text,usage
                use_memory=request['memory'] and not memory_disabled(dict(question=request['question']))
                past=None;status='disabled'
                if use_memory:
                    status='unavailable'
                    if self.recall:
                        try:
                            async with asyncio.timeout(3):
                                manifest=await self.recall.prepare(credential,dict(question=request['question'],passages=[],memory=True,
                                    session_id=request['live']['session_id'] if request['live'] else '__main_chat__'))
                            status=manifest['status'];past=manifest.get('packet')
                        except Exception:pass
                assembly=asyncio.create_task(asyncio.to_thread(assemble,self.memory,owner,request['question'],attachment=request['attachment'],
                    live=request['live'],past=past,memory_status=status,use_memory=use_memory))
                try:prepared=await asyncio.shield(assembly)
                except asyncio.CancelledError:
                    prepared=await assembly;raise
                if not input_fits(prepared['data']):raise Rejected('companion_context_too_large')
                await check()
                await send(dict(type='context',sources=prepared['data']['sources'],memory_status=status))
                answer=''
                async with aclosing(self.provider.stream(prepared['data'])) as events:
                    async for event in events:
                        if event['type']=='delta':
                            if first_text is None:first_text=time.monotonic()-started_at
                            answer+=event['text']
                            if len(answer.encode())>16000:raise Rejected('answer_incomplete')
                            await send(event)
                        elif event['type']=='completed':
                            if not answer.strip():raise Rejected('answer_incomplete')
                            refs=references(answer,prepared['data']['sources'])
                            citations=[dict(id=item['id'],source=item) for item in prepared['data']['sources'] if item['id'] in refs]
                            await check()
                            save=asyncio.create_task(asyncio.to_thread(self.chat.complete,owner,request['question_id'],answer,
                                packets=prepared['packets'],history_ids=prepared['history_ids'],citations=citations))
                            try:await asyncio.shield(save)
                            except asyncio.CancelledError:
                                await save;completed=True;raise
                            completed=True
                            usage={key:event.get(key) for key in ('input_tokens','output_tokens')}
                            await send(dict(type='done',question_id=request['question_id'],references=refs,saved=True))
                            return
                raise Rejected('answer_incomplete')

            async def monitor():
                while True:
                    await asyncio.sleep(.25);await check()
            async def disconnected():
                await socket.wait_closed();raise Rejected('cancelled')
            tasks=[asyncio.create_task(generate()),asyncio.create_task(monitor()),asyncio.create_task(disconnected())]
            try:
                async with asyncio.timeout(20):
                    done,_=await asyncio.wait(tasks,return_when=asyncio.FIRST_COMPLETED)
                    for task in done:task.result()
            finally:
                for task in tasks:
                    if not task.done():task.cancel()
                await asyncio.gather(*tasks,return_exceptions=True)
        except Exception as error:
            try:await send(dict(type='error',message=str(error) if isinstance(error,Rejected) else 'answer_unavailable'))
            except Exception:pass
        finally:
            if created and not completed:await asyncio.to_thread(self.chat.fail,owner,request['question_id'])
            if prepared:
                for snapshot in {item['snapshot_id'] for p in prepared['packets'] for item in p['items'] if 'snapshot_id' in item}:
                    await asyncio.to_thread(release,self.memory,owner,snapshot)
            if reservation:
                self.admission.finish(reservation,completed=completed)
                print(json.dumps(dict(category='companion',request_id=reservation,completed=completed,
                    first_text_seconds=first_text,elapsed_seconds=time.monotonic()-started_at,**usage)),flush=True)
            await socket.close()
