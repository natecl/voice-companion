"""Reuse local discovery, original evidence and correction expansion without paid ranking."""
import json
import memory_context
import memory_related
from admission import Rejected
from notes_recall import collect, validate_selection
from proactive_policy import cutoff
from proactive_models import bounded


def recent_window(passages, limit=5000):
    """Bound UTF-8 JSON bytes, keeping original passage IDs and character offsets."""
    current=[]
    for p in reversed(passages[-8:]):
        item=dict(p)
        if len(json.dumps([item]+current,ensure_ascii=False).encode())<=limit:
            current.insert(0,item)
            continue
        if current:break
        # One provider utterance can span minutes. Keep its recent tail, with
        # explicit clipping metadata and exact source offsets for citations.
        low,high=0,len(p['text'])
        while low<high:
            mid=(low+high)//2
            trial=dict(item,text=p['text'][mid:],text_start=mid,text_end=len(p['text']),truncated=True)
            if len(json.dumps([trial],ensure_ascii=False).encode())<=limit:high=mid
            else:low=mid+1
        offset=low
        # Avoid starting in the middle of a word when a boundary is available.
        while offset<len(p['text']) and offset>0 and not p['text'][offset-1].isspace():offset+=1
        if offset<len(p['text']):
            current=[dict(item,text=p['text'][offset:],text_start=offset,text_end=len(p['text']),truncated=True)]
        break
    return current


def prepare(store,owner,live,previous=(),embedder=None,allowed_sources=None):
    digest = cutoff(live)
    current = recent_window(live['passages'])
    if not current: return None
    query = ' '.join(p['text'] for p in current)[-1000:]
    pool = collect(store,owner,query,exclude_session=live['session_id'],embedder=embedder)
    if allowed_sources is not None:
        pool=[c for c in pool if all(i["session_id"] in allowed_sources for i in c["packet"]["items"])]
    if not pool: return None
    items=[];notes=[]
    for candidate in pool[:4]:
        if not validate_selection(store,owner,candidate['packet'],candidate['notes']):
            raise Rejected('memory_context_changed')
        for item in candidate['packet']['items']:
            if item not in items: items.append(item)
        notes.extend(candidate['notes'])
    packet = dict(version='selected-evidence-v1',owner=owner,items=items,digest=memory_context.fingerprint(items))
    packet = memory_related.expand(store,owner,packet,max_items=8)
    if allowed_sources is not None and any(i["session_id"] not in allowed_sources for i in packet["items"]):return None
    # Do not trim away correction context to fit. Oversize attempts stay quiet.
    if any(i['session_id'] == live['session_id'] for i in packet['items']):
        raise Rejected('proactive_active_source_dependency')
    state = dict(current=dict(captured_at=live['captured_at'],timezone=live['timezone'],passages=current,
        speaker_identity='unidentified_recording_speakers'),
        sources=[dict(id=f'm{i}',**item) for i,item in enumerate(packet['items'],1)],
        previous=list(previous)[-4:])
    bounded(state)
    if not validate_selection(store,owner,packet,notes): raise Rejected('memory_context_changed')
    return dict(state=state,packet=packet,notes=notes,cutoff=digest)
