"""Keep learned knowledge separate from a removed recording.

Only committed evidence-writer memories qualify. We retain their already stored
bounded supporting quotes and judgments, never copy the recording payload. These
quotes remain internal evidence for future identity/correction decisions, not a
reopenable transcript. Existing deleted recordings cannot be recovered here.
"""
import json
import re
from memory_search import STOP_WORDS

SCHEMA = '''BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS retained_recording(
 owner TEXT NOT NULL, session TEXT NOT NULL, revision INTEGER NOT NULL,
 captured_at REAL NOT NULL, timezone TEXT NOT NULL, passages TEXT NOT NULL,
 PRIMARY KEY(owner,session), FOREIGN KEY(owner,session) REFERENCES source(owner,session));
PRAGMA user_version=16; COMMIT;'''


def exists(db, owner, session):
    return db.execute('SELECT 1 FROM retained_recording WHERE owner=? AND session=?', (owner, session)).fetchone() is not None


def preserve(db, owner, session):
    row = db.execute('SELECT * FROM source WHERE owner=? AND session=? AND deleted=0', (owner, session)).fetchone()
    if row is None:return
    source = json.loads(row['payload'])
    if source.get('origin', 'recording') != 'recording':return
    supports = db.execute('SELECT claim,passage FROM support WHERE owner=? AND session=? AND revision=?',
                          (owner,session,row['revision'])).fetchall()
    if not supports:return
    # Legacy claims without independently stored extraction evidence keep their
    # existing invalidation behavior; never relabel generated prose as a quote.
    proposals = {r['claim']:json.loads(r['proposal']) for r in db.execute(
        'SELECT claim,proposal FROM memory_fact_evidence WHERE owner=? AND session=? AND revision=?',
        (owner,session,row['revision']))}
    if any(not any(e['passage']==s['passage'] for e in proposals.get(s['claim'],{}).get('evidence',[])) for s in supports):return
    db.execute('INSERT OR IGNORE INTO retained_recording VALUES(?,?,?,?,?,?)',
               (owner,session,row['revision'],source['captured_at'],source['timezone'],json.dumps({p['id']:p['speakers'] for p in source['passages'] if any(s['passage']==p['id'] for s in supports)})))


def source_metadata(db, owner, session):
    row = db.execute('SELECT payload FROM source WHERE owner=? AND session=? AND deleted=0', (owner,session)).fetchone()
    if row:return json.loads(row['payload'])
    row = db.execute('SELECT * FROM retained_recording WHERE owner=? AND session=?', (owner,session)).fetchone()
    return dict(row,session_id=row['session']) if row else None


def supporting_passage(db, owner, ref):
    row = db.execute('SELECT passages FROM retained_recording WHERE owner=? AND session=? AND revision=?',
                     (owner,ref['session'],ref['revision'])).fetchone()
    if row is None:return None
    speakers=json.loads(row['passages']).get(ref['passage'],[])
    quotes=[]
    for row in db.execute('''SELECT e.proposal FROM memory_fact_evidence e JOIN support s
        ON s.claim=e.claim AND s.owner=e.owner AND s.session=e.session AND s.revision=e.revision
        WHERE e.owner=? AND e.session=? AND e.revision=? AND s.passage=? ORDER BY e.claim''',
        (owner,ref['session'],ref['revision'],ref['passage'])):
        proposal=json.loads(row['proposal'])
        quotes.extend(e['quote'] for e in proposal['evidence'] if e['passage']==ref['passage'])
    if not quotes:return None
    # Gaps between distinct excerpts are explicit, not reconstructed speech.
    return dict(id=ref['passage'],text='\n[…]\n'.join(dict.fromkeys(quotes)),
                speakers=speakers,retained_excerpts=True)


def reference_for_claim(db, owner, claim):
    row=db.execute('''SELECT r.* FROM retained_recording r JOIN support s
        ON s.owner=r.owner AND s.session=r.session AND s.revision=r.revision
        JOIN source src ON src.owner=r.owner AND src.session=r.session
        JOIN claim c ON c.id=s.claim AND c.owner=s.owner
        WHERE r.owner=? AND s.claim=? AND src.deleted=1 AND c.state!='invalid'
        ORDER BY r.session LIMIT 1''',(owner,claim)).fetchone()
    if row is None:return None
    return dict(retained_claim_id=claim,session_id=row['session'],revision=row['revision'],passage_id='retained_'+claim)


def hydrate(store, db, owner, ref, now):
    import memory_identity
    import memory_time
    import memory_related
    canonical=reference_for_claim(db,owner,ref['retained_claim_id'])
    if canonical is None or any(ref.get(k)!=v for k,v in canonical.items()):return None
    claim=dict(db.execute('SELECT * FROM claim WHERE owner=? AND id=?',(owner,ref['retained_claim_id'])).fetchone())
    claim.pop('owner')
    memory_time.annotate(db,owner,claim)
    store._qualify_time(claim,now);store._qualify_pending(db,owner,claim)
    claim.update(memory_identity.claim_identity(db,owner,claim['id']))
    claim['related_claims']=memory_related.relationships(db,owner,claim['id'])
    source=source_metadata(db,owner,canonical['session_id'])
    return dict(canonical,captured_at=source['captured_at'],timezone=source['timezone'],origin='recording',
                start=0,speakers=[],text_start=0,text_end=len(claim['text']),text=claim['text'],lifecycle=[claim],
                evidence_type='retained_memory',claim_scope='derived_claim',source_available=False)


def retrieve(store, owner, query, *, limit=50, exclude_session=None):
    terms=set(re.findall(r'\w+',query.casefold()))-STOP_WORDS
    if not terms:return []
    ranked=[]
    with store.connect() as db:
        rows=db.execute('''SELECT DISTINCT c.id,c.text FROM claim c JOIN support s ON s.claim=c.id AND s.owner=c.owner
            JOIN retained_recording r ON r.owner=s.owner AND r.session=s.session AND r.revision=s.revision
            WHERE c.owner=? AND c.state!='invalid' AND (? IS NULL OR r.session!=?)''',(owner,exclude_session,exclude_session))
        for row in rows:
            score=len(terms & set(re.findall(r'\w+',row['text'].casefold())))
            if score:ranked.append((score,row['id']))
        ranked.sort(key=lambda v:(-v[0],v[1]))
        return [ref for _,claim in ranked[:limit] if (ref:=reference_for_claim(db,owner,claim)) is not None]
