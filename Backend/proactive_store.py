"""Durable idempotency and ordinary assistant turns for proactive contributions."""
import json
from admission import Rejected
from companion_chat import CompanionChat
from memory_store import identifier

SCHEMA = '''BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS proactive_attempt(
 owner TEXT NOT NULL REFERENCES owner(id), capture TEXT NOT NULL, cutoff TEXT NOT NULL,
 state TEXT NOT NULL, turn TEXT,
 PRIMARY KEY(owner,capture,cutoff));
CREATE TABLE IF NOT EXISTS proactive_connection(
 owner TEXT NOT NULL, capture TEXT NOT NULL, connection TEXT NOT NULL, turn TEXT NOT NULL,
 PRIMARY KEY(owner,capture,connection),
 FOREIGN KEY(owner,turn) REFERENCES companion_turn(owner,id));
PRAGMA user_version=19; COMMIT;'''


def migrate(db):
    # Historical schemas and replayed migration fixtures may already contain tables.
    # The additive column defaults preserve every pre-existing user/assistant turn.
    db.execute('BEGIN IMMEDIATE')
    try:
        if 'kind' not in {r[1] for r in db.execute('PRAGMA table_info(companion_turn)')}:
            db.execute("ALTER TABLE companion_turn ADD COLUMN kind TEXT NOT NULL DEFAULT 'reply'")
        for statement in SCHEMA.replace('BEGIN IMMEDIATE;', '').replace('COMMIT;', '').split(';'):
            if statement.strip():db.execute(statement)
        db.execute('COMMIT')
    except BaseException:
        db.execute('ROLLBACK');raise


class ProactiveStore:
    def __init__(self,store):
        self.store=store
        self.chat=CompanionChat(store)

    def claim(self,owner,capture,cutoff):
        identifier(capture);identifier(cutoff)
        with self.store.transaction() as db:
            self.chat._main(db,owner)
            old=db.execute('SELECT state,turn FROM proactive_attempt WHERE owner=? AND capture=? AND cutoff=?',
                (owner,capture,cutoff)).fetchone()
            if old:return dict(old)
            if db.execute('SELECT count(*) FROM proactive_attempt WHERE owner=? AND capture=?',
                    (owner,capture)).fetchone()[0]>=12:raise Rejected('proactive_attempt_limit')
            # Bound persisted bookkeeping alongside existing 2,000-turn limit.
            if db.execute('SELECT count(*) FROM proactive_attempt WHERE owner=?',(owner,)).fetchone()[0]>=2000:
                raise Rejected('proactive_storage_limit')
            db.execute("INSERT INTO proactive_attempt VALUES(?,?,?,'pending',NULL)",(owner,capture,cutoff))
            return None

    def finish(self,owner,capture,cutoff,state):
        if state not in ('silence','cancelled','unavailable'):raise ValueError('Invalid terminal state')
        with self.store.transaction() as db:
            db.execute("UPDATE proactive_attempt SET state=? WHERE owner=? AND capture=? AND cutoff=? AND state='pending'",
                (state,owner,capture,cutoff))

    def previous(self,owner,capture):
        with self.store.connect() as db:
            rows=db.execute('''SELECT t.answer FROM proactive_connection c JOIN companion_turn t ON t.owner=c.owner AND t.id=c.turn
                WHERE c.owner=? AND c.capture=? ORDER BY t.sequence DESC LIMIT 4''',(owner,capture)).fetchall()
            return [r['answer'] for r in reversed(rows) if r['answer']]

    def save(self,owner,capture,cutoff,turn_id,connection,text,packet,live_packet):
        identifier(turn_id);identifier(connection)
        if not isinstance(text,str) or not text.strip() or len(text)>600 or '[[' in text or ']]' in text:
            raise Rejected('invalid_proactive_output')
        with self.store.transaction() as db:
            row=db.execute('SELECT state FROM proactive_attempt WHERE owner=? AND capture=? AND cutoff=?',
                (owner,capture,cutoff)).fetchone()
            if not row or row['state']!='pending':raise Rejected('proactive_attempt_finished')
            if db.execute('SELECT 1 FROM proactive_connection WHERE owner=? AND capture=? AND connection=?',
                    (owner,capture,connection)).fetchone():
                db.execute("UPDATE proactive_attempt SET state='silence' WHERE owner=? AND capture=? AND cutoff=?",(owner,capture,cutoff))
                return None
            if db.execute("SELECT 1 FROM companion_turn WHERE owner=? AND state='pending'",(owner,)).fetchone():
                raise Rejected('chat_busy')
            count,seq=db.execute('SELECT count(*),coalesce(max(sequence),0)+1 FROM companion_turn WHERE owner=?',(owner,)).fetchone()
            if count>=2000:raise Rejected('chat_storage_limit')
            db.execute("INSERT INTO companion_turn(owner,id,sequence,question,state,created_at,kind) VALUES(?,?,?,'','pending',?,'proactive')",
                (owner,turn_id,seq,self.store.clock()))
            # Same transaction: dependencies are rehydrated and validated before commit.
            # All supplied evidence remains attached internally, even without visible citations.
            self.chat._complete(db,owner,turn_id,text,[packet,live_packet],[],[])
            db.execute('INSERT INTO proactive_connection VALUES(?,?,?,?)',(owner,capture,connection,turn_id))
            db.execute("UPDATE proactive_attempt SET state='complete',turn=? WHERE owner=? AND capture=? AND cutoff=?",
                (turn_id,owner,capture,cutoff))
            return turn_id
