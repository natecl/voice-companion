"""Transactional owner-scoped lexical candidates; no inference or recency cutoff."""
import json
import re
from admission import Rejected
import memory_time


def migrate(db):
    db.execute('BEGIN IMMEDIATE')
    try:
        db.execute('''CREATE VIRTUAL TABLE memory_passage_index USING fts5(
            owner UNINDEXED, session UNINDEXED, revision UNINDEXED, passage UNINDEXED,
            text, tokenize='unicode61')''')
        for row in db.execute('SELECT owner,payload FROM source WHERE deleted=0').fetchall():
            index_source(db,row['owner'],json.loads(row['payload']))
        db.execute('PRAGMA user_version=10')
        db.execute('COMMIT')
    except BaseException:
        db.execute('ROLLBACK');raise


def index_source(db,owner,source):
    db.executemany('INSERT INTO memory_passage_index(owner,session,revision,passage,text) VALUES(?,?,?,?,?)',
        [(owner,source['session_id'],source['revision'],p['id'],p['text']) for p in source['passages']])


def retrieve(store,owner,query,*,limit=12,exclude_session=None):
    if not isinstance(query,str) or len(query)>1000 or type(limit) is not int or not 1<=limit<=50:
        raise Rejected('invalid_query')
    terms=list(dict.fromkeys(re.findall(r'\w+',query.casefold())))[:24]
    if not terms:return []
    match=' OR '.join('"'+term+'"' for term in terms)
    now=store.clock()
    with store.transaction() as db:
        hits=db.execute('''SELECT i.session,i.revision,i.passage,rank FROM memory_passage_index i
            JOIN source s ON s.owner=i.owner AND s.session=i.session AND s.revision=i.revision
            WHERE memory_passage_index MATCH ? AND i.owner=? AND s.deleted=0
            AND (? IS NULL OR i.session!=?)
            ORDER BY rank,i.session,i.passage LIMIT ?''',(match,owner,exclude_session,exclude_session,limit)).fetchall()
        sources={};results=[]
        for hit in hits:
            session=hit['session']
            if session not in sources:
                sources[session]=json.loads(db.execute('SELECT payload FROM source WHERE owner=? AND session=?',(owner,session)).fetchone()[0])
            source=sources[session]
            passage=next(p for p in source['passages'] if p['id']==hit['passage'])
            claims=[dict(r) for r in db.execute('''SELECT c.id,c.state,c.valid_from,c.valid_until,c.replaces,c.basis,c.subject
                FROM claim c JOIN support s ON s.claim=c.id
                WHERE s.owner=? AND s.session=? AND s.revision=? AND s.passage=? ORDER BY c.id''',
                (owner,session,hit['revision'],hit['passage']))]
            for claim in claims:
                memory_time.annotate(db,owner,claim)
                store._qualify_time(claim,now)
                store._qualify_pending(db,owner,claim)
            results.append(dict(session_id=session,revision=hit['revision'],passage_id=hit['passage'],
                captured_at=source['captured_at'],timezone=source['timezone'],origin=source.get('origin','recording'),
                text=passage['text'],start=passage['start'],lifecycle=claims,lexical_score=hit['rank']))
        return results
