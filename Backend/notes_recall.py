"""Unified notes/transcript recall candidate; existing rollout flag stays off."""
import asyncio
import json
import re
import uuid
from admission import Rejected
from indexed_recall import memory_disabled
from memory_models import JEV
import memory_context
import memory_hybrid
import memory_multi_ranking
import memory_related
import memory_retention
from memory_search import STOP_WORDS
import notes_search
from recording_notes import RecordingNotes


def packet_for(store, owner, refs):
    return memory_context.select(store, owner, refs, limit=8)


def evidence_key(item):
    return (item.get('retained_claim_id'),item['session_id'],item['revision'],
            item['passage_id'],item['text_start'],item['text_end'])


def bounded_packet(store,owner,item,query):
    if len(item['text'])>1800:
        terms=[t for t in re.findall(r'\w+',query.casefold()) if t not in STOP_WORDS]
        positions=[item['text'].casefold().find(t) for t in terms if t in item['text'].casefold()]
        start=max(0,(min(positions) if positions else 0)-300)
        end=min(len(item['text']),start+1800)
        item={**item,'text_start':item['text_start']+start,'text_end':item['text_start']+end}
    return packet_for(store,owner,[item])


def collect(store, owner, query, exclude_session=None, embedder=None):
    """Fuse discovery routes; rank each original excerpt once, never its summary twice."""
    routes=[]
    hybrid=memory_hybrid.retrieve(store,owner,query,embedder=embedder,
        exclude_session=exclude_session,limit=12)['packet']['items']
    routes.append([dict(kind='retained' if 'retained_claim_id' in p else 'transcript',item=p) for p in hybrid])
    notes=[]
    for note in notes_search.retrieve(store,owner,query,limit=12,exclude_session=exclude_session):
        refs=[dict(session_id=note['session_id'],revision=note['revision'],passage_id=p) for p in note['passages']]
        packet=packet_for(store,owner,refs)
        if len(packet['items'])==len(refs):
            notes.extend(dict(kind='note',item=p,note=note) for p in packet['items'])
    routes.append(notes)
    terms=' '.join(t for t in re.findall(r'\w+',query.casefold()) if t not in STOP_WORDS)
    personal=[]
    if terms:
        for claim in store.search(owner,terms,profile_only=True,limit=4):
            refs=[dict(session_id=s['session'],revision=s['revision'],passage_id=s['passage'])
                  for s in claim['sources'] if s['session']!=exclude_session]
            personal.extend(dict(kind='personal',item=p) for p in packet_for(store,owner,refs[:8])['items'])
    routes.append(personal)
    refs=memory_retention.retrieve(store,owner,query,limit=4,exclude_session=exclude_session)
    routes.append([dict(kind='retained',item=p) for p in packet_for(store,owner,refs)['items']])
    candidates={}
    for route in routes:
        visited=set()
        for hit in route:
            packet=bounded_packet(store,owner,hit['item'],query)
            if not packet['items']:continue
            item=packet['items'][0];key=evidence_key(item)
            candidate=candidates.setdefault(key,dict(kind=hit['kind'],kinds=[],text=item['text'],
                packet=packet,notes=[],score=0.))
            # Concurrent source/claim changes must not be hidden by mixing snapshots.
            if candidate['packet']!=packet:raise Rejected('memory_context_changed')
            if hit['kind'] not in candidate['kinds']:candidate['kinds'].append(hit['kind'])
            if 'note' in hit and hit['note'] not in candidate['notes']:candidate['notes'].append(hit['note'])
            if key not in visited:
                visited.add(key);candidate['score']+=1/(60+len(visited))
    return sorted(candidates.values(),key=lambda c:(-c['score'],evidence_key(c['packet']['items'][0])[1:]))[:12]


def selection_order(ranking,pool_size):
    # Jev reorders; it cannot erase the strongest two independently discovered
    # excerpts. Include at most four excerpts total, plus known correction context.
    # This is bounded context discovery, not a claim that every excerpt is relevant.
    ranked=sorted((k for k,a in ranking['judgments'].items() if a['choice']!='unrelated'),key=lambda k:(
        -ranking['judgments'][k]['probabilities']['helpful'],int(k[1:])))
    return list(dict.fromkeys([f'p{i}' for i in range(min(2,pool_size))]+ranked))


def note_valid(store,owner,note):
    try:
        current=RecordingNotes(store).read(owner,note['session_id'])
    except Rejected:
        return False
    if not current or current['state']!='ready' or current['revision']!=note['revision'] or current['generation_version']!=note['generation_version']:
        return False
    payload=current['notes']
    entries=[('Overview',payload['overview'])]+[(s['heading'],b) for s in payload['sections'] for b in s['items']]
    index=int(note['entry'])
    if index>=len(entries):return False
    heading,item=entries[index]
    return note['text']==payload['title']+'\n'+heading+'\n'+item['text'] and note['passages']==item['passages']


def validate_selection(store,owner,packet,notes):
    return memory_context.valid(store,owner,packet) and all(note_valid(store,owner,n) for n in notes)


class NotesFirstRecall:
    def __init__(self,store,models,budget,embedder=None):
        self.store,self.models,self.budget,self.embedder=store,models,budget,embedder

    async def prepare(self,credential,data):
        if memory_disabled(data):
            return dict(status='disabled',sources=[],contract='indexed-v1',packet=None)
        owner=await asyncio.to_thread(self.store.owner_for,credential)
        pool=await asyncio.to_thread(collect,self.store,owner,data['question'],data.get('session_id'),self.embedder)
        chosen=packet_for(self.store,owner,[]);notes=[];skipped=0
        if pool:
            request=memory_multi_ranking.request(data['question'],[c['text'] for c in pool])
            attempt=str(uuid.uuid4())+':notes-ranking'
            await asyncio.to_thread(self.budget.reserve,attempt,JEV)
            try:
                response=await self.models.judge(request)
                await asyncio.to_thread(self.budget.finish,attempt,response['usage'])
                ranking=memory_multi_ranking.order(response['data'],request)
            except BaseException:
                await asyncio.to_thread(self.budget.finish,attempt)
                raise
            count=0
            for key in selection_order(ranking,len(pool)):
                if count==4:break
                candidate=pool[int(key[1:])]
                candidate_notes=candidate['notes']
                if not await asyncio.to_thread(validate_selection,self.store,owner,candidate['packet'],candidate_notes):
                    raise Rejected('memory_context_changed')
                if all(item in chosen['items'] for item in candidate['packet']['items']):continue
                # Keep pre-judgment snapshots. Rehydrating here would hide revisions.
                items=list(chosen['items'])
                for item in candidate['packet']['items']:
                    if item not in items:items.append(item)
                trial=dict(version=chosen['version'],owner=owner,items=items,digest=memory_context.fingerprint(items))
                trial=await asyncio.to_thread(memory_related.expand,self.store,owner,trial)
                if len(trial['items'])>8 or len(json.dumps(trial['items'],ensure_ascii=False).encode())>10000:
                    if count<min(2,len(pool)):raise Rejected('recall_too_large')
                    skipped+=1;continue
                chosen=trial;notes+=candidate_notes;count+=1
        if not await asyncio.to_thread(validate_selection,self.store,owner,chosen,notes):
            raise Rejected('memory_context_changed')
        sources=[dict(id=f'm{i}',**item) for i,item in enumerate(chosen['items'],1)]
        status='available' if sources else 'no_match'
        if not sources and skipped:raise Rejected('recall_too_large')
        from ask import input_fits
        proposed={**data,'past_sources':sources,'memory_status':status,'memory_contract':'indexed-v1','memory_coverage':'partial'}
        if not input_fits(proposed):raise Rejected('recall_too_large')
        return dict(status=status,sources=sources,contract='indexed-v1',packet=chosen,coverage='partial',notes=notes,
                    retrieval=dict(strategy='unified-evidence-v1',candidates={kind:sum(kind in c['kinds'] for c in pool)
                                   for kind in ('note','transcript','personal','retained')},budget_skipped=skipped))

    async def validate(self,manifest):
        packet=manifest['packet']
        if packet is not None and not await asyncio.to_thread(validate_selection,self.store,packet['owner'],packet,manifest.get('notes',[])):
            raise Rejected('memory_context_changed')
