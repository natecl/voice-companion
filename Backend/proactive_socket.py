"""Authenticated foreground lifecycle for contributions; hosted startup does not enable it."""
import asyncio
import json
import time
from admission import Rejected
from proactive_policy import ProactivePolicy,cutoff
from memory_store import identifier


def request(raw):
    if not isinstance(raw,str) or len(raw.encode())>64000:raise Rejected('invalid_proactive_request')
    try:
        data=json.loads(raw)
        if not isinstance(data,dict):raise ValueError()
        operation=data.get('operation')
        if operation=='observe':
            if set(data)!={'operation','live'}:raise ValueError()
            cutoff(data['live'])
        elif operation in ('open','quiet','stop'):
            if set(data)!={'operation','capture'}:raise ValueError()
            identifier(data['capture'])
        else:raise ValueError()
        return data
    except (ValueError,KeyError,TypeError):raise Rejected('invalid_proactive_request') from None


class ProactiveSocketService:
    def __init__(self,admission,service,*,clock=time.monotonic):
        self.admission,self.service,self.clock=admission,service,clock
        self.policies={};self.connected=set();self.revisions={}

    async def handle(self,socket):
        token=socket.request.headers.get('Authorization','').removeprefix('Bearer ')
        policy=None;job=None;owner=None;registered=False
        async def send(event):await socket.send(json.dumps(event))
        try:
            credential=self.admission.authorized(token)
            owner=self.service.store.owner_for(credential)
            async with asyncio.timeout(5):first=request(await socket.recv())
            if first['operation']!='open':raise Rejected('proactive_open_required')
            if owner in self.connected:raise Rejected('proactive_already_connected')
            key=(owner,first['capture'])
            if key not in self.policies:
                if len(self.policies)>=128:raise Rejected('proactive_session_limit')
                policy=ProactivePolicy();policy.start(*key);self.policies[key]=policy
            else:
                policy=self.policies[key];policy.resume()
            self.connected.add(owner);registered=True
            await send(dict(type='ready',enabled=policy.enabled))

            async def evaluate(lease,live):
                def current():
                    self.admission.authorized(token)
                    return policy.valid(lease,self.clock())
                try:
                    result=await self.service.evaluate(owner,live,current)
                    if not current():return
                    contributed=result['type']=='contribution'
                    policy.finish(lease,self.clock(),result.get('turn_id') if contributed else None)
                    await send(result)
                except asyncio.CancelledError:raise
                except Exception:
                    if policy.valid(lease,self.clock()):
                        policy.finish(lease,self.clock());await send(dict(type='unavailable'))

            async for raw in socket:
                self.admission.authorized(token)
                data=request(raw)
                if data['operation']=='open':raise Rejected('proactive_already_open')
                if data['operation'] in ('quiet','stop'):
                    if data['capture']!=policy.capture:raise Rejected('proactive_capture_changed')
                    policy.quiet()
                    if job:
                        job.cancel();await asyncio.gather(job,return_exceptions=True);job=None
                    await send(dict(type='quiet'))
                    if data['operation']=='stop':return
                else:
                    stamp=(data['live']['revision'],cutoff(data['live']))
                    previous=self.revisions.get(key)
                    if previous and (stamp[0]<previous[0] or (stamp[0]==previous[0] and stamp[1]!=previous[1])):
                        raise Rejected('proactive_revision_changed')
                    self.revisions[key]=stamp
                    # observe invalidates an older lease before cancellation can complete.
                    lease=policy.observe(data['live'],self.clock())
                    if job and not job.done() and (lease is not None or policy.pending is None):
                        job.cancel();await asyncio.gather(job,return_exceptions=True);job=None
                    if lease is not None:job=asyncio.create_task(evaluate(lease,data['live']))
        except Exception:
            try:await send(dict(type='unavailable'))
            except Exception:pass
        finally:
            if registered:
                policy.background()
                if job:
                    job.cancel();await asyncio.gather(job,return_exceptions=True)
                self.connected.discard(owner)
