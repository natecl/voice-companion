"""Durable main chat and source-derived answer invalidation; no model calls."""
import json
import hashlib
import re
import uuid
from admission import Rejected
import memory_context

SCHEMA='''BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS companion_chat(
 owner TEXT PRIMARY KEY REFERENCES owner(id), id TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS companion_turn(
 owner TEXT NOT NULL REFERENCES companion_chat(owner), id TEXT NOT NULL,
 sequence INTEGER NOT NULL, question TEXT NOT NULL, state TEXT NOT NULL,
 answer TEXT, created_at REAL NOT NULL, citations TEXT NOT NULL DEFAULT '[]',
 PRIMARY KEY(owner,id), UNIQUE(owner,sequence));
CREATE UNIQUE INDEX IF NOT EXISTS companion_pending ON companion_turn(owner) WHERE state='pending';
CREATE TABLE IF NOT EXISTS companion_dependency(
 owner TEXT NOT NULL, turn TEXT NOT NULL, session TEXT NOT NULL, reference TEXT NOT NULL,
 fingerprint TEXT NOT NULL,
 PRIMARY KEY(owner,turn,reference),
 FOREIGN KEY(owner,turn) REFERENCES companion_turn(owner,id));
CREATE INDEX IF NOT EXISTS companion_source ON companion_dependency(owner,session);
PRAGMA user_version=13; COMMIT;'''


REQUEST_SCHEMA="""BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS companion_request(
 owner TEXT NOT NULL, turn TEXT NOT NULL, digest TEXT NOT NULL,
 PRIMARY KEY(owner,turn), FOREIGN KEY(owner,turn) REFERENCES companion_turn(owner,id));
PRAGMA user_version=15; COMMIT;"""


def request_digest(question,context):
    return hashlib.sha256(json.dumps([question,context],sort_keys=True,ensure_ascii=False).encode()).hexdigest()


def scrub(db,owner,turn):
    db.execute("UPDATE companion_turn SET state='invalidated',answer=NULL,citations='[]' WHERE owner=? AND id=?",(owner,turn))
    db.execute('DELETE FROM companion_dependency WHERE owner=? AND turn=?',(owner,turn))


def invalidate_source(db,owner,session,*,deleting=True):
    # Dependents inherit every source used by previous answers in their context.
    turns=db.execute("SELECT DISTINCT turn FROM companion_dependency WHERE owner=? AND session=? AND json_extract(reference,'$.retained_claim_id') IS NULL AND (? OR json_extract(reference,'$.snapshot_id') IS NULL)",(owner,session,deleting)).fetchall()
    for row in turns:
        if deleting:
            # Keep the conversation, but do not reuse unavailable evidence as current context.
            db.execute("UPDATE companion_turn SET state='outdated' WHERE owner=? AND id=? AND state='complete'",(owner,row['turn']))
            saved=db.execute('SELECT citations FROM companion_turn WHERE owner=? AND id=?',(owner,row['turn'])).fetchone()
            citations=[c for c in json.loads(saved['citations']) if c['source'].get('session_id')!=session]
            db.execute('UPDATE companion_turn SET citations=? WHERE owner=? AND id=?',(json.dumps(citations),owner,row['turn']))
            db.execute('DELETE FROM companion_dependency WHERE owner=? AND turn=? AND session=?',(owner,row['turn'],session))
        else:scrub(db,owner,row['turn'])


def reference(item):
    keys=('session_id','revision','passage_id','text_start','text_end')
    ref={key:item[key] for key in keys}
    if 'snapshot_id' in item:ref['snapshot_id']=item['snapshot_id']
    if 'retained_claim_id' in item:ref['retained_claim_id']=item['retained_claim_id']
    return json.dumps(ref,sort_keys=True,separators=(',',':'))


class CompanionChat:
    def __init__(self,store):self.store=store

    def _main(self,db,owner):
        if not db.execute('SELECT 1 FROM owner WHERE id=?',(owner,)).fetchone():raise Rejected('unknown_owner')
        db.execute('INSERT OR IGNORE INTO companion_chat VALUES(?,?)',(owner,str(uuid.uuid4())))
        return db.execute('SELECT id FROM companion_chat WHERE owner=?',(owner,)).fetchone()[0]

    def main(self,owner):
        with self.store.transaction() as db:return self._main(db,owner)

    def start(self,owner,question_id,question,*,context=None):
        from memory_store import identifier
        identifier(question_id)
        if not isinstance(question,str) or not question.strip() or len(question)>1000:raise Rejected('invalid_question')
        digest=request_digest(question,context)
        with self.store.transaction() as db:
            conversation=self._main(db,owner)
            prior=db.execute('SELECT * FROM companion_turn WHERE owner=? AND id=?',(owner,question_id)).fetchone()
            if prior:
                stored=db.execute('SELECT digest FROM companion_request WHERE owner=? AND turn=?',(owner,question_id)).fetchone()
                expected=stored[0] if stored else request_digest(prior['question'],None)
                if prior['question']!=question or digest!=expected:raise Rejected('question_id_conflict')
                self._validate_turn(db,owner,prior)
                prior=db.execute('SELECT * FROM companion_turn WHERE owner=? AND id=?',(owner,question_id)).fetchone()
                return dict(conversation_id=conversation,created=False,turn=dict(prior))
            if db.execute("SELECT 1 FROM companion_turn WHERE owner=? AND state='pending'",(owner,)).fetchone():
                raise Rejected('chat_busy')
            count,sequence=db.execute('SELECT count(*),coalesce(max(sequence),0)+1 FROM companion_turn WHERE owner=?',(owner,)).fetchone()
            if count>=2000:raise Rejected('chat_storage_limit')
            db.execute("INSERT INTO companion_turn(owner,id,sequence,question,state,answer,created_at) VALUES(?,?,?,?,'pending',NULL,?)",(owner,question_id,sequence,question,self.store.clock()))
            db.execute('INSERT INTO companion_request VALUES(?,?,?)',(owner,question_id,digest))
            return dict(conversation_id=conversation,created=True,turn=dict(db.execute('SELECT * FROM companion_turn WHERE owner=? AND id=?',(owner,question_id)).fetchone()))

    def _dependencies(self,db,owner,turn):
        return [dict(row) for row in db.execute('SELECT * FROM companion_dependency WHERE owner=? AND turn=?',(owner,turn))]

    def _valid_dependency(self,db,owner,dep):
        item=memory_context.hydrate(self.store,db,owner,json.loads(dep['reference']),self.store.clock())
        return item is not None and memory_context.fingerprint([item])==dep['fingerprint']

    def _validate_turn(self,db,owner,row):
        if row['state']!='complete':return False
        if not all(self._valid_dependency(db,owner,dep) for dep in self._dependencies(db,owner,row['id'])):
            # Qualification changes retire context, not the visible conversation.
            # Keep provenance so deletion can remove unavailable source links.
            db.execute("UPDATE companion_turn SET state='outdated' WHERE owner=? AND id=?",(owner,row['id']))
            return False
        return True

    def complete(self,owner,question_id,answer,*,packets=(),history_ids=(),citations=()):
        if not isinstance(answer,str) or not answer.strip() or len(answer.encode())>16000:raise Rejected('invalid_answer')
        if len(packets)>4 or len(history_ids)>8 or len(set(history_ids))!=len(history_ids):raise Rejected('chat_context_too_large')
        with self.store.transaction() as db:
            self._complete(db,owner,question_id,answer,packets,history_ids,citations)

    def _complete(self,db,owner,question_id,answer,packets,history_ids,citations):
        turn=db.execute('SELECT * FROM companion_turn WHERE owner=? AND id=?',(owner,question_id)).fetchone()
        if not turn or turn['state']!='pending':raise Rejected('chat_turn_not_pending')
        deps={}
        # Carry provenance through follow-ups even when they do not cite the original recording.
        for old_id in history_ids:
            old=db.execute('SELECT * FROM companion_turn WHERE owner=? AND id=? AND sequence<?',(owner,old_id,turn['sequence'])).fetchone()
            if not old or not self._validate_turn(db,owner,old):raise Rejected('chat_history_changed')
            for dep in self._dependencies(db,owner,old_id):deps[dep['reference']]=dep
        for packet in packets:
            if packet.get('owner')!=owner or packet.get('version')!='selected-evidence-v1' or len(packet.get('items',[]))>50:
                raise Rejected('invalid_chat_evidence')
            if memory_context.fingerprint(packet['items'])!=packet.get('digest'):raise Rejected('invalid_chat_evidence')
            for item in packet['items']:
                dep=dict(reference=reference(item),session=item['session_id'],fingerprint=memory_context.fingerprint([item]))
                if not self._valid_dependency(db,owner,dep):raise Rejected('memory_context_changed')
                prior=deps.get(dep['reference'])
                if prior and prior['fingerprint']!=dep['fingerprint']:raise Rejected('memory_context_changed')
                deps[dep['reference']]=dep
        if len(deps)>50:raise Rejected('chat_context_too_large')
        if len(citations)>50:raise Rejected('invalid_chat_citations')
        citation_ids=set();normalized_citations=[]
        for citation in citations:
            if (not isinstance(citation,dict) or set(citation)!={'id','source'}
                    or not isinstance(citation['id'],str) or not re.fullmatch(r'[pm][1-9][0-9]*',citation['id'])
                    or citation['id'] in citation_ids):raise Rejected('invalid_chat_citations')
            citation_ids.add(citation['id'])
            try:ref=reference(citation['source'])
            except (KeyError,TypeError):raise Rejected('invalid_chat_citations') from None
            if ref not in deps:raise Rejected('invalid_chat_citations')
            normalized_citations.append(dict(id=citation['id'],source=json.loads(ref)))
        if set(re.findall(r'\[\[([^\[\]]+)\]\]',answer))!=citation_ids:raise Rejected('invalid_chat_citations')
        for dep in deps.values():
            db.execute('INSERT INTO companion_dependency VALUES(?,?,?,?,?)',(owner,question_id,dep['session'],dep['reference'],dep['fingerprint']))
        db.execute("UPDATE companion_turn SET state='complete',answer=?,citations=? WHERE owner=? AND id=?",(answer,json.dumps(normalized_citations),owner,question_id))

    def fail(self,owner,question_id):
        # Explicit terminal failure, including reviewed interrupted requests. Never auto-retry inference.
        with self.store.transaction() as db:
            db.execute("UPDATE companion_turn SET state='failed',answer=NULL WHERE owner=? AND id=? AND state='pending'",(owner,question_id))

    def citation(self,owner,turn_id,citation_id):
        """Resolve only a citation already saved on this owner's turn, never an arbitrary client ref."""
        with self.store.transaction() as db:
            row=db.execute('SELECT * FROM companion_turn WHERE owner=? AND id=?',(owner,turn_id)).fetchone()
            if row is None:raise Rejected('source_unavailable')
            self._validate_turn(db,owner,row)
            row=db.execute('SELECT * FROM companion_turn WHERE owner=? AND id=?',(owner,turn_id)).fetchone()
            ref=next((c['source'] for c in json.loads(row['citations']) if c['id']==citation_id),None)
            if ref is None or 'retained_claim_id' in ref:raise Rejected('source_unavailable')
            item=memory_context.hydrate(self.store,db,owner,ref,self.store.clock())
            if item is None:raise Rejected('source_unavailable')
            return dict(id=citation_id,**item)

    def page(self,owner,*,before=None,limit=30):
        if type(limit) is not int or not 1<=limit<=50 or (before is not None and (type(before) is not int or before<1)):
            raise Rejected('invalid_chat_page')
        with self.store.transaction() as db:
            conversation=self._main(db,owner)
            rows=db.execute('SELECT * FROM companion_turn WHERE owner=? AND sequence<? ORDER BY sequence DESC LIMIT ?',
                            (owner,before if before is not None else 2**63-1,limit+1)).fetchall()
            more=len(rows)>limit;rows=rows[:limit]
            for row in rows:self._validate_turn(db,owner,row)
            items=[]
            for row in reversed(rows):
                current=dict(db.execute('SELECT * FROM companion_turn WHERE owner=? AND id=?',(owner,row['id'])).fetchone())
                current.pop('owner');current['citations']=json.loads(current['citations']);items.append(current)
            return dict(conversation_id=conversation,turns=items,next_before=rows[-1]['sequence'] if more else None)

    def context(self,owner,*,max_turns=8,max_bytes=6000):
        if type(max_turns) is not int or not 1<=max_turns<=8 or type(max_bytes) is not int or not 256<=max_bytes<=6000:
            raise Rejected('invalid_chat_context_limit')
        # A suffix of whole valid turns: never skip a failed/deleted turn and revive older context.
        page=self.page(owner,limit=max_turns+1)
        selected=[];omitted=page['next_before'] is not None
        for turn in reversed(page['turns']):
            if turn['state']=='pending':continue
            if turn['state']!='complete':omitted=True;break
            if turn['kind']=='proactive':
                pair=dict(id=turn['id'],assistant=turn['answer'],citations=turn['citations'],origin='proactive')
            else:
                pair=dict(id=turn['id'],user=turn['question'],assistant=turn['answer'],citations=turn['citations'])
            if len(selected)>=max_turns or len(json.dumps([pair]+selected,ensure_ascii=False).encode())>max_bytes:
                omitted=True;break
            selected.insert(0,pair)
        return dict(turns=selected,history_ids=[turn['id'] for turn in selected],history_limited=omitted)

    def evidence(self,owner,history_ids):
        """Canonical evidence behind selected history; never trust assistant prose as a source."""
        if len(history_ids)>8 or len(set(history_ids))!=len(history_ids):raise Rejected('chat_context_too_large')
        with self.store.transaction() as db:
            items={}
            for turn_id in history_ids:
                row=db.execute('SELECT * FROM companion_turn WHERE owner=? AND id=?',(owner,turn_id)).fetchone()
                if not row or not self._validate_turn(db,owner,row):raise Rejected('chat_history_changed')
                for dep in self._dependencies(db,owner,turn_id):
                    items[dep['reference']]=memory_context.hydrate(self.store,db,owner,json.loads(dep['reference']),self.store.clock())
            if len(items)>50:raise Rejected('chat_context_too_large')
            values=list(items.values())
            return dict(version='selected-evidence-v1',owner=owner,items=values,digest=memory_context.fingerprint(values))

    def recover_interrupted(self):
        """Startup only while holding the service's exclusive process lock; no inference retries."""
        with self.store.transaction() as db:
            count=db.execute("UPDATE companion_turn SET state='failed' WHERE state='pending'").rowcount
            db.execute("DELETE FROM companion_snapshot WHERE NOT EXISTS(SELECT 1 FROM companion_dependency WHERE owner=companion_snapshot.owner AND json_extract(reference,'$.snapshot_id')=companion_snapshot.id)")
            return count
