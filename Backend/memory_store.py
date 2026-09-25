"""Application-owned memory lifecycle. No model calls; connections are operation-scoped."""
from contextlib import contextmanager, closing
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
import uuid

from admission import Rejected

VERSION = 2
EXTRACTOR_VERSION = 'memory-v1'
MAX_SOURCE_BYTES = 60000


def identifier(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 100 or not all(c.isalnum() or c in '-_.' for c in value):
        raise Rejected('invalid_memory_request')
    return value


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise Rejected('invalid_memory_request')
    return value


def validate_source(source):
    try:
        if set(source) != {'session_id', 'revision', 'captured_at', 'timezone', 'completed', 'passages'}:
            raise ValueError()
        identifier(source['session_id'])
        if type(source['revision']) is not int or not 1 <= source['revision'] <= 1_000_000:
            raise ValueError()
        number(source['captured_at'])
        if type(source['completed']) is not bool or not isinstance(source['timezone'], str) or not 1 <= len(source['timezone']) <= 100:
            raise ValueError()
        if not isinstance(source['passages'], list) or len(source['passages']) > 200:
            raise ValueError()
        ids = set()
        for p in source['passages']:
            if set(p) != {'id', 'start', 'duration', 'text', 'speakers'}:
                raise ValueError()
            identifier(p['id'])
            if p['id'] in ids or not isinstance(p['text'], str) or not p['text'].strip():
                raise ValueError()
            ids.add(p['id'])
            number(p['start']); number(p['duration'])
            if not isinstance(p['speakers'], list) or len(p['speakers']) > 20 or any(type(x) is not int or not 0 <= x < 1000 for x in p['speakers']):
                raise ValueError()
        payload = json.dumps(source, sort_keys=True, separators=(',', ':'), allow_nan=False)
        if len(payload.encode()) > MAX_SOURCE_BYTES:
            raise Rejected('memory_source_too_large')
        return payload
    except (ValueError, TypeError, KeyError):
        raise Rejected('invalid_memory_request') from None


class MemoryStore:
    def __init__(self, path, *, clock=time.time):
        self.path, self.clock = Path(path), clock
        with self.connect() as db:
            version = db.execute('PRAGMA user_version').fetchone()[0]
            if version not in (0, 1, VERSION):
                raise ValueError('Unsupported memory schema; do not reset the database')
            if version == 0:
                db.executescript('''
                    BEGIN IMMEDIATE;
                    CREATE TABLE owner(id TEXT PRIMARY KEY);
                    CREATE TABLE credential_owner(credential TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES owner(id));
                    CREATE TABLE source(
                      owner TEXT NOT NULL REFERENCES owner(id), session TEXT NOT NULL, revision INTEGER NOT NULL,
                      digest TEXT, payload TEXT, deleted INTEGER NOT NULL DEFAULT 0,
                      PRIMARY KEY(owner,session));
                    CREATE TABLE job(
                      id TEXT PRIMARY KEY, owner TEXT NOT NULL, session TEXT NOT NULL, revision INTEGER NOT NULL,
                      extractor TEXT NOT NULL, state TEXT NOT NULL, lease TEXT,
                      UNIQUE(owner,session,revision,extractor),
                      FOREIGN KEY(owner,session) REFERENCES source(owner,session));
                    CREATE TABLE claim(
                      id TEXT PRIMARY KEY, owner TEXT NOT NULL REFERENCES owner(id), text TEXT,
                      subject TEXT, kind TEXT NOT NULL, basis TEXT NOT NULL, observed REAL NOT NULL,
                      valid_from REAL, valid_until REAL, state TEXT NOT NULL, reason TEXT NOT NULL,
                      replaces TEXT, judgment_version TEXT NOT NULL);
                    CREATE TABLE support(
                      claim TEXT NOT NULL REFERENCES claim(id), owner TEXT NOT NULL, session TEXT NOT NULL,
                      revision INTEGER NOT NULL, passage TEXT NOT NULL,
                      PRIMARY KEY(claim,owner,session,revision,passage),
                      FOREIGN KEY(owner,session) REFERENCES source(owner,session));
                    CREATE INDEX claim_owner ON claim(owner,state);
                    CREATE INDEX support_source ON support(owner,session,revision);
                    PRAGMA user_version=1;
                    COMMIT;
                ''')
            if version < 2:
                db.executescript('''
                    BEGIN IMMEDIATE;
                    CREATE TABLE job_result(
                      job TEXT NOT NULL REFERENCES job(id), stage TEXT NOT NULL,
                      request_hash TEXT NOT NULL, response TEXT NOT NULL,
                      PRIMARY KEY(job,stage,request_hash));
                    ALTER TABLE job ADD COLUMN error TEXT;
                    PRAGMA user_version=2;
                    COMMIT;
                ''')
        self.path.chmod(0o600)

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=2, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        db.execute('PRAGMA secure_delete=ON')
        try:
            yield db
        finally:
            db.close()

    @contextmanager
    def transaction(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            try:
                yield db
                db.execute('COMMIT')
            except BaseException:
                db.execute('ROLLBACK')
                raise

    def owner_for(self, credential, *, existing_owner=None):
        """Server/admin use only. A renewal explicitly binds to the existing stable owner."""
        identifier(credential)
        with self.transaction() as db:
            row = db.execute('SELECT owner FROM credential_owner WHERE credential=?', (credential,)).fetchone()
            if row:
                if existing_owner is not None and existing_owner != row['owner']:
                    raise Rejected('owner_conflict')
                return row['owner']
            if existing_owner is None:
                existing_owner = str(uuid.uuid4())
                db.execute('INSERT INTO owner VALUES(?)', (existing_owner,))
            elif not db.execute('SELECT 1 FROM owner WHERE id=?', (existing_owner,)).fetchone():
                raise Rejected('unknown_owner')
            db.execute('INSERT INTO credential_owner VALUES(?,?)', (credential, existing_owner))
            return existing_owner

    def _invalidate_source(self, db, owner, session):
        db.execute('DELETE FROM job_result WHERE job IN (SELECT id FROM job WHERE owner=? AND session=?)', (owner, session))
        db.execute('DELETE FROM support WHERE owner=? AND session=?', (owner, session))
        # Unsupported content is scrubbed; IDs/state remain for stale-write diagnostics.
        db.execute("UPDATE claim SET state='invalid',reason='source_changed',text=NULL,subject=NULL WHERE owner=? AND NOT EXISTS(SELECT 1 FROM support WHERE support.claim=claim.id)", (owner,))
        db.execute("UPDATE job SET state='obsolete',lease=NULL WHERE owner=? AND session=?", (owner, session))

    def put_source(self, owner, source):
        payload = validate_source(source)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        session, revision = source['session_id'], source['revision']
        with self.transaction() as db:
            old = db.execute('SELECT * FROM source WHERE owner=? AND session=?', (owner, session)).fetchone()
            if old:
                if old['deleted']:
                    return {'status': 'deleted', 'revision': old['revision']}
                if revision < old['revision']:
                    return {'status': 'stale', 'revision': old['revision']}
                if revision == old['revision']:
                    if old['digest'] != digest:
                        raise Rejected('revision_conflict')
                    return {'status': 'unchanged', 'revision': revision}
                self._invalidate_source(db, owner, session)
                db.execute('UPDATE source SET revision=?,digest=?,payload=? WHERE owner=? AND session=?', (revision, digest, payload, owner, session))
            else:
                if db.execute('SELECT count(*) FROM source WHERE owner=? AND deleted=0', (owner,)).fetchone()[0] >= 1000:
                    raise Rejected('memory_storage_limit')
                db.execute('INSERT INTO source VALUES(?,?,?,?,?,0)', (owner, session, revision, digest, payload))
            db.execute('INSERT INTO job(id,owner,session,revision,extractor,state,lease) VALUES(?,?,?,?,?,?,NULL)', (str(uuid.uuid4()), owner, session, revision, EXTRACTOR_VERSION, 'queued'))
            return {'status': 'stored', 'revision': revision}

    def delete_source(self, owner, session):
        identifier(session)
        with self.transaction() as db:
            self._invalidate_source(db, owner, session)
            db.execute('''INSERT INTO source VALUES(?,?,0,NULL,NULL,1)
              ON CONFLICT(owner,session) DO UPDATE SET payload=NULL,digest=NULL,deleted=1''', (owner, session))
        return {'status': 'deleted'}

    def source(self, owner, session):
        with self.connect() as db:
            row = db.execute('SELECT payload FROM source WHERE owner=? AND session=? AND deleted=0', (owner, session)).fetchone()
            return json.loads(row['payload']) if row else None

    def pending_owners(self, credentials):
        # Only internal owners with a currently authorized enrollment may incur learning spend.
        with self.connect() as db:
            allowed = {r['owner'] for r in db.execute('SELECT credential,owner FROM credential_owner') if r['credential'] in credentials}
            return [r['owner'] for r in db.execute("SELECT owner FROM job WHERE state='queued' GROUP BY owner ORDER BY min(rowid)") if r['owner'] in allowed]

    def claim_job(self, owner):
        with self.transaction() as db:
            row = db.execute("SELECT * FROM job WHERE owner=? AND state='queued' ORDER BY rowid LIMIT 1", (owner,)).fetchone()
            if not row:
                return None
            lease = str(uuid.uuid4())
            db.execute("UPDATE job SET state='running',lease=? WHERE id=?", (lease, row['id']))
            return dict(row) | {'lease': lease}

    def review_empty_job(self, owner, original_id, review_version):
        """Operator-only recovery after a diagnosed false rejection; never scheduled automatically."""
        identifier(review_version)
        with self.transaction() as db:
            old = db.execute("SELECT * FROM job WHERE id=? AND owner=? AND state='done'", (original_id, owner)).fetchone()
            if not old: raise Rejected('review_not_eligible')
            live = db.execute('SELECT * FROM source WHERE owner=? AND session=?', (owner, old['session'])).fetchone()
            if not live or live['deleted'] or live['revision'] != old['revision']:
                raise Rejected('review_not_eligible')
            if db.execute('SELECT 1 FROM support WHERE owner=? AND session=? AND revision=?',
                          (owner, old['session'], old['revision'])).fetchone():
                raise Rejected('review_not_empty')
            if db.execute('SELECT 1 FROM job WHERE owner=? AND session=? AND revision=? AND extractor=?',
                          (owner, old['session'], old['revision'], review_version)).fetchone():
                raise Rejected('review_already_attempted')
            job = dict(id=str(uuid.uuid4()), owner=owner, session=old['session'], revision=old['revision'],
                       extractor=review_version, state='running', lease=str(uuid.uuid4()), error=None)
            db.execute('INSERT INTO job(id,owner,session,revision,extractor,state,lease,error) VALUES(:id,:owner,:session,:revision,:extractor,:state,:lease,:error)',job)
            return job

    def recover_jobs(self):
        # A model call may already have incurred spend. Never automatically replay it.
        with self.transaction() as db:
            db.execute("UPDATE job SET state='interrupted',lease=NULL WHERE state='running'")

    def commit_claims(self, job, candidates):
        """Internal writer boundary; not exposed to clients. PR 1 uses fixture judgments."""
        if not isinstance(candidates, list) or len(candidates) > 50:
            raise Rejected('invalid_candidates')
        with self.transaction() as db:
            live = db.execute('SELECT * FROM job WHERE id=?', (job['id'],)).fetchone()
            if not live or live['state'] != 'running' or live['lease'] != job['lease']:
                raise Rejected('stale_job')
            owner, session, revision = live['owner'], live['session'], live['revision']
            source = db.execute('SELECT * FROM source WHERE owner=? AND session=?', (owner, session)).fetchone()
            if source['deleted'] or source['revision'] != revision:
                raise Rejected('stale_job')
            passages = {p['id'] for p in json.loads(source['payload'])['passages']}
            if db.execute("SELECT count(*) FROM claim WHERE owner=?", (owner,)).fetchone()[0] + len(candidates) > 5000:
                raise Rejected('memory_storage_limit')
            for c in candidates:
                self._write_claim(db, c, owner, session, revision, passages)
            db.execute("UPDATE job SET state='done',lease=NULL WHERE id=?", (live['id'],))

    def finish_failed(self, job, code):
        identifier(code)
        with self.transaction() as db:
            db.execute("UPDATE job SET state='failed',error=?,lease=NULL WHERE id=? AND lease=? AND state='running'", (code, job['id'], job['lease']))

    def cached_result(self, job, stage, request_hash):
        with self.connect() as db:
            row = db.execute('SELECT response FROM job_result WHERE job=? AND stage=? AND request_hash=?', (job['id'], stage, request_hash)).fetchone()
            return json.loads(row[0]) if row else None

    def cache_result(self, job, stage, request_hash, result):
        with self.transaction() as db:
            current = db.execute("SELECT 1 FROM job WHERE id=? AND lease=? AND state='running'", (job['id'], job['lease'])).fetchone()
            if not current:
                raise Rejected('stale_job')
            db.execute('INSERT OR REPLACE INTO job_result VALUES(?,?,?,?)', (job['id'], stage, request_hash, json.dumps(result, allow_nan=False)))

    def _write_claim(self, db, c, owner, session, revision, passages):
        if not isinstance(c, dict) or not isinstance(c.get('text'), str) or not 1 <= len(c['text']) <= 2000:
            raise Rejected('invalid_candidate')
        refs = c.get('passages')
        if not isinstance(refs, list) or not refs or any(not isinstance(p, str) or p not in passages for p in refs):
            raise Rejected('invalid_sources')
        if c.get('basis') not in ('stated', 'inferred', 'tentative') or c.get('kind') not in ('event', 'preference', 'decision', 'fact'):
            raise Rejected('invalid_candidate')
        subject = c.get('subject')
        if subject is not None:
            identifier(subject)
        for key in ('valid_from', 'valid_until'):
            if c.get(key) is not None:
                number(c[key])
        if c.get('valid_from') is not None and c.get('valid_until') is not None and c['valid_from'] >= c['valid_until']:
            raise Rejected('invalid_interval')
        version = identifier(c.get('judgment_version'))
        relation, target = c.get('relation', 'new'), c.get('target')
        if relation not in ('new', 'duplicate', 'supersedes') or (relation == 'new' and target is not None):
            raise Rejected('invalid_relation')
        previous = None
        if relation != 'new':
            previous = db.execute("SELECT * FROM claim WHERE id=? AND owner=? AND state!='invalid'", (target, owner)).fetchone()
            if subject is None or not previous or previous['subject'] != subject or previous['kind'] != c['kind']:
                raise Rejected('invalid_relation')
        if relation == 'duplicate':
            # Semantic equivalence is judged upstream; conservative field agreement protects lifecycle.
            if any(previous[k] != c.get(k) for k in ('basis', 'valid_from', 'valid_until')):
                raise Rejected('invalid_relation')
            claim_id = previous['id']
        else:
            if relation == 'supersedes' and (previous['state'] not in ('active', 'expired') or c.get('valid_from') is None or previous['valid_from'] is None or c['valid_from'] < previous['valid_from']):
                raise Rejected('ambiguous_update')
            claim_id = str(uuid.uuid4())
            state = 'expired' if c.get('valid_until') is not None and c['valid_until'] <= self.clock() else 'active'
            db.execute('INSERT INTO claim VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',
                       (claim_id, owner, c['text'], subject, c['kind'], c['basis'], self.clock(),
                        c.get('valid_from'), c.get('valid_until'), state, 'supported', target, version))
            if relation == 'supersedes':
                db.execute("UPDATE claim SET state='superseded',reason='corrected' WHERE id=?", (target,))
        for passage in set(refs):
            db.execute('INSERT OR IGNORE INTO support VALUES(?,?,?,?,?)', (claim_id, owner, session, revision, passage))

    def maintain(self):
        with self.transaction() as db:
            db.execute("UPDATE claim SET state='expired',reason='validity_ended' WHERE state='active' AND valid_until<=?", (self.clock(),))

    def search(self, owner, query='', *, historical=False, limit=20):
        """Bounded lexical baseline. Result provenance/lifecycle is mandatory for downstream recall."""
        if not isinstance(query, str) or len(query) > 1000 or type(limit) is not int or not 1 <= limit <= 50:
            raise Rejected('invalid_query')
        terms = query.casefold().split()[:12]
        with self.connect() as db:
            rows = db.execute("SELECT * FROM claim WHERE owner=? AND state!='invalid' ORDER BY observed DESC,id LIMIT 5000", (owner,)).fetchall()
            result = []
            for row in rows:
                item = dict(row)
                if not historical and (item['state'] != 'active' or (item['valid_until'] is not None and item['valid_until'] <= self.clock()) or (item['valid_from'] is not None and item['valid_from'] > self.clock())):
                    continue
                if terms and not any(t in item['text'].casefold() for t in terms):
                    continue
                item['sources'] = [dict(r) for r in db.execute('SELECT session,revision,passage FROM support WHERE claim=?', (item['id'],))]
                result.append(item)
                if len(result) >= limit:
                    break
            return result

    def evidence(self, owner, session):
        """Raw-source fallback includes lifecycle annotations; not yet used by Ask."""
        with self.connect() as db:
            row = db.execute('SELECT * FROM source WHERE owner=? AND session=? AND deleted=0', (owner, session)).fetchone()
            if not row:
                return None
            source = json.loads(row['payload'])
            for passage in source['passages']:
                passage['claims'] = [dict(r) for r in db.execute('''SELECT c.id,c.state,c.valid_from,c.valid_until,c.replaces FROM claim c
                  JOIN support s ON s.claim=c.id WHERE s.owner=? AND s.session=? AND s.revision=? AND s.passage=?''', (owner, session, row['revision'], passage['id']))]
                for claim in passage['claims']:
                    if claim['state'] == 'active' and claim['valid_until'] is not None and claim['valid_until'] <= self.clock():
                        claim['state'] = 'expired'
            return source

    def recall_snapshot(self, owner):
        """Consistent owner snapshot, including lifecycle for raw-evidence fallback."""
        with self.transaction() as db:
            sources = []
            rows = db.execute('SELECT session,revision,payload FROM source WHERE owner=? AND deleted=0 ORDER BY session', (owner,)).fetchall()
            for row in rows:
                source = json.loads(row['payload'])
                for passage in source['passages']:
                    claims = [dict(c) for c in db.execute("""SELECT c.id,c.state,c.valid_from,c.valid_until,c.replaces,c.basis,c.subject
                        FROM claim c JOIN support s ON s.claim=c.id
                        WHERE s.owner=? AND s.session=? AND s.revision=? AND s.passage=? ORDER BY c.id""",
                        (owner, row['session'], row['revision'], passage['id']))]
                    for claim in claims:
                        if claim['state'] == 'active' and claim['valid_until'] is not None and claim['valid_until'] <= self.clock():
                            claim['state'] = 'expired'
                    passage['claims'] = claims
                sources.append(source)
            return sources

    def profile(self, owner):
        # Derived on demand: no independent stale cache to invalidate in this foundation.
        return [c for c in self.search(owner, limit=50) if c['subject'] == 'user' and c['kind'] == 'preference' and c['basis'] == 'stated'][:10]

    def diagnostics(self, owner):
        with self.connect() as db:
            return {table: [dict(r) for r in db.execute(f'SELECT {column},count(*) AS count FROM {table} WHERE owner=? GROUP BY {column}', (owner,))]
                    for table, column in [('job', 'state'), ('claim', 'state'), ('source', 'deleted')]}

    def backup(self, destination):
        path = Path(destination)
        with path.open('xb'):
            pass
        path.chmod(0o600)
        with self.connect() as source, closing(sqlite3.connect(path)) as target:
            source.backup(target)
