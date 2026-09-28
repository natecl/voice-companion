"""Reuse local discovery, original evidence and correction expansion without paid ranking."""
import json
import memory_context
import memory_related
from admission import Rejected
from notes_recall import collect, validate_selection
from proactive_policy import cutoff
from proactive_models import bounded


def prepare(store,owner,live,previous=(),embedder=None):
    digest = cutoff(live)
    current = live['passages'][-8:]
    if not current: return None
    if len(json.dumps(current,ensure_ascii=False).encode()) > 5000:
        raise Rejected('proactive_live_context_too_large')
    query = ' '.join(p['text'] for p in current)[-1000:]
    pool = collect(store,owner,query,exclude_session=live['session_id'],embedder=embedder)
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
