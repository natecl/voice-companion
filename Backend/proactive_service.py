"""Bounded internal contribution execution; not enabled in hosted routing yet."""
import asyncio
import copy
import hashlib
import json
import uuid
from admission import Rejected
from companion_snapshots import freeze, release
from notes_recall import validate_selection
from proactive_context import prepare
from proactive_models import draft_request,parse_draft,judge_request,allow_draft
from proactive_policy import cutoff
from proactive_store import ProactiveStore


class ProactiveService:
    def __init__(self,store,models,budget,*,route='llm',embedder=None):
        if route not in ('llm','jev'):raise ValueError('Unknown proactive route')
        self.store,self.models,self.budget=store,models,budget
        self.route,self.embedder=route,embedder
        self.messages=ProactiveStore(store)

    async def _call(self,key,request,call):
        self.budget.reserve(key,request['model'])
        try:
            response=await call(request)
            self.budget.finish(key,response.get('usage',{}))
            return response['data']
        except BaseException:
            self.budget.finish(key)
            raise

    async def evaluate(self,owner,live,is_current):
        """is_current is application-owned authorization/capture/foreground validation.

        The caller must serialize updates with commit on the same event loop.
        This method performs its final validation and SQLite commit without await.
        """
        live=copy.deepcopy(live)
        digest=cutoff(live);capture=live['session_id']
        if not is_current():return dict(type='cancelled')
        prior=self.messages.claim(owner,capture,digest)
        if prior:return dict(type='existing',**prior)
        snapshot=None;terminal='unavailable'
        try:
            async with asyncio.timeout(15):
                context=prepare(self.store,owner,live,self.messages.previous(owner,capture),self.embedder)
                if not context:
                    terminal='silence';return dict(type='silence')
                state=context['state']
                # Freeze only the bounded current context, preserving original passage offsets.
                refs=[dict(session_id=capture,revision=live['revision'],passage_id=p['id'],text_start=0,text_end=len(p['text']))
                    for p in state['current']['passages']]
                snapshot=freeze(self.store,owner,live,refs)
                def check():
                    if not is_current():raise Rejected('proactive_cancelled')
                    if not validate_selection(self.store,owner,context['packet'],context['notes']):
                        raise Rejected('memory_context_changed')
                check()
                key='proactive:'+owner+':'+capture+':'+digest
                if self.route=='jev':
                    req=judge_request(state)
                    judged=await self._call(key+':judge',req,self.models.judge)
                    check()
                    if not allow_draft(judged,req):
                        terminal='silence';return dict(type='silence')
                result=await self._call(key+':draft',draft_request(state),self.models.extract)
                check();result=parse_draft(result,state)
                if result['decision']=='silence':
                    terminal='silence';return dict(type='silence')
                selected=[s for s in state['sources'] if s['id'] in result['evidence_ids']]
                # Stable source span identity, not model wording or ephemeral m1 numbering.
                identity=sorted((s['session_id'],s['passage_id'],s.get('retained_claim_id','')) for s in selected)
                connection=hashlib.sha256(json.dumps(identity).encode()).hexdigest()
                turn=self.messages.save(owner,capture,digest,str(uuid.uuid4()),connection,result['text'],context['packet'],snapshot)
                terminal='silence' if turn is None else 'complete'
                return dict(type='silence') if turn is None else dict(type='contribution',turn_id=turn,text=result['text'])
        except asyncio.CancelledError:
            terminal='cancelled';raise
        except (Rejected,TimeoutError) as error:
            terminal='cancelled' if str(error)=='proactive_cancelled' else 'unavailable'
            return dict(type=terminal)
        except Exception:
            # No provider details/private payloads in user-facing results; no paid retry.
            return dict(type='unavailable')
        finally:
            if terminal!='complete':self.messages.finish(owner,capture,digest,terminal)
            if snapshot:
                for item in snapshot['items']:
                    release(self.store,owner,item['snapshot_id'])
