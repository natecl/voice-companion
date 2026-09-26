"""Bounded, source-labelled companion context. Internal assembly, no model calls."""
import copy
import json
import re
from admission import Rejected
from companion_chat import CompanionChat
from memory_chunks import pieces
from memory_context import fingerprint,select,valid
from memory_search import STOP_WORDS
from memory_store import identifier,validate_source
from indexed_recall import memory_disabled

MAX_BYTES=12000


def size(value):return len(json.dumps(value,ensure_ascii=False).encode())


def excerpts(source,question,*,live=False):
    """Original spans only. Large recordings are explicitly partial, never fake full summaries."""
    full=[dict(session_id=source['session_id'],revision=source['revision'],passage_id=p['id'],
               text_start=0,text_end=len(p['text'])) for p in source['passages']]
    if size(source['passages'])<=3500 and len(full)<=8:return full,'complete'
    terms=set(re.findall(r'\w+',question.casefold()))-STOP_WORDS
    windows=[]
    for p,start,end in pieces(source):
        start=max(0,start-160);end=min(len(p['text']),end+160)
        score=len(terms & set(re.findall(r'\w+',p['text'][start:end].casefold())))
        windows.append((score,p['start'],start,dict(session_id=source['session_id'],revision=source['revision'],
                       passage_id=p['id'],text_start=start,text_end=end)))
    windows.sort(key=lambda value:(-value[0],-value[1] if live else value[1],-value[2] if live else value[2]))
    chosen=[w[3] for w in windows if w[0]>0][:2]
    if not chosen and live:
        chosen=[w[3] for w in sorted(windows,key=lambda value:(-value[1],-value[2]))[:1]]
    merged=[]
    positions={p['id']:i for i,p in enumerate(source['passages'])}
    for ref in sorted(chosen,key=lambda ref:(positions[ref['passage_id']],ref['text_start'])):
        if merged and ref['passage_id']==merged[-1]['passage_id'] and ref['text_start']<=merged[-1]['text_end']:
            merged[-1]['text_end']=max(merged[-1]['text_end'],ref['text_end'])
        else:merged.append(dict(ref))
    return merged,'partial' if merged else 'partial_no_match'


def live_items(source,refs):
    result=[]
    for ref in refs:
        p=next(p for p in source['passages'] if p['id']==ref['passage_id'])
        result.append(dict(ref,text=p['text'][ref['text_start']:ref['text_end']],start=p['start'],
                           speakers=p['speakers'],evidence_type='live_snapshot',origin='recording'))
    return result


def assemble(store,owner,question,*,attachment=None,live=None,past=None,memory_status='disabled',use_memory=True):
    if not isinstance(question,str) or not question.strip() or len(question)>1000:raise Rejected('invalid_question')
    if memory_status not in ('disabled','available','no_match','unavailable','context_limited'):raise Rejected('invalid_memory_status')
    if type(use_memory) is not bool:raise Rejected('invalid_memory_flag')
    exclude_past=not use_memory or memory_disabled(dict(question=question))
    if exclude_past and past is not None:raise Rejected('memory_disabled')
    chat=CompanionChat(store)
    history=dict(turns=[],history_limited=True) if exclude_past else chat.context(owner,max_bytes=3000)
    if exclude_past:memory_status='disabled'
    packets=[];groups={};metadata={}
    if attachment is not None:
        if not isinstance(attachment,dict) or set(attachment)!={'session_id','revision'}:raise Rejected('invalid_attachment')
        identifier(attachment['session_id'])
        if type(attachment['revision']) is not int:raise Rejected('invalid_attachment')
        source=store.source(owner,attachment['session_id'])
        if source is None:raise Rejected('attachment_unavailable')
        if source['revision']!=attachment['revision']:raise Rejected('attachment_changed')
        if not source['completed']:raise Rejected('attachment_not_final')
        refs,coverage=excerpts(source,question)
        packet=select(store,owner,refs);packets.append(packet);groups['attached']=packet['items']
        metadata['attached']=dict(attachment,coverage=coverage)
    snapshot=None
    if live is not None:
        validate_source(live)
        if live['completed'] or live.get('origin') is not None:raise Rejected('invalid_live_snapshot')
        if attachment and live['session_id']==attachment['session_id']:raise Rejected('recording_context_conflict')
        snapshot=copy.deepcopy(live)
        refs,coverage=excerpts(snapshot,question,live=True)
        groups['live']=live_items(snapshot,refs)
        metadata['live']=dict(session_id=snapshot['session_id'],revision=snapshot['revision'],coverage=coverage,
                              cutoff_seconds=max((p['start']+p['duration'] for p in snapshot['passages']),default=0))
    if past is not None:
        if memory_status=='disabled':raise Rejected('memory_disabled')
        if not valid(store,owner,past):raise Rejected('memory_context_changed')
        packets.append(past);groups['past']=past['items']
    while True:
        history_ids=[turn['id'] for turn in history['turns']]
        history_packet=chat.evidence(owner,history_ids)
        current_groups=dict(groups,history_evidence=history_packet['items'])
        sources=[];seen={};group_ids={}
        for name,items in current_groups.items():
            group_ids[name]=[]
            for item in items:
                # Keep live capture distinct even if an old stored passage has the same session ID.
                key=(name=='live',item['session_id'],item['revision'],item['passage_id'],item['text_start'],item['text_end'])
                if key not in seen:
                    seen[key]=f'p{len(sources)+1}';sources.append(dict(item,id=seen[key]))
                group_ids[name].append(seen[key])
        contextual_history=copy.deepcopy(history['turns'])
        for turn in contextual_history:
            mapping={}
            for citation in turn['citations']:
                ref=citation['source']
                key=(False,ref['session_id'],ref['revision'],ref['passage_id'],ref['text_start'],ref['text_end'])
                if key not in seen:raise Rejected('chat_history_changed')
                mapping[citation['id']]=seen[key]
            turn['assistant']=re.sub(r'\[\[([^\[\]]+)\]\]',lambda match:'[['+mapping[match.group(1)]+']]',turn['assistant'])
            turn['citations']=[dict(id=mapping[c['id']],source=c['source']) for c in turn['citations']]
        data=dict(contract='companion-context-v1',question=question,history=contextual_history,
                  history_limited=history['history_limited'],sources=sources,source_groups=group_ids,
                  recordings=metadata,memory_status=memory_status)
        if size(data)<=MAX_BYTES and len(sources)<=12:break
        if history['turns']:
            history['turns'].pop(0);history['history_limited']=True;continue
        raise Rejected('companion_context_too_large')
    for packet in packets+[history_packet]:
        if not valid(store,owner,packet):raise Rejected('memory_context_changed')
    return dict(data=data,packets=packets,history_ids=history_ids,
                live_snapshot=snapshot,requires_live_persistence=snapshot is not None,context_digest=fingerprint([data]))
