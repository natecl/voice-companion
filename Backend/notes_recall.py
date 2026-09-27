"""Notes-first recall candidate. One bounded Jev call; original evidence answers."""
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


def collect(store, owner, query, exclude_session=None, embedder=None):
    """Reserve space for each route: four notes, four fallback, two personal, two retained."""
    pool=[]
    for note in notes_search.retrieve(store,owner,query,limit=4,exclude_session=exclude_session):
        refs=[dict(session_id=note['session_id'],revision=note['revision'],passage_id=p) for p in note['passages']]
        packet=packet_for(store,owner,refs)
        if len(packet['items'])==len(refs):
            pool.append(dict(kind='note',text='Derived note; original passages verify it:\n'+note['text'],packet=packet,note=note))
    fallback=memory_hybrid.retrieve(store,owner,query,embedder=embedder,exclude_session=exclude_session,limit=12)['packet']['items']
    for item in [p for p in fallback if 'retained_claim_id' not in p][:4]:
        if len(item['text'])>1800:
            terms=[t for t in re.findall(r'\w+',query.casefold()) if t not in STOP_WORDS]
            positions=[item['text'].casefold().find(t) for t in terms if t in item['text'].casefold()]
            start=max(0,(min(positions) if positions else 0)-300)
            end=min(len(item['text']),start+1800)
            ref={**item,'text_start':item['text_start']+start,'text_end':item['text_start']+end}
            packet=packet_for(store,owner,[ref])
        else:packet=packet_for(store,owner,[item])
        if packet['items']:
            pool.append(dict(kind='transcript',text=packet['items'][0]['text'],packet=packet))
    terms=' '.join(t for t in re.findall(r'\w+',query.casefold()) if t not in STOP_WORDS)
    if terms:
        for claim in store.search(owner,terms,profile_only=True,limit=2):
            refs=[dict(session_id=s['session'],revision=s['revision'],passage_id=s['passage'])
                  for s in claim['sources'] if s['session']!=exclude_session]
            packet=packet_for(store,owner,refs[:8])
            if packet['items'] and len(claim['text'])<=1800:
                pool.append(dict(kind='personal',text='Supported personal context:\n'+claim['text'],packet=packet))
    for ref in memory_retention.retrieve(store,owner,query,limit=2,exclude_session=exclude_session):
        packet=packet_for(store,owner,[ref])
        if packet['items'] and len(packet['items'][0]['text'])<=1800:
            pool.append(dict(kind='retained',text=packet['items'][0]['text'],packet=packet))
    return pool


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
            for key in ranking['order']:
                if key=='none' or count==3:break
                candidate=pool[int(key[1:])]
                candidate_notes=[candidate['note']] if 'note' in candidate else []
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
                    retrieval=dict(strategy='notes-first-v1',candidates={kind:sum(c['kind']==kind for c in pool)
                                   for kind in ('note','transcript','personal','retained')},budget_skipped=skipped))

    async def validate(self,manifest):
        packet=manifest['packet']
        if packet is not None and not await asyncio.to_thread(validate_selection,self.store,packet['owner'],packet,manifest.get('notes',[])):
            raise Rejected('memory_context_changed')
