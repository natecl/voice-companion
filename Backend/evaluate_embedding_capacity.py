"""Offline Linux capacity proof; run in a 512 MiB, 0.5 CPU container, without swap."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import time
from local_embeddings import LocalEmbeddings


def run(cache):
    model=LocalEmbeddings(cache,offline=True)
    text=('Maya likes swimming and has practice on Tuesday. Alex prefers afternoon appointments. '*40)[:1500]
    started=time.monotonic()
    with ThreadPoolExecutor(2) as pool:
        job=pool.submit(model.passages,[text]*32)
        latencies=[]
        for _ in range(5):
            time.sleep(.2)
            before=time.monotonic()
            assert len(model.query('What does Maya enjoy?'))==384
            latencies.append(time.monotonic()-before)
        vectors=job.result(timeout=120)
    assert len(vectors)==32 and all(len(v)==384 for v in vectors)
    peak=int(Path('/sys/fs/cgroup/memory.peak').read_text())
    result=dict(passages=32,concurrent_queries=5,elapsed_seconds=round(time.monotonic()-started,3),
        query_seconds=[round(t,3) for t in latencies],peak_bytes=peak,
        memory_events=Path('/sys/fs/cgroup/memory.events').read_text())
    print(json.dumps(result,indent=2),flush=True)
    assert peak<448*1024*1024, 'Insufficient service headroom'
    assert max(latencies)<2, 'Insufficient headroom under the three-second recall deadline'


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cache',type=Path,required=True)
    run(parser.parse_args().cache)
