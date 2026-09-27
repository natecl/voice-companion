"""Revision-bound recording notes. Storage only: no scheduling or provider calls."""
import json
import uuid
from admission import Rejected

GENERATION_VERSION = 'recording-notes-v1'
MAX_INPUT_BYTES = 48_000
MAX_OUTPUT_BYTES = 20_000
SCHEMA = '''BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS recording_notes(
 owner TEXT NOT NULL, session TEXT NOT NULL, revision INTEGER NOT NULL,
 generation_version TEXT NOT NULL, state TEXT NOT NULL
 CHECK(state IN ('pending','generating','ready','failed','outdated')),
 attempt TEXT, payload TEXT, error TEXT,
 PRIMARY KEY(owner,session), FOREIGN KEY(owner,session) REFERENCES source(owner,session));
PRAGMA user_version=17;
COMMIT;'''


def invalidate(db, owner, session, *, deleting=False):
    if deleting:
        db.execute('DELETE FROM recording_notes WHERE owner=? AND session=?', (owner, session))
    else:
        db.execute("UPDATE recording_notes SET state='outdated',attempt=NULL,payload=NULL,error='source_changed' WHERE owner=? AND session=?", (owner, session))


def validate_notes(data, source):
    """Structural/source-ID validity is necessary, not proof of factual accuracy."""
    def text(value, limit):
        return isinstance(value, str) and bool(value.strip()) and len(value) <= limit
    def bullet(item):
        if not isinstance(item, dict) or set(item) != {'text', 'passages'}:
            raise Rejected('invalid_notes')
        refs = item['passages']
        if (not text(item['text'], 1200) or not isinstance(refs, list) or not 1 <= len(refs) <= 8
                or any(not isinstance(p, str) for p in refs)
                or len(set(refs)) != len(refs) or set(refs) - ids):
            raise Rejected('invalid_notes_reference')
    ids = {p['id'] for p in source['passages']}
    if not isinstance(data, dict) or set(data) != {'title', 'overview', 'sections'}:
        raise Rejected('invalid_notes')
    if not text(data['title'], 120):raise Rejected('invalid_notes')
    bullet(data['overview'])
    sections = data['sections']
    if not isinstance(sections, list) or len(sections) > 6:raise Rejected('invalid_notes')
    count = 0
    for section in sections:
        if (not isinstance(section, dict) or set(section) != {'heading', 'items'}
                or not text(section['heading'], 80) or not isinstance(section['items'], list)
                or not 1 <= len(section['items']) <= 12):
            raise Rejected('invalid_notes')
        for item in section['items']:bullet(item)
        count += len(section['items'])
    payload = json.dumps(data, ensure_ascii=False, allow_nan=False)
    if count > 36 or len(payload.encode()) > MAX_OUTPUT_BYTES:raise Rejected('notes_too_large')
    return payload


def enqueue_source(db, owner, source):
    """Called in the source transaction: synchronization and scheduling commit together."""
    if source.get('origin') == 'personal_text':return
    error = ('empty_transcript' if not source['passages'] else
             'notes_input_too_large' if len(json.dumps(source, ensure_ascii=False).encode()) > MAX_INPUT_BYTES else None)
    db.execute("""INSERT INTO recording_notes VALUES(?,?,?,?,?,NULL,NULL,?)
        ON CONFLICT(owner,session) DO UPDATE SET revision=excluded.revision,
        generation_version=excluded.generation_version,state=excluded.state,
        attempt=NULL,payload=NULL,error=excluded.error""",
        (owner,source['session_id'],source['revision'],GENERATION_VERSION,'failed' if error else 'pending',error))


class RecordingNotes:
    def __init__(self, store):self.store = store

    @staticmethod
    def _source(db, owner, session):
        row = db.execute('SELECT revision,payload FROM source WHERE owner=? AND session=? AND deleted=0', (owner, session)).fetchone()
        if row is None:raise Rejected('source_unavailable')
        source = json.loads(row['payload'])
        if source.get('origin') == 'personal_text':raise Rejected('notes_require_recording')
        return source

    def enqueue(self, owner, session, revision, *, retry=False):
        """Caller must use terminal recording sync; no automatic historical backfill."""
        with self.store.transaction() as db:
            source = self._source(db, owner, session)
            if type(revision) is not int or revision != source['revision']:raise Rejected('stale_notes')
            old = db.execute('SELECT * FROM recording_notes WHERE owner=? AND session=?', (owner, session)).fetchone()
            if old and old['revision'] == revision and old['state'] != 'outdated':
                if not retry:return old['state']
                if old['state'] != 'failed':raise Rejected('notes_not_retryable')
            elif retry:raise Rejected('notes_not_retryable')
            enqueue_source(db, owner, source)
            return db.execute('SELECT state FROM recording_notes WHERE owner=? AND session=?',(owner,session)).fetchone()[0]

    def claim(self, owner, session):
        with self.store.transaction() as db:
            source = self._source(db, owner, session)
            row = db.execute("SELECT * FROM recording_notes WHERE owner=? AND session=? AND state='pending'", (owner, session)).fetchone()
            if row is None:return None
            if row['revision'] != source['revision']:raise Rejected('stale_notes')
            attempt = str(uuid.uuid4())
            db.execute("UPDATE recording_notes SET state='generating',attempt=? WHERE owner=? AND session=?", (attempt, owner, session))
            return dict(owner=owner, session=session, revision=row['revision'], attempt=attempt,
                        generation_version=row['generation_version'], source=source)

    def complete(self, job, data):
        with self.store.transaction() as db:
            source = self._source(db, job['owner'], job['session'])
            payload = validate_notes(data, source)
            result = db.execute('''UPDATE recording_notes SET state='ready',payload=?,error=NULL
                WHERE owner=? AND session=? AND revision=? AND generation_version=?
                AND attempt=? AND state='generating' AND revision=?''',
                (payload, job['owner'], job['session'], job['revision'], job['generation_version'], job['attempt'], source['revision']))
            if result.rowcount != 1:raise Rejected('stale_notes')

    def fail(self, job, reason):
        if reason not in {'generation_failed','generation_interrupted','invalid_notes','budget_limit','notes_input_too_large'}:
            raise ValueError('Use a bounded, content-free notes failure code')
        with self.store.transaction() as db:
            db.execute("""UPDATE recording_notes SET state='failed',payload=NULL,error=?
                WHERE owner=? AND session=? AND revision=? AND attempt=? AND state='generating'""",
                (reason, job['owner'], job['session'], job['revision'], job['attempt']))

    def recover_interrupted(self):
        """Only at exclusive service startup; never retry paid work automatically."""
        with self.store.transaction() as db:
            db.execute("UPDATE recording_notes SET state='failed',payload=NULL,error='generation_interrupted' WHERE state='generating'")

    def read(self, owner, session):
        with self.store.connect() as db:
            source = self._source(db, owner, session)
            row = db.execute('SELECT * FROM recording_notes WHERE owner=? AND session=?', (owner, session)).fetchone()
            if row is None:return None
            current = row['revision'] == source['revision'] and row['generation_version'] == GENERATION_VERSION
            return dict(revision=row['revision'], generation_version=row['generation_version'],
                        state=row['state'] if current else 'outdated', incomplete=not source['completed'],
                        notes=json.loads(row['payload']) if current and row['state']=='ready' else None,
                        error=row['error'] if current else 'source_changed')
