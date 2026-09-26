"""Rank fusion for discovery; final answer relevance selection remains separate."""
from admission import Rejected
import memory_context
import memory_search
import memory_vectors
import memory_retention


def retrieve(store, owner, query, *, embedder=None, use_memory=True, limit=12, exclude_session=None):
    if type(use_memory) is not bool or type(limit) is not int or not 1 <= limit <= 50:
        raise Rejected('invalid_query')
    if not use_memory:
        return dict(status='disabled', packet=memory_context.select(store, owner, []))
    lexical = memory_search.retrieve(store, owner, query, limit=50, exclude_session=exclude_session)
    semantic = memory_vectors.retrieve(store, owner, query, embedder, limit=50,
                                      exclude_session=exclude_session) if embedder else []
    scores = {}; refs = {}
    retained = memory_retention.retrieve(store, owner, query, limit=50, exclude_session=exclude_session)
    for hits in (lexical, semantic, retained):
        visited = set()
        for rank, hit in enumerate(hits, 1):
            key = (hit['session_id'], hit['revision'], hit['passage_id'])
            if key in visited: continue
            visited.add(key)
            scores[key] = scores.get(key, 0.) + 1 / (60 + rank)
            # Keep the highest-ranked contextual window from the semantic path.
            if key not in refs or 'text_start' in hit: refs[key] = hit
    ranked = [refs[key] for key in sorted(scores, key=lambda key: (-scores[key], key))]
    return dict(status='hybrid' if embedder else 'lexical_only',
                packet=memory_context.select(store, owner, ranked[:100], limit=limit))
