"""Candidate-only execution of the frozen cases plus an abstention check; no automatic paid fallback.

Dry mode exercises socket/storage/source composition with explicitly synthetic
model responses. Replay uses exact saved requests; changed requests require a
separately authorized bounded transport. Neither dry mode nor replay is live QA.
"""
import argparse
import asyncio
import json
from pathlib import Path
from unittest.mock import patch
import evaluate_notes_first as screen
from evaluate_matched_recall import seed as matched_seed, EXTRA, CachedTransport
from memory_vectors import index_source
from test_memory import source
from evaluate_retention import Transport
from local_embeddings import LocalEmbeddings
from notes_recall import NotesFirstRecall


ABSTENTION=('abstention','Do these notes give the concert ticket price?', '')


def seed(store,credential,case,embedder):
    if case!='abstention':return matched_seed(store,credential,case,embedder)
    owner=store.owner_for(credential)
    src=source('concert',text='The concert is outdoors at the riverside amphitheatre. Doors open at six.')
    store.put_source(owner,src)
    screen.save_note(store,owner,src,dict(title='Concert',overview=dict(text=src['passages'][0]['text'],passages=['p1']),sections=[]))
    index_source(store,owner,'concert',embedder)
    return owner


async def run(directory,cache,*,replay=None,command=None,dry=False):
    directory.mkdir(parents=True,exist_ok=False)
    embedder=LocalEmbeddings(cache,offline=True)
    transport=CachedTransport(directory,command,replay)
    results=[]
    try:
        for case in screen.CASES+EXTRA+[ABSTENTION]:
            with patch.object(screen,'CASES',[case]),patch.object(screen,'seed',lambda s,c,k:seed(s,c,k,embedder)), \
                 patch.object(screen,'NotesFirstRecall',lambda s,m,b:NotesFirstRecall(s,m,b,embedder)), \
                 patch.object(screen,'Transport',lambda *a,**k:transport):
                target=directory/case[0]
                await screen.run(target,command=command,replay=replay,dry=dry)
            result=json.loads((target/'results.json').read_text())[0]
            context=next(e for e in result['events'] if e['type']=='context')
            sessions={s['session_id'] for s in context['sources']}
            if case[0]=='conflict':assert {'a','b'}<=sessions,'Competing account missing'
            results.append(result)
            (directory/'results.json').write_text(json.dumps(results,indent=2))
        (directory/'summary.json').write_text(json.dumps(dict(cases=len(results),dry=dry,
            evidence='synthetic response plumbing' if dry else 'provider-response execution',
            semantic_review_required=True),indent=2))
    except BaseException as error:
        (directory/'failure.json').write_text(json.dumps(dict(error=str(error),transport=getattr(transport,'failure',None))))
        raise
    finally:await Transport.close(transport)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('directory',type=Path)
    parser.add_argument('--cache',type=Path,required=True)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--dry',action='store_true');mode.add_argument('--replay',type=Path);mode.add_argument('--transport')
    a=parser.parse_args();asyncio.run(run(a.directory,a.cache,replay=a.replay,command=a.transport,dry=a.dry))
