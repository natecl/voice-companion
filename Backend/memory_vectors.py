"""Versioned source-local embedding cache. Explicit indexing; no automatic model calls."""
import json
import math
import struct
from admission import Rejected

SCHEMA='''BEGIN IMMEDIATE;
CREATE TABLE memory_embedding(
 owner TEXT NOT NULL, session TEXT NOT NULL, revision INTEGER NOT NULL,
 passage TEXT NOT NULL, start INTEGER NOT NULL, end INTEGER NOT NULL,
 model TEXT NOT NULL, dimensions INTEGER NOT NULL, vector BLOB NOT NULL,
 PRIMARY KEY(owner,session,revision,passage,start,model),
 FOREIGN KEY(owner,session) REFERENCES source(owner,session));
CREATE INDEX embedding_owner_model ON memory_embedding(owner,model);
PRAGMA user_version=11; COMMIT;'''


def normalized(values,dimensions):
    values=[float(v) for v in values]
    if len(values)!=dimensions or not all(math.isfinite(v) for v in values):raise Rejected('invalid_embedding')
    norm=math.sqrt(sum(v*v for v in values))
    if norm==0:raise Rejected('invalid_embedding')
    return [v/norm for v in values]


def index_source(store,owner,session,embedder,*,expected_revision=None):
    source=store.source(owner,session)
    if source is None or (expected_revision is not None and source['revision']!=expected_revision):
        raise Rejected('stale_embedding_source')
    pieces=[]
    for passage in source['passages']:
        for start,end,text in embedder.windows(passage['text']):
            if not (type(start) is int and type(end) is int and 0<=start<end<=len(passage['text'])
                    and text==passage['text'][start:end]):raise Rejected('invalid_embedding_span')
            pieces.append((passage['id'],start,end,text))
            if len(pieces)>512:raise Rejected('embedding_source_too_large')
    with store.connect() as db:
        existing=db.execute('SELECT passage,start,end FROM memory_embedding WHERE owner=? AND session=? AND revision=? AND model=? ORDER BY passage,start',
            (owner,session,source['revision'],embedder.contract)).fetchall()
        if sorted(tuple(r) for r in existing)==sorted(p[:3] for p in pieces):
            return dict(status='cached',pieces=len(pieces))
    vectors=embedder.passages([p[3] for p in pieces]) if pieces else []
    if len(vectors)!=len(pieces):raise Rejected('invalid_embedding_count')
    blobs=[struct.pack('<'+'f'*embedder.dimensions,*normalized(v,embedder.dimensions)) for v in vectors]
    with store.transaction() as db:
        row=db.execute('SELECT revision,deleted FROM source WHERE owner=? AND session=?',(owner,session)).fetchone()
        if row is None or row['deleted'] or row['revision']!=source['revision']:raise Rejected('stale_embedding_source')
        count=db.execute('SELECT count(*) FROM memory_embedding WHERE owner=? AND model=? AND session!=?',(owner,embedder.contract,session)).fetchone()[0]
        if count+len(pieces)>20000:raise Rejected('embedding_storage_limit')
        db.execute('DELETE FROM memory_embedding WHERE owner=? AND session=? AND model=?',(owner,session,embedder.contract))
        db.executemany('INSERT INTO memory_embedding VALUES(?,?,?,?,?,?,?,?,?)',
            [(owner,session,source['revision'],p[0],p[1],p[2],embedder.contract,embedder.dimensions,b) for p,b in zip(pieces,blobs)])
    return dict(status='indexed',pieces=len(pieces))


def retrieve(store,owner,query,embedder,*,limit=12,exclude_session=None):
    if not isinstance(query,str) or not query.strip() or len(query)>1000 or type(limit) is not int or not 1<=limit<=50:
        raise Rejected('invalid_query')
    vector=normalized(embedder.query(query),embedder.dimensions)
    with store.transaction() as db:
        rows=db.execute('''SELECT e.* FROM memory_embedding e JOIN source s ON s.owner=e.owner AND s.session=e.session
            WHERE e.owner=? AND e.model=? AND s.deleted=0 AND s.revision=e.revision
            AND (? IS NULL OR e.session!=?)''',(owner,embedder.contract,exclude_session,exclude_session)).fetchall()
        ranked=[]
        for row in rows:
            if row['dimensions']!=embedder.dimensions:raise Rejected('embedding_contract_mismatch')
            values=struct.unpack('<'+'f'*embedder.dimensions,row['vector'])
            score=sum(a*b for a,b in zip(vector,values))
            ranked.append((score,row))
        ranked.sort(key=lambda pair:(-pair[0],pair[1]['session'],pair[1]['passage'],pair[1]['start']))
        result=[]
        for score,row in ranked[:limit]:
            source=json.loads(db.execute('SELECT payload FROM source WHERE owner=? AND session=?',(owner,row['session'])).fetchone()[0])
            passage=next(p for p in source['passages'] if p['id']==row['passage'])
            result.append(dict(session_id=row['session'],revision=row['revision'],passage_id=row['passage'],
                text_start=row['start'],text_end=row['end'],text=passage['text'][row['start']:row['end']],
                semantic_score=score,model=embedder.contract))
        return result
