"""Real local embedding probe; no provider APIs. Optional fastembed environment required."""
import argparse
import json
from pathlib import Path
import resource
import time
import numpy as np
from fastembed import TextEmbedding


def run(cache):
    cases=json.loads((Path(__file__).parent/'fixtures/memory_semantic/cases.json').read_text())
    start=time.perf_counter();model=TextEmbedding('BAAI/bge-small-en-v1.5',cache_dir=str(cache),threads=2)
    load=time.perf_counter()-start
    query_start=time.perf_counter();queries=np.array(list(model.query_embed([c['query'] for c in cases])))
    query_ms=(time.perf_counter()-query_start)*1000/len(cases)
    results=[]
    for size in (10,100,1000):
        documents=[c['text'] for c in cases]+[f'Community notice {i}: pool opening hours, neighborhood traffic and library book deliveries.' for i in range(size-len(cases))]
        started=time.perf_counter();vectors=np.array(list(model.passage_embed(documents,batch_size=32)))
        elapsed=time.perf_counter()-started
        scores=queries@vectors.T
        checks={c['id']:i in np.argsort(-scores[i])[:5].tolist() for i,c in enumerate(cases)}
        results.append(dict(documents=size,index_seconds=round(elapsed,3),recall_at_5=checks))
    return dict(model='BAAI/bge-small-en-v1.5',load_seconds=round(load,3),mean_query_ms=round(query_ms,3),
                max_rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,results=results)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True);a=p.parse_args()
    result=run(a.cache);print(json.dumps(result,indent=2))
    if not all(all(r['recall_at_5'].values()) for r in result['results']):raise SystemExit(1)
