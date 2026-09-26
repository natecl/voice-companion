"""Actual pinned local model through durable queue and hybrid retrieval; no API calls."""
import argparse
import asyncio
import json
from pathlib import Path
import tempfile
from local_embeddings import LocalEmbeddings
from memory_store import MemoryStore
from memory_indexing import IndexWorker,coverage
from memory_hybrid import retrieve
from test_memory import source


async def run(cache):
    model=LocalEmbeddings(cache)
    cases=json.loads((Path(__file__).parent/'fixtures/memory_semantic/cases.json').read_text())
    with tempfile.TemporaryDirectory() as directory:
        store=MemoryStore(Path(directory)/'memory.sqlite',embedding_model=model.contract)
        owner=store.owner_for('qa')
        class Admission:
            def active_credentials(self):return ['qa']
        worker=IndexWorker(store,model,Admission())
        for case in cases:store.put_source(owner,source(case['id'],text=case['text']))
        before=coverage(store,owner,model.contract)
        while await worker.step():pass
        after=coverage(store,owner,model.contract)
        checks={case['id']:case['id'] in [i['session_id'] for i in retrieve(store,owner,case['query'],embedder=model,limit=3)['packet']['items']] for case in cases}
        store.delete_source(owner,cases[0]['id'])
        deleted=cases[0]['id'] not in [i['session_id'] for i in retrieve(store,owner,cases[0]['query'],embedder=model)['packet']['items']]
        print(json.dumps(dict(model=model.contract,before=before,after=after,checks=checks,deleted_absent=deleted),indent=2))
        assert before=={'queued':6} and after=={'done':6} and all(checks.values()) and deleted

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--cache',type=Path,required=True)
    asyncio.run(run(p.parse_args().cache))
