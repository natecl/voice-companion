"""Atomic application of accepted evidence decisions; internal writer boundary."""
import json
import uuid
from admission import Rejected
import memory_evidence
import memory_identity
import memory_transitions
from memory_models import fingerprint

SCHEMA='''
BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS memory_fact_evidence(
 claim TEXT PRIMARY KEY REFERENCES claim(id), owner TEXT NOT NULL,
 session TEXT NOT NULL, revision INTEGER NOT NULL, proposal TEXT NOT NULL, judgments TEXT NOT NULL,
 FOREIGN KEY(owner,session) REFERENCES source(owner,session));
CREATE INDEX IF NOT EXISTS fact_evidence_source ON memory_fact_evidence(owner,session);
PRAGMA user_version=8;
COMMIT;
'''


def snapshot(db,owner,claim):
    row=db.execute("SELECT * FROM claim WHERE owner=? AND id=? AND state!='invalid'",(owner,claim)).fetchone()
    if row is None:raise Rejected('stale_relation_target')
    supports=[dict(r) for r in db.execute('SELECT session,revision,passage FROM support WHERE owner=? AND claim=? ORDER BY session,revision,passage',(owner,claim))]
    if not supports:raise Rejected('stale_relation_target')
    for ref in supports:memory_identity.live_passage(db,owner,ref)
    mentions=[dict(r) for r in db.execute("SELECT * FROM memory_mention WHERE owner=? AND claim=? ORDER BY id",(owner,claim))]
    links=[dict(r) for r in db.execute('''SELECT l.* FROM memory_identity_link l JOIN memory_mention m ON m.id=l.mention
        WHERE m.owner=? AND m.claim=? ORDER BY l.id''',(owner,claim))]
    return fingerprint(dict(claim=dict(row),supports=supports,mentions=mentions,links=links))


def commit(store,job,items):
    if not isinstance(items,list) or len(items)>256:raise Rejected('invalid_candidates')
    ids=[]
    with store.transaction() as db:
        store._chunk_job(db,job)
        owner,session,revision=job['owner'],job['session'],job['revision']
        source=json.loads(db.execute('SELECT payload FROM source WHERE owner=? AND session=?',(owner,session)).fetchone()[0])
        if db.execute('SELECT count(*) FROM claim WHERE owner=?',(owner,)).fetchone()[0]+len(items)>5000:raise Rejected('memory_storage_limit')
        # Check every prior snapshot before mutating any member of this batch.
        for item in items:
            for target,token in item.get('snapshots',{}).items():
                if snapshot(db,owner,target)!=token:raise Rejected('stale_relation_target')
        for item in items:
            proposal=item['proposal']
            raw={key:proposal[key] for key in memory_evidence.FIELDS}
            if memory_evidence.parse(dict(memories=[raw]),source,exact_spans=proposal.get('spans'))[0]!=proposal:raise Rejected('invalid_evidence_extraction')
            action=item['action']
            if action not in ('new','unresolved','correct'):raise Rejected('invalid_relation')
            target=item.get('target')
            target_item=item.get('target_item')
            if target_item is not None:
                if target is not None or type(target_item) is not int or not 0<=target_item<len(ids):raise Rejected('invalid_batch_target')
                target=ids[target_item]
            if action=='correct' and (not target or (target_item is None and target not in item.get('snapshots',{}))):raise Rejected('missing_correction_snapshot')
            if action!='correct' and target is not None:raise Rejected('invalid_relation')
            identified=item.get('identity_verified',True)
            subject=None if not identified else 'user' if proposal['scope']=='author' else ('mention_'+uuid.uuid4().hex if proposal['scope']!='unresolved' else None)
            # The timestamp is the first source observation of applicability, never an invented event date.
            current_change=item.get('current_change')
            if current_change and (action!='correct' or not current_change.get('accepted') or current_change.get('label')!='current_change'
                    or current_change.get('policy')!='applicability' or current_change.get('probabilities',{}).get('current_change',0)<.95
                    or proposal['kind'] not in ('fact','preference','event','decision') or proposal['time']['status'] not in ('past','current') or proposal['basis']!='stated'):
                raise Rejected('invalid_current_change')
            current=proposal['time']['status']=='current' or bool(current_change)
            state_action='new' if action=='new' and current else 'unresolved'
            claim=dict(text=proposal['text'],kind=proposal['kind'],basis=proposal['basis'],subject=subject,
                passages=list(dict.fromkeys(r['passage'] for r in proposal['spans'])),
                valid_from=source['captured_at'] if current else None,valid_until=None,
                judgment_version=memory_evidence.VERSION,relation=state_action,
                profile_link=item.get('profile_verified',True) and identified and proposal['scope']=='related_to_author')
            possible=list(item.get('possible_targets',[]))
            if any(t not in item.get('snapshots',{}) for t in possible):raise Rejected('missing_correction_snapshot')
            for pending in item.get('possible_target_items',[]):
                if type(pending) is not int or not 0<=pending<len(ids):raise Rejected('invalid_batch_target')
                possible.append(ids[pending])
            if possible and action!='unresolved':raise Rejected('invalid_relation')
            if target:claim['proposed_targets']=[target]
            elif possible:claim['proposed_targets']=possible
            identifier=store._write_claim(db,claim,owner,session,revision,{p['id'] for p in source['passages']})
            memory_identity.add_mentions(db,owner,identifier,session,revision,claim['passages'],proposal['mention'])
            refs=[dict(session=session,revision=revision,passage=p) for p in claim['passages']]
            anchor=item.get('anchor')
            anchor_item=item.get('anchor_item')
            if anchor_item is not None:
                if anchor is not None or type(anchor_item) is not int or not 0<=anchor_item<len(ids):raise Rejected('invalid_batch_anchor')
                row=db.execute("SELECT l.id FROM memory_identity_link l JOIN memory_mention m ON m.id=l.mention WHERE m.claim=? AND l.state='active' ORDER BY l.id LIMIT 1",(ids[anchor_item],)).fetchone()
                if row is None:raise Rejected('unresolved_identity_link')
                anchor=row[0]
            if anchor is not None and (not identified or proposal['scope']=='unresolved'):raise Rejected('unresolved_identity_link')
            if identified and proposal['scope']!='unresolved':
                anchor_refs=item.get('anchor_refs',[])
                first=anchor
                evidence=refs+anchor_refs
                for mention in db.execute("SELECT id FROM memory_mention WHERE owner=? AND claim=? ORDER BY id",(owner,identifier)).fetchall():
                    link=memory_identity.link_in_transaction(db,owner,mention['id'],evidence,rubric=item['rubric'],anchor=first)
                    if first is None:first=link['id']
            db.execute('INSERT INTO memory_fact_evidence VALUES(?,?,?,?,?,?)',
                       (identifier,owner,session,revision,json.dumps(proposal),json.dumps(dict(item['judgments'],current_change=current_change))))
            if action=='correct':
                context=memory_transitions.context(db,owner,identifier,target)
                memory_transitions.apply_in_transaction(db,owner,identifier,target,evidence_token=context['token'],rubric=item['rubric'],now=store.clock())
            ids.append(identifier)
        memory_transitions.reopen_invalid(db,owner)
        db.execute("UPDATE job SET state='done',lease=NULL WHERE id=?",(job['id'],))
    return ids
