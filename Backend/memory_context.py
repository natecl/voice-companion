"""Source hydration and selected-evidence validation; no inference."""
import hashlib
import json
from admission import Rejected
import memory_identity
import memory_time


def hydrate(store, db, owner, ref, now):
    row = db.execute('SELECT payload FROM source WHERE owner=? AND session=? AND revision=? AND deleted=0',
                     (owner, ref['session_id'], ref['revision'])).fetchone()
    if row is None: return None
    source = json.loads(row['payload'])
    passage = next((p for p in source['passages'] if p['id'] == ref['passage_id']), None)
    if passage is None: return None
    start, end = ref.get('text_start', 0), ref.get('text_end', len(passage['text']))
    if type(start) is not int or type(end) is not int or not 0 <= start <= end <= len(passage['text']):
        raise Rejected('invalid_context_span')
    claims = [dict(r) for r in db.execute('''SELECT c.id,c.text,c.state,c.reason,c.valid_from,c.valid_until,
        c.replaces,c.basis,c.subject,c.kind,c.profile_link FROM claim c JOIN support s ON s.claim=c.id
        WHERE c.owner=? AND s.owner=? AND s.session=? AND s.revision=? AND s.passage=? ORDER BY c.id''',
        (owner, owner, source['session_id'], source['revision'], passage['id']))]
    for claim in claims:
        memory_time.annotate(db, owner, claim)
        store._qualify_time(claim, now)
        store._qualify_pending(db, owner, claim)
        claim.update(memory_identity.claim_identity(db, owner, claim['id']))
    return dict(session_id=source['session_id'], revision=source['revision'], passage_id=passage['id'],
                captured_at=source['captured_at'], timezone=source['timezone'],
                origin=source.get('origin', 'recording'), start=passage['start'],
                speakers=passage.get('speakers', []), text_start=start, text_end=end,
                text=passage['text'][start:end], lifecycle=claims,
                evidence_type='original_source', claim_scope='whole_passage')


def fingerprint(items):
    return hashlib.sha256(json.dumps(items, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()).hexdigest()


def select(store, owner, ranked, *, limit=12):
    if type(limit) is not int or not 1 <= limit <= 50 or len(ranked) > 100:
        raise Rejected('invalid_context_limit')
    with store.transaction() as db:
        items = []; seen = set(); now = store.clock()
        for ref in ranked:
            key = (ref['session_id'], ref['revision'], ref['passage_id'], ref.get('text_start'), ref.get('text_end'))
            if key in seen: continue
            seen.add(key)
            item = hydrate(store, db, owner, ref, now)
            if item is not None: items.append(item)
            if len(items) == limit: break
        return dict(version='selected-evidence-v1', owner=owner, items=items, digest=fingerprint(items))


def valid(store, owner, packet):
    if packet.get('version') != 'selected-evidence-v1' or packet.get('owner') != owner: return False
    items = packet.get('items', [])
    if len(items) > 50 or fingerprint(items) != packet.get('digest'): return False
    with store.transaction() as db:
        now = store.clock()
        current = [hydrate(store, db, owner, item, now) for item in items]
        return all(item is not None for item in current) and fingerprint(current) == packet['digest']
