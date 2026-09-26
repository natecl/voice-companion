"""Source-backed identity storage. Internal judgments only; no inference or name matching.

A mention describes who a claim concerns. Its speaker label is provenance, never
proof that the speaker is the account owner. Link decisions are supplied by a
separately verified caller; this module checks ownership, revisions and dependency
integrity, not whether a model's semantic judgment is correct.
"""
import hashlib
import json
import uuid
from admission import Rejected

SCHEMA = """
BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS memory_entity(
 id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES owner(id));
CREATE TABLE IF NOT EXISTS memory_mention(
 id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES owner(id),
 claim TEXT NOT NULL REFERENCES claim(id), session TEXT NOT NULL, revision INTEGER NOT NULL,
 passage TEXT NOT NULL, description TEXT, state TEXT NOT NULL,
 FOREIGN KEY(owner,session) REFERENCES source(owner,session));
CREATE INDEX IF NOT EXISTS mention_claim ON memory_mention(owner,claim);
CREATE INDEX IF NOT EXISTS mention_source ON memory_mention(owner,session);
CREATE TABLE IF NOT EXISTS memory_identity_link(
 id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES owner(id),
 mention TEXT NOT NULL REFERENCES memory_mention(id), entity TEXT NOT NULL REFERENCES memory_entity(id),
 anchor TEXT REFERENCES memory_identity_link(id), state TEXT NOT NULL, rubric TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS identity_one_active_link
 ON memory_identity_link(mention) WHERE state='active';
CREATE INDEX IF NOT EXISTS identity_anchor ON memory_identity_link(anchor);
CREATE TABLE IF NOT EXISTS memory_identity_support(
 link TEXT NOT NULL REFERENCES memory_identity_link(id), owner TEXT NOT NULL,
 session TEXT NOT NULL, revision INTEGER NOT NULL, passage TEXT NOT NULL,
 PRIMARY KEY(link,owner,session,revision,passage),
 FOREIGN KEY(owner,session) REFERENCES source(owner,session));
CREATE INDEX IF NOT EXISTS identity_support_source ON memory_identity_support(owner,session);
PRAGMA user_version=5;
COMMIT;
"""


def description(value):
    if not isinstance(value, dict) or set(value) != {'name', 'relationship', 'qualifiers', 'speaker_label'}:
        raise Rejected('invalid_mention')
    for field in ('name', 'relationship'):
        text = value[field]
        if text is not None and (not isinstance(text, str) or not text.strip() or len(text) > 200):
            raise Rejected('invalid_mention')
    qualifiers = value['qualifiers']
    # None means not extracted, not evidence of no distinguishing qualifier.
    if qualifiers is not None and (not isinstance(qualifiers, list) or len(qualifiers) > 10
            or any(not isinstance(q, str) or not q.strip() or len(q) > 200 for q in qualifiers)):
        raise Rejected('invalid_mention')
    label = value['speaker_label']
    if label is not None and (type(label) is not int or not 0 <= label < 1000):
        raise Rejected('invalid_mention')
    return json.dumps(value, sort_keys=True, ensure_ascii=False)


def live_passage(db, owner, ref):
    if (not isinstance(ref, dict) or set(ref) != {'session', 'revision', 'passage'}
            or not isinstance(ref['session'], str) or not isinstance(ref['passage'], str)
            or type(ref['revision']) is not int):
        raise Rejected('invalid_identity_evidence')
    row = db.execute('SELECT revision,payload,deleted FROM source WHERE owner=? AND session=?',
                     (owner, ref['session'])).fetchone()
    if not row or row['deleted'] or row['revision'] != ref['revision']:
        raise Rejected('stale_identity_evidence')
    passage = next((p for p in json.loads(row['payload'])['passages'] if p['id'] == ref['passage']), None)
    if passage is None:
        raise Rejected('stale_identity_evidence')
    return passage


def add_mentions(db, owner, claim, session, revision, passages, value):
    """Called inside the claim commit transaction; no separate partial write."""
    encoded = description(value)
    for passage in set(passages):
        ref = dict(session=session, revision=revision, passage=passage)
        evidence = live_passage(db, owner, ref)
        if value['speaker_label'] is not None and value['speaker_label'] not in evidence['speakers']:
            raise Rejected('invalid_mention_speaker')
        key = json.dumps([owner, claim, session, revision, passage, encoded])
        mention = hashlib.sha256(key.encode()).hexdigest()
        db.execute('INSERT OR IGNORE INTO memory_mention VALUES(?,?,?,?,?,?,?,?)',
                   (mention, owner, claim, session, revision, passage, encoded, 'live'))


def invalidate_source(db, owner, session):
    """Scrub descriptors; invalidate directly and transitively supported links."""
    db.execute("UPDATE memory_mention SET state='invalid',description=NULL WHERE owner=? AND session=?", (owner, session))
    db.execute("""UPDATE memory_identity_link SET state='invalid' WHERE owner=? AND
      (mention IN (SELECT id FROM memory_mention WHERE owner=? AND state='invalid') OR
       id IN (SELECT link FROM memory_identity_support WHERE owner=? AND session=?))""",
       (owner, owner, owner, session))
    db.execute('DELETE FROM memory_identity_support WHERE owner=? AND session=?', (owner, session))
    while True:
        changed = db.execute("""UPDATE memory_identity_link SET state='invalid'
          WHERE owner=? AND state='active' AND anchor IN
          (SELECT id FROM memory_identity_link WHERE owner=? AND state!='active')""", (owner, owner)).rowcount
        if not changed:
            break


def claim_identity(db, owner, claim):
    rows = db.execute("""SELECT m.id,l.entity FROM memory_mention m
      LEFT JOIN memory_identity_link l ON l.mention=m.id AND l.state='active' AND l.owner=m.owner
      WHERE m.owner=? AND m.claim=? AND m.state='live'""", (owner, claim)).fetchall()
    if not rows:
        existed = db.execute('SELECT 1 FROM memory_mention WHERE owner=? AND claim=? LIMIT 1', (owner, claim)).fetchone()
        return dict(identity_status='unresolved' if existed else 'legacy_unverified', entity_id=None)
    entities = {r['entity'] for r in rows}
    if None in entities or len(entities) != 1:
        return dict(identity_status='unresolved', entity_id=None)
    return dict(identity_status='established', entity_id=next(iter(entities)))


class IdentityStore:
    def __init__(self, store):
        self.store = store

    def mentions(self, owner, claim):
        with self.store.connect() as db:
            rows = db.execute("SELECT * FROM memory_mention WHERE owner=? AND claim=? AND state='live' ORDER BY id", (owner, claim))
            return [dict(row) | {'description': json.loads(row['description'])} for row in rows]

    def link(self, owner, mention, evidence, *, rubric, anchor=None):
        with self.store.transaction() as db:
            return link_in_transaction(db, owner, mention, evidence, rubric=rubric, anchor=anchor)


def link_in_transaction(db, owner, mention, evidence, *, rubric, anchor=None):
    """Persist an accepted identity decision; never exposed as a client API.

    No anchor creates a fresh opaque entity, not an identified account owner.
    Linking to an existing entity requires an active anchor link and live
    evidence for both mentions. Matching names alone never calls this method.
    Explicitly distinct qualifiers/relationships are conservatively rejected.
    """
    if not isinstance(rubric, str) or not rubric or len(rubric) > 100:
        raise Rejected('invalid_identity_rubric')
    if not isinstance(evidence, list) or not 1 <= len(evidence) <= 20:
        raise Rejected('invalid_identity_evidence')
    row = db.execute("SELECT * FROM memory_mention WHERE id=? AND owner=? AND state='live'", (mention, owner)).fetchone()
    if not row:
        raise Rejected('stale_identity_mention')
    refs = set()
    for ref in evidence:
        live_passage(db, owner, ref)
        refs.add((ref['session'], ref['revision'], ref['passage']))
    if (row['session'], row['revision'], row['passage']) not in refs:
        raise Rejected('missing_mention_evidence')
    current = db.execute("SELECT * FROM memory_identity_link WHERE mention=? AND state='active'", (mention,)).fetchone()
    # A retry may reuse a decision, but may not rewrite it or change its support.
    if current:
        old_refs = {tuple(r) for r in db.execute('SELECT session,revision,passage FROM memory_identity_support WHERE link=?', (current['id'],))}
        if current['anchor'] != anchor or current['rubric'] != rubric or old_refs != refs:
            raise Rejected('identity_link_conflict')
        return dict(current)
    if anchor is None:
        entity = str(uuid.uuid4())
        db.execute('INSERT INTO memory_entity VALUES(?,?)', (entity, owner))
    else:
        prior = db.execute("""SELECT l.entity,m.* FROM memory_identity_link l
          JOIN memory_mention m ON m.id=l.mention
          WHERE l.id=? AND l.owner=? AND l.state='active' AND m.state='live'""", (anchor, owner)).fetchone()
        if not prior:
            raise Rejected('stale_identity_anchor')
        if (prior['session'], prior['revision'], prior['passage']) not in refs:
            raise Rejected('missing_anchor_evidence')
        old, new = json.loads(prior['description']), json.loads(row['description'])
        # This is a guard, not an identity classifier. Unknown metadata stays unresolved.
        if old['qualifiers'] is None or new['qualifiers'] is None:
            raise Rejected('incomplete_identity_metadata')
        if old['relationship'] != new['relationship'] or set(old['qualifiers']) != set(new['qualifiers']):
            raise Rejected('identity_distinction')
        entity = prior['entity']
    link = dict(id=str(uuid.uuid4()), owner=owner, mention=mention, entity=entity,
                anchor=anchor, state='active', rubric=rubric)
    db.execute('INSERT INTO memory_identity_link VALUES(:id,:owner,:mention,:entity,:anchor,:state,:rubric)', link)
    for session, revision, passage in refs:
        db.execute('INSERT INTO memory_identity_support VALUES(?,?,?,?,?)', (link['id'], owner, session, revision, passage))
    return link
