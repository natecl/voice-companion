"""Real local model -> SQLite -> retrieval proof. Target max query latency <100ms at 1000 sources."""
import argparse
import json
from pathlib import Path
import tempfile
import time
from local_embeddings import LocalEmbeddings
from memory_store import MemoryStore
from memory_vectors import index_source,retrieve
from test_memory import source


def run(cache):
    model=LocalEmbeddings(cache)
    cases=json.loads((Path(__file__).parent/'fixtures/memory_semantic/cases.json').read_text())
    results=[]
    with tempfile.TemporaryDirectory() as folder:
        store=MemoryStore(Path(folder)/'memory.sqlite');owner=store.owner_for('semantic-qa');inserted=0
        for size in (10,100,1000):
            while inserted<size:
                if inserted<len(cases):session,text=cases[inserted]['id'],cases[inserted]['text']
                else:session,text=f'notice{inserted}',f'Community notice {inserted}: pool hours, traffic and library deliveries.'
                store.put_source(owner,source(session,text=text));index_source(store,owner,session,model);inserted+=1
            checks={};latency=[]
            for case in cases:
                start=time.perf_counter();hits=retrieve(store,owner,case['query'],model,limit=5)
                latency.append((time.perf_counter()-start)*1000)
                checks[case['id']]=case['id'] in [h['session_id'] for h in hits]
                for hit in hits:
                    original=store.source(owner,hit['session_id'])['passages'][0]['text']
                    assert original[hit['text_start']:hit['text_end']]==hit['text']
            results.append(dict(sources=size,recall_at_5=checks,max_query_ms=round(max(latency),3)))
        other=store.owner_for('long-source')
        text=('The room was quiet and the windows were open. '*150)+'My canoe is turquoise and stored beside the river.'
        store.put_source(other,source('long',text=text));out=index_source(store,other,'long',model)
        hits=retrieve(store,other,'What color is my canoe?',model,limit=3)
        long_ok=any('My canoe is turquoise' in h['text'] for h in hits)
        assert all(h['session_id']=='long' for h in hits)
        cached=index_source(store,other,'long',model)['status']=='cached'
        store.delete_source(other,'long');deleted=not retrieve(store,other,'canoe',model)
    result=dict(model=model.contract,results=results,long_source_pieces=out['pieces'],late_fact_retrieved=long_ok,
                cache_reused=cached,deleted_absent=deleted)
    print(json.dumps(result,indent=2))
    assert all(all(r['recall_at_5'].values()) and r['max_query_ms']<100 for r in results)
    assert long_ok and cached and deleted

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);a=p.parse_args();run(a.cache)
