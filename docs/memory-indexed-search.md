# Indexed lexical retrieval — checkpoint 5A

Schema 10 adds an SQLite FTS5 index of original passages with owner/source/revision/passage identifiers. Source writes, revisions and deletion update the index in the same transaction. Migration rebuilds from live source payloads without inference or new learning jobs. Existing models, prompts and the installed Ask retrieval path remain unchanged; `memory_search.retrieve` is the new candidate interface awaiting hybrid retrieval/context integration.

The query is tokenized into at most 24 literal terms, parameterized and ranked by FTS5 relevance before a bounded result limit. Ownership and live source revision are checked before limiting. No recency cutoff or complete-library payload scan runs at query time. The selected original passages include lifecycle/time qualifications read in the same transaction. Ranking does not promote unresolved identity or expired facts. Results include original source origin, allowing downstream policy to distinguish authenticated text from anonymous recordings.

This is lexical candidate selection, not semantic retrieval, model ranking or final context injection. Long selected passages remain original text; bounded context packing is subsequent work. Wordless queries return empty; query and result limits are enforced. API deletion removes index rows transactionally, not a claim of physical erasure from historical SQLite pages or backups.

Implementation reference: [SQLite FTS5 documentation](https://www.sqlite.org/fts5.html), specifically literal query syntax, Unicode tokenization, ranking and transactional virtual-table writes.

## QA

Local macOS/Python 3.13.7/SQLite 3.50.4. Four focused tests passed for owner isolation, revision replacement, deletion/tombstone protection, literal query handling, expired evidence annotation, schema-9 rebuild, and retrieval of the oldest source in a real 1,000-source SQLite library. Source, database and FTS integrity checks pass. Full backend suite: 225 tests passed in approximately 9 seconds. Existing ResourceWarnings remain separate cleanup.

Before measurement the local target was p95 under 100 ms at each of 10/100/1,000 sources. `python3 evaluate_memory_search.py` runs 20 lookups per size against older relevant evidence plus newer overlapping-word distractors. The designated old source was retrieved on every lookup; measured p95 was 0.247/0.258/0.272 ms. Raw results: `Backend/fixtures/memory_search/lexical-benchmark.json`. These are synthetic lexical timings, not semantic recall, whole-answer latency or hosted performance guarantees.

Reproduce from Backend: `python3 -m unittest test_memory_search`, then `python3 evaluate_memory_search.py`. No paid provider calls, app changes, deployment or production migration. The remaining QA allowance stays $0.09 as recorded in memory-consolidation.md.
