"""Identity-dependent corrections with durable dependencies and stale-decision checks.

Internal storage contract for accepted semantic judgments. No model calls and no
implicit migration of legacy corrections. Revocation reopens uncertainty; it does
not invent a current fact or automatically rerun inference.
"""
import hashlib
import json
import uuid
from admission import Rejected
from memory_identity import claim_identity

SCHEMA = """
BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS memory_correction(
 id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES owner(id),
 incoming TEXT NOT NULL REFERENCES claim(id), target TEXT NOT NULL REFERENCES claim(id),
 entity TEXT NOT NULL REFERENCES memory_entity(id), state TEXT NOT NULL,
 rubric TEXT NOT NULL, evidence_token TEXT NOT NULL,
 UNIQUE(owner,incoming,target,evidence_token));
CREATE TABLE IF NOT EXISTS memory_correction_link(
 correction TEXT NOT NULL REFERENCES memory_correction(id),
 link TEXT NOT NULL REFERENCES memory_identity_link(id), PRIMARY KEY(correction,link));
CREATE INDEX IF NOT EXISTS correction_owner ON memory_correction(owner,state);
PRAGMA user_version=6;
COMMIT;
"""


def context(db, owner, incoming, target):
    if incoming == target:
        raise Rejected('invalid_correction')
    claims, identities, links = [], [], set()
    for identifier in (incoming, target):
        row = db.execute("SELECT * FROM claim WHERE id=? AND owner=? AND state!='invalid'", (identifier, owner)).fetchone()
        if row is None:
            raise Rejected('stale_correction_claim')
        item = dict(row)
        item['sources'] = [dict(r) for r in db.execute(
            'SELECT session,revision,passage FROM support WHERE claim=? AND owner=? ORDER BY session,revision,passage', (identifier, owner))]
        if not item['sources']:
            raise Rejected('stale_correction_claim')
        identity = claim_identity(db, owner, identifier)
        if identity['identity_status'] != 'established':
            raise Rejected('unresolved_correction_identity')
        identities.append(identity['entity_id'])
        claims.append(item)
        links.update(r['id'] for r in db.execute("""SELECT l.id FROM memory_identity_link l
          JOIN memory_mention m ON m.id=l.mention WHERE m.claim=? AND m.owner=?
          AND m.state='live' AND l.state='active'""", (identifier, owner)))
    if identities[0] != identities[1]:
        raise Rejected('different_correction_identity')
    evidence = dict(claims=claims, entity=identities[0], links=sorted(links))
    evidence['token'] = hashlib.sha256(json.dumps(evidence, sort_keys=True).encode()).hexdigest()
    return evidence


def eligible(db, owner, evidence):
    new, old = evidence['claims']
    reviewed = bool(db.execute("SELECT 1 FROM memory_correction WHERE owner=? AND incoming=? AND target=? AND state='reopened'",
                               (owner, new['id'], old['id'])).fetchone())
    if ((new['kind'] != old['kind'] and not verified_current_change(db,new,old)) or new['basis'] != 'stated' or old['basis'] == 'inferred'
            or new['state'] not in ('active', 'expired', 'unresolved')
            or old['state'] not in (('active', 'expired', 'unresolved') if reviewed else ('active', 'expired'))
            or new['valid_from'] is None or old['valid_from'] is None
            or new['valid_from'] < old['valid_from']
            or (new['replaces'] is not None and not (reviewed and new['replaces'] == old['id']))):
        raise Rejected('incompatible_correction')


def verified_current_change(db,new,old):
    """Narrow opt-in exception: retain event wording, with separately checked applicability."""
    if new['kind'] not in ('fact','preference','event','decision') or old['kind'] not in ('fact','preference','event','decision'):return False
    if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='memory_fact_evidence'").fetchone():return False
    row=db.execute('SELECT proposal,judgments FROM memory_fact_evidence WHERE claim=? AND owner=?',(new['id'],new['owner'])).fetchone()
    if row is None:return False
    proposal,judgments=json.loads(row[0]),json.loads(row[1])
    decision=judgments.get('current_change') or {}
    return (proposal['time']['status'] in ('past','current') and proposal['basis']=='stated'
            and decision.get('accepted') is True and decision.get('label')=='current_change'
            and decision.get('policy')=='applicability'
            and decision.get('probabilities',{}).get('current_change',0)>=.95)


def reopen_invalid(db, owner):
    """Same transaction as source invalidation or changed claim support.

    Conservative chain rule: if one correction's identity/evidence is no longer
    valid, reopen the connected correction chain. Never restore a superseded fact
    as current merely because the correcting source disappeared.
    """
    rows = [dict(r) for r in db.execute("SELECT * FROM memory_correction WHERE owner=? AND state='active'", (owner,))]
    invalid, affected = set(), set()
    for row in rows:
        try:
            evidence = context(db, owner, row['incoming'], row['target'])
            recorded = {r['link'] for r in db.execute('SELECT link FROM memory_correction_link WHERE correction=?', (row['id'],))}
            if evidence['entity'] != row['entity'] or not recorded.issubset(evidence['links']):
                raise Rejected('changed_correction_identity')
        except Rejected:
            invalid.add(row['id'])
            affected.update((row['incoming'], row['target']))
    while True:
        extra = [r for r in rows if r['id'] not in invalid and (r['incoming'] in affected or r['target'] in affected)]
        if not extra:
            break
        for row in extra:
            invalid.add(row['id'])
            affected.update((row['incoming'], row['target']))
    for row in rows:
        if row['id'] not in invalid:
            continue
        db.execute("UPDATE memory_correction SET state='reopened' WHERE id=?", (row['id'],))
        for claim in (row['incoming'], row['target']):
            db.execute("UPDATE claim SET state='unresolved',reason='identity_evidence_changed' WHERE id=? AND owner=? AND state!='invalid'", (claim, owner))
        # Original evidence and historical replaces pointers remain inspectable.
        live = db.execute("SELECT count(*) FROM claim WHERE id IN (?,?) AND owner=? AND state!='invalid'", (row['incoming'], row['target'], owner)).fetchone()[0]
        if live == 2:
            db.execute('INSERT OR IGNORE INTO claim_relation_proposal VALUES(?,?)', (row['incoming'], row['target']))


class MemoryTransitions:
    def __init__(self, store):
        self.store = store

    def prepare_correction(self, owner, incoming, target):
        with self.store.transaction() as db:
            evidence = context(db, owner, incoming, target)
            eligible(db, owner, evidence)
            return evidence

    def apply_correction(self, owner, incoming, target, *, evidence_token, rubric):
        with self.store.transaction() as db:
            return apply_in_transaction(db, owner, incoming, target, evidence_token=evidence_token,
                                        rubric=rubric, now=self.store.clock())


def apply_in_transaction(db, owner, incoming, target, *, evidence_token, rubric, now):
    if not isinstance(rubric, str) or not rubric or len(rubric) > 100:
        raise Rejected('invalid_correction_rubric')
    if not isinstance(evidence_token, str) or len(evidence_token) != 64:
        raise Rejected('invalid_correction_token')
    reopen_invalid(db, owner)
    prior = db.execute('SELECT * FROM memory_correction WHERE owner=? AND incoming=? AND target=? AND evidence_token=?',
                       (owner, incoming, target, evidence_token)).fetchone()
    if prior:
        if prior['state'] != 'active' or prior['rubric'] != rubric:
            raise Rejected('stale_correction_decision')
        return dict(prior)
    evidence = context(db, owner, incoming, target)
    if evidence['token'] != evidence_token:
        raise Rejected('stale_correction_decision')
    eligible(db, owner, evidence)
    new, old = evidence['claims']
    row = dict(id=str(uuid.uuid4()), owner=owner, incoming=incoming, target=target,
               entity=evidence['entity'], state='active', rubric=rubric, evidence_token=evidence_token)
    db.execute('INSERT INTO memory_correction VALUES(:id,:owner,:incoming,:target,:entity,:state,:rubric,:evidence_token)', row)
    for link in evidence['links']:
        db.execute('INSERT INTO memory_correction_link VALUES(?,?)', (row['id'], link))
    state = 'expired' if new['valid_until'] is not None and new['valid_until'] <= now else 'active'
    db.execute("UPDATE claim SET state=?,reason='identity_supported_correction',replaces=? WHERE id=?", (state, target, incoming))
    db.execute("UPDATE claim SET state='superseded',reason='identity_supported_correction' WHERE id=?", (target,))
    db.execute('DELETE FROM claim_relation_proposal WHERE claim=?', (incoming,))
    return row
