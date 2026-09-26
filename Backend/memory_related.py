"""Follow stored change evidence; similarity scores cannot hide known corrections."""
from admission import Rejected


def relationships(db, owner, claim):
    rows=db.execute('''SELECT id AS claim, 'superseded_by' AS relation FROM claim
        WHERE owner=? AND replaces=? AND state!='invalid'
        UNION SELECT c.replaces AS claim, 'supersedes' AS relation FROM claim c
        JOIN claim target ON target.id=c.replaces AND target.owner=c.owner
        WHERE c.owner=? AND c.id=? AND c.state!='invalid' AND target.state!='invalid'
        UNION SELECT p.claim, 'possible_change_from' AS relation FROM claim_relation_proposal p
        JOIN claim c ON c.id=p.claim WHERE c.owner=? AND p.target=? AND c.state!='invalid'
        UNION SELECT p.target AS claim, 'possible_change_to' AS relation FROM claim_relation_proposal p
        JOIN claim c ON c.id=p.target WHERE c.owner=? AND p.claim=? AND c.state!='invalid'
        ORDER BY relation,claim LIMIT 51''',(owner,claim,owner,claim,owner,claim,owner,claim)).fetchall()
    if len(rows)>50: raise Rejected('related_context_too_large')
    return [dict(row) for row in rows]


def expand(store, owner, packet, *, max_claims=20, max_items=12):
    import memory_context
    if type(max_claims) is not int or not 1<=max_claims<=50 or type(max_items) is not int or not 1<=max_items<=50:
        raise Rejected('invalid_context_limit')
    if packet.get('owner')!=owner or packet.get('version')!='selected-evidence-v1':
        raise Rejected('memory_context_changed')
    if len(packet.get('items',[]))>max_items:
        raise Rejected('related_context_too_large')
    with store.transaction() as db:
        now=store.clock()
        items=[memory_context.hydrate(store,db,owner,item,now) for item in packet['items']]
        if any(item is None for item in items) or memory_context.fingerprint(items)!=packet['digest']:
            raise Rejected('memory_context_changed')
        seen=set(); pending=[c['id'] for item in items for c in item['lifecycle']]
        refs={(item['session_id'],item['revision'],item['passage_id']) for item in items}
        while pending:
            claim=pending.pop(0)
            if claim in seen: continue
            seen.add(claim)
            if len(seen)>max_claims: raise Rejected('related_context_too_large')
            pending.extend(r['claim'] for r in relationships(db,owner,claim) if r['claim'] not in seen)
            supports=db.execute('''SELECT p.session,p.revision,p.passage FROM support p
                JOIN source s ON s.owner=p.owner AND s.session=p.session AND s.revision=p.revision
                WHERE p.owner=? AND p.claim=? AND s.deleted=0 ORDER BY p.session,p.passage''',(owner,claim)).fetchall()
            if any(tuple(s) in refs for s in supports): continue
            if not supports: raise Rejected('memory_context_changed')
            support=supports[0]
            item=memory_context.hydrate(store,db,owner,dict(session_id=support['session'],
                revision=support['revision'],passage_id=support['passage']),now)
            if item is None: raise Rejected('memory_context_changed')
            items.append(item);refs.add(tuple(support))
            if len(items)>max_items: raise Rejected('related_context_too_large')
        return dict(version=packet['version'],owner=owner,items=items,digest=memory_context.fingerprint(items))
