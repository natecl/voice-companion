"""Owner-scoped evidence candidates ranked before limits; no identity inference."""
import json
import re
from admission import Rejected
from memory_identity import claim_identity, live_passage
from memory_atomic import snapshot


def terms(text):
    stop={'the','a','an','my','author','authors','now','instead','of','is','and','to','i','user'}
    return set(re.findall(r'\w+',text.casefold()))-stop


def related(store,owner,proposal,*,limit=4):
    if type(limit) is not int or not 1<=limit<=20:raise Rejected('invalid_candidate_limit')
    name=proposal['mention']['name']
    query=terms(proposal['text']+' '+(proposal['change']['previous_text'] or ''))
    ranked=[]
    with store.connect() as db:
        # Owner storage has a 5,000-claim cap. No recency prefilter is allowed here.
        for row in db.execute("SELECT * FROM claim WHERE owner=? AND state IN ('active','expired','unresolved')",(owner,)):
            item=dict(row)
            mentions=[dict(r) for r in db.execute("SELECT id,description FROM memory_mention WHERE owner=? AND claim=? AND state='live'",(owner,item['id']))]
            descriptions=[json.loads(r['description']) for r in mentions]
            overlap=len(query & terms(item['text']))
            named=bool(name and any(d['name'] and name.casefold()==d['name'].casefold() for d in descriptions))
            # This ranks possible matches, including distinct same-name people.
            # It is not authorization to merge them or a claim of exhaustive semantic recall.
            if not overlap and not named:continue
            score=overlap+4*named+int(item['kind']==proposal['kind'])
            ranked.append((score,item,mentions,descriptions))
        ranked.sort(key=lambda r:(-r[0],r[1]['id']))
        result=[]
        for score,item,mentions,descriptions in ranked[:limit]:
            refs=[dict(r) for r in db.execute('SELECT session,revision,passage FROM support WHERE owner=? AND claim=? ORDER BY session,revision,passage',(owner,item['id']))]
            evidence=[]
            for ref in refs:
                passage=live_passage(db,owner,ref)
                source=db.execute('SELECT payload FROM source WHERE owner=? AND session=?',(owner,ref['session'])).fetchone()
                origin=json.loads(source['payload']).get('origin','recording')
                evidence.append(dict(ref=ref,passage=passage,origin=origin,captured_at=json.loads(source['payload']).get('captured_at')))
            item.update(claim_identity(db,owner,item['id']))
            item['evidence_token']=snapshot(db,owner,item['id'])
            item['identity_links']=[dict(r) for r in db.execute("SELECT l.* FROM memory_identity_link l JOIN memory_mention m ON m.id=l.mention WHERE m.owner=? AND m.claim=? AND l.state='active' ORDER BY l.id",(owner,item['id']))]
            metadata=db.execute('SELECT proposal FROM memory_fact_evidence WHERE owner=? AND claim=?',(owner,item['id'])).fetchone()
            item['proposal']=json.loads(metadata[0]) if metadata else None
            item.update(mentions=[dict(id=m['id'],description=d) for m,d in zip(mentions,descriptions)],evidence=evidence)
            result.append(item)
    return dict(candidates=result,matched_count=len(ranked),truncated=len(ranked)>limit,
                method='lexical_and_mentions',semantic_complete=False)
