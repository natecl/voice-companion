"""Matched full semantic+Jev recall comparison, with exact-response reuse."""
import argparse
import asyncio
import json
from pathlib import Path
from unittest.mock import patch
from evaluate_retention import Transport
import evaluate_notes_first as screen
from indexed_recall import IndexedMemoryRecall
from notes_recall import NotesFirstRecall
from local_embeddings import LocalEmbeddings
from memory_vectors import index_source
from memory_models import fingerprint
from test_memory import source

EXTRA=[('conflict','Where is the Northstar picnic definitely taking place?', ''),
       ('paraphrase','Where can I leave my bicycle at the venue?', 'courtyard'),
       ('long','For Orion, what are the equipment return deadline and the deposit receipt number?', 'or-4821')]
BASE_SEED=screen.seed


def seed(store,credential,case,embedder):
    if case not in {c[0] for c in EXTRA}:owner=BASE_SEED(store,credential,case)
    else:
        owner=store.owner_for(credential)
        if case=='conflict':
            for session,text in [('a','Leah: I think the Northstar picnic is at Riverside Park this Saturday.'),
                                 ('b','Amir: I heard the Northstar picnic would be at the botanical garden, but the organizer has not confirmed a venue.')]:
                src=source(session,text=text);store.put_source(owner,src)
                screen.save_note(store,owner,src,dict(title='Northstar picnic',overview=dict(text=text,passages=['p1']),sections=[]))
        elif case=='paraphrase':
            src=source('cycling',text='Riders may secure their bikes in the courtyard racks behind the entrance.')
            store.put_source(owner,src)
            screen.save_note(store,owner,src,dict(title='Arrival',overview=dict(text='Cycle storage is outside behind the entrance.',passages=['p1']),sections=[]))
        else:
            src=source('orion')
            src['passages']=[dict(id=f'p{i}',start=float(i*20),duration=19.,speakers=[i%2],
                text=('The planning team reviewed the room layout, volunteer badges, seating and the refreshment table. '*3)) for i in range(40)]
            src['passages'][8]['text']='For Orion, borrowed equipment must be returned by Friday at 5 pm.'
            src['passages'][32]['text']='The Orion equipment deposit receipt number is OR-4821. This is not the event admission code.'
            store.put_source(owner,src)
            screen.save_note(store,owner,src,dict(title='Orion logistics',overview=dict(text='Equipment returns are due Friday at 5 pm; deposit receipt OR-4821.',passages=['p8','p32']),sections=[]))
    with store.connect() as db:sessions=[r[0] for r in db.execute('SELECT session FROM source WHERE owner=? AND deleted=0',(owner,))]
    for session in sessions:index_source(store,owner,session,embedder)
    return owner


class CachedTransport(Transport):
    async def call(self,request):
        key=fingerprint(request)
        if key in self.saved:
            value=self.saved[key]
            self.calls.append(dict(value,reused=True))
            (self.directory/'calls.json').write_text(json.dumps(self.calls,indent=2))
            return value['raw']
        try:raw=await super().call(request)
        except Exception as error:
            self.failure=str(error);raise
        self.saved[key]=self.calls[-1]
        return raw

    async def start(self):
        if self.process is None:await super().start()

    async def close(self):pass  # Shared across arms; the outer runner closes it once.


async def run(directory,cache,command=None,replay=None,dry=False):
    directory.mkdir(parents=True,exist_ok=False)
    embedder=LocalEmbeddings(cache,offline=True)
    transport=CachedTransport(directory,command,replay)
    for path in [screen.FIXTURES/'notes-first/calls.json',screen.FIXTURES/'retained-memory/calls.json']:
        for call in json.loads(path.read_text()):transport.saved.setdefault(fingerprint(call['request']),call)
    results=[]
    try:
        for case in screen.CASES+EXTRA:
            for strategy in ('indexed','notes'):
                factory=(lambda store,models,budget:IndexedMemoryRecall(store,models,budget,embedder,multi_source=True)) if strategy=='indexed' else (lambda store,models,budget:NotesFirstRecall(store,models,budget,embedder))
                with patch.object(screen,'CASES',[case]),patch.object(screen,'seed',lambda s,c,k:seed(s,c,k,embedder)),patch.object(screen,'NotesFirstRecall',factory),patch.object(screen,'Transport',lambda *a,**k:transport):
                    target=directory/(case[0]+'-'+strategy)
                    first_call=len(transport.calls)
                    try:
                        await screen.run(target,command=command,replay=replay,dry=dry)
                        status='complete'
                    except AssertionError as error:
                        # Preserve semantic/transport failure, do not retry or conceal it.
                        status='failed: '+str(error)[:500]
                events=json.loads((target/'results.json').read_text())[0]['events'] if (target/'results.json').exists() else []
                calls=transport.calls[first_call:]
                context=next((e for e in events if e['type']=='context'),{})
                cited=set(events[-1].get('references',[])) if events else set()
                cited_sessions={s['session_id'] for s in context.get('sources',[]) if s['id'] in cited}
                coverage_failure=case[0]=='conflict' and not {'a','b'} <= cited_sessions
                results.append(dict(case=case[0],strategy=strategy,status=status,
                    conflict_coverage_failure=coverage_failure,events=events,calls=calls))
                (target/'summary.json').write_text(json.dumps(dict(cases=1,strategy=strategy,dry=dry,
                    status=status,conflict_coverage_failure=coverage_failure,
                    manual_semantic_review_required=True),indent=2))
                (directory/'results.json').write_text(json.dumps(results,indent=2))
                if getattr(transport,'failure',None):raise RuntimeError(transport.failure)
                if any('allowance' in str(e).lower() or 'call limit' in str(e).lower() for e in events):raise RuntimeError('Budget exhausted; stop')
    finally:
        await Transport.close(transport)
    return results

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path);parser.add_argument('--cache',type=Path,required=True)
    mode=parser.add_mutually_exclusive_group(required=True);mode.add_argument('--transport');mode.add_argument('--replay',type=Path);mode.add_argument('--dry',action='store_true')
    a=parser.parse_args();asyncio.run(run(a.directory,a.cache,a.transport,a.replay,a.dry))
