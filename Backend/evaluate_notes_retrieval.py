"""Offline candidate/evidence comparison, NOT a production retrieval replacement.

Uses exact saved notes responses. No network transport or paid fallback exists.
Both candidates use lexical matching; semantic search, Jev ranking and new answer
quality are deliberately unmeasured. Outputs preserve misses, not just passes.
"""
import argparse
import asyncio
import copy
import json
from pathlib import Path
import re
import sqlite3

from admission import Rejected
from evaluate_recording_notes import run as replay_notes
import memory_context
import memory_hybrid
from memory_search import STOP_WORDS
from memory_store import MemoryStore
from recording_notes import RecordingNotes

FIXTURES = Path(__file__).parent / 'fixtures'
# Expectations specified from original transcripts, before inspecting retrieval.
CASES = [
    ('conversation', 'When are Alex and Jordan meeting?', ['p1', 'p2']),
    ('conversation', 'Who will send the agenda?', ['p2']),
    ('lecture', 'What explains ice cream sales and swimming?', ['p2']),
    ('lecture', 'Was homework assigned?', ['p3']),
    ('appointment', 'Does the dog have a confirmed diagnosis?', ['p1', 'p3']),
    ('reflection', 'Is walking before class a decided routine?', ['p2']),
    ('correction', 'Where will Cedar meet?', ['p3']),
]


def bullets(notes):
    return [notes['overview']] + [item for section in notes['sections'] for item in section['items']]


def notes_candidates(store, owner, query, *, enabled=True):
    """Evaluation-only FTS index rebuilt from revision-valid notes on each call.

    At most three notes, then twelve distinct cited original passages. A real
    integration would need durable indexing, retrieval ranking and a byte budget.
    """
    if not enabled:
        return [], []
    terms = [t for t in dict.fromkeys(re.findall(r'\w+', query.casefold())) if t not in STOP_WORDS][:24]
    if not terms:
        return [], []
    with store.connect() as db:
        sessions = [r[0] for r in db.execute('SELECT session FROM source WHERE owner=? AND deleted=0 ORDER BY session', (owner,))]
    notes = RecordingNotes(store)
    documents = {}
    with sqlite3.connect(':memory:') as index:
        index.execute("CREATE VIRTUAL TABLE notes_index USING fts5(session UNINDEXED,text,tokenize='unicode61')")
        for session in sessions:
            value = notes.read(owner, session)
            if not value or value['state'] != 'ready':
                continue
            documents[session] = value
            payload = value['notes']
            text = '\n'.join([payload['title']] + [b['text'] for b in bullets(payload)])
            index.execute('INSERT INTO notes_index VALUES(?,?)', (session, text))
        hits = index.execute('SELECT session FROM notes_index WHERE notes_index MATCH ? ORDER BY rank,session LIMIT 3',
                             (' OR '.join('"'+t+'"' for t in terms),)).fetchall()
    selected = [dict(session_id=session, **documents[session]) for (session,) in hits]
    refs = [dict(session_id=n['session_id'], revision=n['revision'], passage_id=p)
            for n in selected for p in dict.fromkeys(p for b in bullets(n['notes']) for p in b['passages'])]
    return selected, memory_context.select(store, owner, refs, limit=12)['items']


def score(items, case, expected):
    found = {p['passage_id'] for p in items if p['session_id'] == 'notes-'+case}
    return dict(required_present=set(expected) <= found,
                missing=sorted(set(expected)-found),
                references=[f"{p['session_id']}:{p['passage_id']}" for p in items],
                evidence_text_bytes=sum(len(p['text'].encode()) for p in items))


async def run(directory):
    directory.mkdir(parents=True, exist_ok=False)
    await replay_notes(directory/'notes', replay=FIXTURES/'recording-notes/calls.json')
    store = MemoryStore(directory/'notes/notes.sqlite')
    owner = store.owner_for('notes-qa')
    rows = []
    for case, query, expected in CASES:
        baseline = memory_hybrid.retrieve(store, owner, query, limit=12)['packet']['items']
        notes, expanded = notes_candidates(store, owner, query)
        rows.append(dict(case=case, question=query, required_passages=expected,
                         current_lexical=score(baseline, case, expected),
                         notes_expanded=score(expanded, case, expected),
                         selected_notes=[n['notes'] for n in notes],
                         notes_text_bytes=sum(len(json.dumps(n['notes']).encode()) for n in notes)))
    # Hand-authored compression control, explicitly NOT another model result.
    # Keep a valid topic overview while omitting one example and its source link.
    note_store = RecordingNotes(store)
    with store.transaction() as db:
        db.execute("UPDATE recording_notes SET state='outdated' WHERE owner=? AND session='notes-lecture'", (owner,))
    note_store.enqueue(owner, 'notes-lecture', 1)
    job = note_store.claim(owner, 'notes-lecture')
    note_store.complete(job, dict(title='Correlation and Causation',
        overview=dict(text='Correlation describes variables changing together.', passages=['p1']), sections=[]))
    detail_query = 'What explains ice cream sales and swimming?'
    direct = memory_hybrid.retrieve(store, owner, detail_query)['packet']['items']
    _, compressed = notes_candidates(store, owner, detail_query)
    assert score(direct, 'lecture', ['p2'])['required_present']
    assert not score(compressed, 'lecture', ['p2'])['required_present']
    # Finding the right note by its topic still cannot expand an uncited example.
    _, topic = notes_candidates(store, owner, 'correlation')
    assert any(p['session_id'] == 'notes-lecture' for p in topic)
    assert not score(topic, 'lecture', ['p2'])['required_present']
    # Real owner, opt-out, source-version, citation and deletion paths.
    other = store.owner_for('different-owner')
    assert notes_candidates(store, other, 'Cedar') == ([], [])
    assert notes_candidates(store, owner, 'Cedar', enabled=False) == ([], [])
    before = notes_candidates(store, owner, 'Cedar')[1]
    assert before and len(memory_context.select(store, owner, before)['items']) == len(before)
    source = copy.deepcopy(json.loads((FIXTURES/'recording-notes/cases.json').read_text())[-1]['source'])
    source['revision'] = 2
    store.put_source(owner, source)
    assert notes_candidates(store, owner, 'Cedar') == ([], [])
    assert memory_context.select(store, owner, before)['items'] == []
    store.delete_source(owner, 'notes-conversation')
    try:
        RecordingNotes(store).read(owner, 'notes-conversation')
        raise AssertionError('Deleted notes still readable')
    except Rejected as error:
        assert str(error) == 'source_unavailable'
    assert not any(p['session_id']=='notes-conversation' for p in notes_candidates(store, owner, 'agenda')[1])
    report = dict(new_paid_calls=0, cases=rows,
                  compression_control=dict(provenance='Hand-authored omission, not generated output',
                      direct_transcript_finds_detail=True, notes_detail_query_misses=True,
                      topic_note_citations_also_omit_detail=True),
                  current_lexical_required_hits=sum(r['current_lexical']['required_present'] for r in rows),
                  notes_expanded_required_hits=sum(r['notes_expanded']['required_present'] for r in rows),
                  controls=dict(owner_isolation=True, opt_out=True, original_passages_open=True,
                                stale_notes_excluded=True, stale_citations_invalid=True, deleted_notes_unavailable=True),
                  limitations=['Five short synthetic recordings; seven lexical queries, no statistical generalization.',
                               'Baseline has no semantic embedding or final model ranking; not the full deployed harness.',
                               'Notes route expands all citations from up to three notes, capped at twelve passages.',
                               'No new Jev retrieval, new answers, latency or inference cost measured.',
                               'No learned claims seeded in matched corpus; retention replay is a separate lifecycle baseline.'])
    (directory/'results.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'cases'}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    asyncio.run(run(parser.parse_args().directory))
