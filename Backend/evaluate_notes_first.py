"""Six frozen companion socket cases. Operator transport enforces paid caps."""
import argparse
import asyncio
import itertools
import json
from pathlib import Path
import uuid
from unittest.mock import patch
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from admission import Admission,Rejected
from companion_service import CompanionService
from companion_chat import CompanionChat
from evaluate_retention import Transport,TransportBudget
from memory_models import fingerprint
from memory_store import MemoryStore
from notes_generation import request as notes_request
from notes_recall import NotesFirstRecall
from recording_notes import RecordingNotes
from test_memory import source,candidate

FIXTURES=Path(__file__).parent/'fixtures'
CASES=[('correction','Where will Cedar meet?', 'garden pavilion'),
       ('omitted','What explains ice cream sales and swimming?', 'weather'),
       ('appointment','Does the dog have a confirmed diagnosis, and should its food change?', 'diagnos'),
       ('personal','What does my daughter Maya enjoy, and do you know whether I train for marathons?', 'swim'),
       ('change','Where does Project Birch meet now?', 'community center'),
       ('retained','Where does Project Juniper meet now, and can I open the original recording?', 'community center')]


def save_note(store,owner,src,data):
    notes=RecordingNotes(store);notes.enqueue(owner,src['session_id'],src['revision'])
    notes.complete(notes.claim(owner,src['session_id']),data)


def seed(store,credential,case):
    if case=='retained':
        state=json.loads((FIXTURES/'retained-memory/state.json').read_text())
        with store.transaction() as db:
            db.execute('PRAGMA defer_foreign_keys=ON')
            allowed={'owner','source','claim','support','memory_entity','memory_mention','memory_identity_link','memory_identity_support','memory_correction','memory_correction_link','claim_relation_proposal','memory_fact_evidence','retained_recording'}
            for table,rows in state.items():
                if table not in allowed:raise ValueError('Unexpected fixture table')
                for row in rows:
                    columns=[r[1] for r in db.execute('PRAGMA table_info('+table+')')]
                    assert set(row)==set(columns)
                    db.execute('INSERT INTO '+table+' VALUES('+','.join('?' for _ in columns)+')',[row[c] for c in columns])
        return store.owner_for(credential,existing_owner=state['owner'][0]['id'])
    owner=store.owner_for(credential)
    if case in ('correction','omitted','appointment'):
        name='lecture' if case=='omitted' else case
        src=next(c['source'] for c in json.loads((FIXTURES/'recording-notes/cases.json').read_text()) if c['id']==name)
        store.put_source(owner,src)
        calls=json.loads((FIXTURES/'recording-notes/calls.json').read_text())
        note=next(c['response']['data'] for c in calls if fingerprint(c['request'])==fingerprint(notes_request(store.source(owner,src['session_id']))))
        if case=='omitted':note=dict(title='Correlation and Causation',overview=dict(text='Correlation describes variables changing together.',passages=['p1']),sections=[])
        save_note(store,owner,src,note)
    elif case=='personal':
        src=dict(source('personal',text='My daughter Maya enjoys swimming.'),origin='personal_text')
        store.put_source(owner,src)
        store.commit_claims(store.claim_job(owner),[dict(candidate('My daughter Maya enjoys swimming.'),subject='Maya',kind='fact',profile_link=True)])
        store.put_source(owner,source('anonymous',text='I train for marathons.'))
    else:
        src=source('birch-old',text='Project Birch meets at the library.')
        store.put_source(owner,src);store.commit_claims(store.claim_job(owner),[dict(candidate('Project Birch meets at the library.'),subject='Birch')])
        old=store.search(owner)[0]['id']
        save_note(store,owner,src,dict(title='Project Birch',overview=dict(text='Project Birch meets at the library.',passages=['p1']),sections=[]))
        store.put_source(owner,source('birch-new',text='Project Birch now meets at the community center instead of the library.'))
        store.commit_claims(store.claim_job(owner),[dict(candidate('Project Birch meets at the community center.',relation='supersedes',target=old),subject='Birch')])
    return owner


async def run(directory,command=None,replay=None,dry=False):
    directory.mkdir(parents=True,exist_ok=False)
    transport=Transport(directory,command,replay)
    results=[]
    try:
        if not dry:await transport.start()
        for index,(case,query,required) in enumerate(CASES):
            store=MemoryStore(directory/(case+'.sqlite'),clock=lambda:1790461403.,personal_learning=True,retain_recording_memories=True)
            ledger=Admission(directory/(case+'-usage.sqlite'),total_microusd=3000,limits={'ask':(3000,3000,1)})
            credential,token=ledger.enroll()
            counter=itertools.count(100)
            with patch('uuid.uuid4',side_effect=lambda:uuid.UUID(int=next(counter))):owner=seed(store,credential,case)
            if dry:
                from test_notes_recall import Judge
                class Answers:
                    async def stream(self,data):
                        yield dict(type='delta',text='Fixture plumbing only.')
                        yield dict(type='completed')
                judge=Judge();answers=Answers()
            else:judge=answers=transport
            recall=NotesFirstRecall(store,judge,TransportBudget())
            service=CompanionService(ledger,store,answers,recall)
            async with serve(service.handle,'127.0.0.1',0,max_size=64000) as server:
                url=f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/companion'
                async with connect(url,additional_headers={'Authorization':'Bearer '+token}) as socket:
                    await socket.send(json.dumps(dict(operation='ask',question_id=case,question=query,memory=True,attachment=None,live=None)))
                    events=[json.loads(raw) async for raw in socket]
            results.append(dict(case=case,question=query,events=events))
            (directory/'results.json').write_text(json.dumps(results,indent=2))
            assert events[-1].get('saved') is True,events
            context=next(e for e in events if e['type']=='context')
            assert context['memory_status']=='available',context
            answer=''.join(e['text'] for e in events if e['type']=='delta')
            print(json.dumps(dict(case=case,answer=answer)),flush=True)
            if not dry:assert required in answer.casefold(),answer
            page=CompanionChat(MemoryStore(store.path,clock=lambda:1790461403.)).page(owner)
            assert len(page['turns'])==1 and page['turns'][0]['state']=='complete'
            if not dry:
                assert page['turns'][0]['citations'], 'Answers must cite supplied evidence'
                for citation in page['turns'][0]['citations']:
                    chat=CompanionChat(store)
                    if case=='retained':
                        try:chat.citation(owner,case,citation['id'])
                        except Rejected as error:assert str(error)=='source_unavailable'
                        else:raise AssertionError('Deleted transcript must not open')
                    else:
                        evidence=chat.citation(owner,case,citation['id'])
                        assert evidence['text'] and evidence['evidence_type']=='original_source'
            ledger.close()
        (directory/'summary.json').write_text(json.dumps(dict(cases=6,new_paid_calls=12 if command else 0,
             dry=dry,manual_semantic_review_required=not dry),indent=2))
    finally:await transport.close()

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--transport');group.add_argument('--replay',type=Path);group.add_argument('--dry',action='store_true')
    args=parser.parse_args();asyncio.run(run(args.directory,args.transport,args.replay,args.dry))
