"""Offline behavior fixture: actual writer and storage, exact provider replay only."""
import json
from pathlib import Path
from evaluate_source_verification import Transport, TransportBudget, ROOT
from memory_evidence_writer import EvidenceWriter
from memory_store import MemoryStore
from companion_chat import CompanionChat
from companion_context import assemble
import memory_context
import memory_hybrid
import memory_related

async def seed(store, owner, directory):
    directory.mkdir(parents=True,exist_ok=True)
    models=Transport('false',directory,[ROOT/'source-verification/initial-calls.json',ROOT/'source-verification/verified-calls.json'])
    writer=EvidenceWriter(store,models,TransportBudget(),chunking=True,semantic_boundaries=True,
        expiry=True,consolidation=True,independent_source_verification=True)
    calls=json.loads((ROOT/'subject-continuity/calls.json').read_text())
    sources=[json.loads(calls[i]['request']['input']) for i in (0,3)]
    for source in sources:source.pop('origin',None)
    try:
        # Delete the original BEFORE learning its correction: same model requests
        # still resolve from the previously committed exact supporting excerpts.
        store.put_source(owner,sources[0]);await writer.process_next(owner)
        store.delete_source(owner,sources[0]['session_id'])
        store.put_source(owner,sources[1]);await writer.process_next(owner)
        store.delete_source(owner,sources[1]['session_id'])
        reopened=MemoryStore(store.path)
        packet=memory_related.expand(reopened,owner,memory_hybrid.retrieve(reopened,owner,'Where does Project Juniper meet?')['packet'])
        context=assemble(reopened,owner,'Where does Project Juniper meet?',past=packet,memory_status='available')
        item=next(i for i in context['data']['sources'] if 'community center' in i['text'] and i['lifecycle'][0]['state']=='active')
        chat=CompanionChat(reopened);chat.start(owner,'retention-fixture','Where does Project Juniper meet?')
        answer='From what I remember, Project Juniper now meets at the community center. [['+item['id']+']]'
        chat.complete(owner,'retention-fixture',answer,packets=context['packets'],citations=[dict(id=item['id'],source=item)])
        page=CompanionChat(MemoryStore(store.path)).page(owner)
        assert page['turns'][0]['state']=='complete'
        assert all(i['evidence_type']=='retained_memory' for i in packet['items'])
        assert memory_context.valid(reopened,owner,packet)
        report=dict(provider_mode='exact saved responses; answer injected for UI/storage QA',paid_calls=0,
            source_available=[reopened.source(owner,s['session_id']) is not None for s in sources],
            claims=[dict(text=c['text'],state=c['state'],identity_status=c['identity_status']) for c in reopened.search(owner,historical=True)],
            retained_answer=page['turns'][0]['answer'],references=page['turns'][0]['citations'],
            answer_reopened=page['turns'][0]['state'],selected_evidence_valid=True)
        (directory/'report.json').write_text(json.dumps(report,indent=2))
        return report
    finally:models.close()

if __name__=='__main__':
    import asyncio
    import sys
    directory=Path(sys.argv[1]);directory.mkdir(parents=True,exist_ok=False)
    store=MemoryStore(directory/'memory.sqlite',retain_recording_memories=True)
    print(json.dumps(asyncio.run(seed(store,store.owner_for('retention-qa'),directory)),indent=2))
