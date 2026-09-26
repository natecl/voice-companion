"""Explicit local embedding queue; no inference at startup or in source transactions."""
import asyncio
import uuid
from admission import Rejected
from memory_vectors import index_source

SCHEMA='''BEGIN IMMEDIATE;
CREATE TABLE IF NOT EXISTS memory_index_job(
 owner TEXT NOT NULL, session TEXT NOT NULL, revision INTEGER NOT NULL, model TEXT NOT NULL,
 state TEXT NOT NULL, lease TEXT, error TEXT,
 PRIMARY KEY(owner,session,revision,model),
 FOREIGN KEY(owner,session) REFERENCES source(owner,session));
CREATE INDEX IF NOT EXISTS memory_index_queue ON memory_index_job(model,state);
CREATE INDEX IF NOT EXISTS claim_replacement ON claim(owner,replaces);
PRAGMA user_version=12; COMMIT;'''


def enqueue(db,owner,source,model):
    if model is not None and source['completed']:
        db.execute("INSERT OR IGNORE INTO memory_index_job VALUES(?,?,?,?,'queued',NULL,NULL)",
                   (owner,source['session_id'],source['revision'],model))


def coverage(store,owner,model):
    with store.connect() as db:
        rows=db.execute('''SELECT coalesce(j.state,'unindexed') AS state,count(*) AS count
            FROM source s LEFT JOIN memory_index_job j ON j.owner=s.owner AND j.session=s.session
                AND j.revision=s.revision AND j.model=?
            WHERE s.owner=? AND s.deleted=0 AND json_extract(s.payload,'$.completed')=1
            GROUP BY coalesce(j.state,'unindexed')''',(model,owner))
        return {r['state']:r['count'] for r in rows}


class IndexWorker:
    def __init__(self,store,embedder,admission):
        self.store,self.embedder,self.admission=store,embedder,admission
        self.state='starting';self.completed=0;self.failed=0

    def recover(self):
        # Operator calls once under the service's exclusive process lock. Pure local work
        # can resume; the source-version cache makes an interrupted completed write reusable.
        with self.store.transaction() as db:
            db.execute("UPDATE memory_index_job SET state='queued',lease=NULL WHERE model=? AND state='running'",(self.embedder.contract,))

    def claim(self):
        credentials=set(self.admission.active_credentials())
        with self.store.transaction() as db:
            owners={r['owner'] for r in db.execute('SELECT credential,owner FROM credential_owner') if r['credential'] in credentials}
            rows=db.execute("SELECT rowid,* FROM memory_index_job WHERE model=? AND state='queued' ORDER BY rowid",(self.embedder.contract,))
            job=next((dict(r) for r in rows if r['owner'] in owners),None)
            if job is None:return None
            job['lease']=str(uuid.uuid4())
            db.execute("UPDATE memory_index_job SET state='running',lease=? WHERE rowid=?",(job['lease'],job['rowid']))
            return job

    def finish(self,job,state,error=None):
        with self.store.transaction() as db:
            changed=db.execute('UPDATE memory_index_job SET state=?,lease=NULL,error=? WHERE rowid=? AND lease=? AND state=\'running\'',
                       (state,error,job['rowid'],job['lease'])).rowcount
            return changed==1

    async def step(self):
        job=await asyncio.to_thread(self.claim)
        if job is None:return False
        self.state='running'
        try:
            result=await asyncio.to_thread(index_source,self.store,job['owner'],job['session'],self.embedder,expected_revision=job['revision'])
            if not await asyncio.to_thread(self.finish,job,'done'):
                return dict(status='obsolete')
            self.completed+=1
            return result
        except Rejected as error:
            code=str(error)
            await asyncio.to_thread(self.finish,job,'failed',code)
            self.failed+=1
            if code not in ('stale_embedding_source','embedding_source_too_large','embedding_storage_limit'):
                self.state='halted';raise
            return dict(status='failed',reason=code)
        except Exception:
            await asyncio.to_thread(self.finish,job,'failed','index_service_failure')
            self.state='halted';raise

    def status(self):
        return dict(state=self.state,completed=self.completed,failed=self.failed)

    async def run(self):
        try:
            while True:
                if not await self.step():
                    self.state='idle';await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.state='stopped';raise
        except Exception:
            self.state='halted'
