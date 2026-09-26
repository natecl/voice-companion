"""Local lexical scale probe. Target p95 <100ms for each 10/100/1000-source library."""
import json
from pathlib import Path
import platform
import sqlite3
import tempfile
import time
from memory_store import MemoryStore
from memory_search import retrieve
from test_memory import source


def run():
    results=[]
    with tempfile.TemporaryDirectory() as folder:
        store=MemoryStore(Path(folder)/'memory.sqlite');owner=store.owner_for('synthetic')
        store.put_source(owner,source('oldest',text='Maya practices underwater hockey at the municipal pool.'))
        inserted=1
        for size in (10,100,1000):
            while inserted<size:
                store.put_source(owner,source(f'n{inserted}',text='Maya practices swimming at the neighborhood pool.'))
                inserted+=1
            durations=[]
            for _ in range(20):
                start=time.perf_counter();hits=retrieve(store,owner,'underwater hockey',limit=8)
                durations.append((time.perf_counter()-start)*1000)
                assert [h['session_id'] for h in hits]==['oldest']
            p95=sorted(durations)[18]
            results.append(dict(sources=size,target_recalled=True,p95_ms=round(p95,3),target_met=p95<100))
    return dict(python=platform.python_version(),sqlite=sqlite3.sqlite_version,platform=platform.system(),
                candidate_method='lexical_only',results=results)

if __name__=='__main__':print(json.dumps(run(),indent=2))
