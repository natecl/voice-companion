"""Frozen ranker probe: each answer-bearing passage must rank first among topical distractors.

Irrelevant-query scores are diagnostics, not permission to invent a calibrated rejection threshold.
Target: each 12-passage ranking under 500 ms on local CPU, excluding initial model load.
"""
import argparse
import json
from pathlib import Path
import resource
import time
from local_reranker import LocalReranker


def run(cache):
    root = Path(__file__).parent/'fixtures'
    positives = json.loads((root/'memory_semantic/cases.json').read_text())
    cases = json.loads((root/'memory_reranking/cases.json').read_text())
    start = time.perf_counter(); model = LocalReranker(cache); loaded = time.perf_counter()-start
    texts = [case['text'] for case in positives] + cases['distractors']
    checks = []; negative = []
    for expected, case in enumerate(positives):
        start = time.perf_counter(); ranked, scores = model.rank(case['query'], texts)
        checks.append(dict(id=case['id'], rank=ranked.index(expected)+1,
                           ms=round((time.perf_counter()-start)*1000, 3), scores=scores))
    for query in cases['irrelevant_queries']:
        ranked, scores = model.rank(query, texts)
        negative.append(dict(query=query, top_index=ranked[0], top_score=scores[ranked[0]]))
    result = dict(model=model.contract, load_seconds=round(loaded, 3), checks=checks,
                  irrelevant_queries=negative, peak_rss_platform_units=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    print(json.dumps(result, indent=2))
    assert all(c['rank']==1 and c['ms']<500 for c in checks)

if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cache',type=Path,required=True)
    run(parser.parse_args().cache)
