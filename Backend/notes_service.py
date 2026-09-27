"""Authenticated notes reads/retries and a serial durable background worker."""
import asyncio
import json
from admission import Rejected
from memory_store import identifier
from recording_notes import RecordingNotes


class NotesService:
    def __init__(self, admission, store):
        self.admission, self.store = admission, store
        self.notes = RecordingNotes(store)
        self.slots = asyncio.Semaphore(2)

    def execute(self, owner, data):
        if (not isinstance(data,dict) or set(data)!={'operation','session_id','revision'}
                or data['operation'] not in ('read','retry') or type(data['revision']) is not int or data['revision']<1):
            raise Rejected('invalid_notes_request')
        identifier(data['session_id'])
        source = self.store.source(owner,data['session_id'])
        if source is None:raise Rejected('source_unavailable')
        if source['revision'] != data['revision']:raise Rejected('stale_notes')
        if data['operation']=='retry':
            current=self.notes.read(owner,data['session_id'])
            if current is None or current['error'] in ('empty_transcript','notes_input_too_large'):
                raise Rejected('notes_not_retryable')
            self.notes.enqueue(owner,data['session_id'],data['revision'],retry=True)
        result=self.notes.read(owner,data['session_id'])
        # Recheck after read. A concurrent deletion/revision never exposes old notes.
        source=self.store.source(owner,data['session_id'])
        if source is None:raise Rejected('source_unavailable')
        if source['revision'] != data['revision']:raise Rejected('stale_notes')
        return dict(type='notes',session_id=data['session_id'],revision=data['revision'],result=result)

    async def handle(self,socket):
        try:
            async with asyncio.timeout(8):
                async with self.slots:
                    raw=await socket.recv()
                    if not isinstance(raw,str) or len(raw.encode())>1000:raise Rejected('invalid_notes_request')
                    try:data=json.loads(raw)
                    except ValueError:raise Rejected('invalid_notes_request') from None
                    token=socket.request.headers.get('Authorization','').removeprefix('Bearer ')
                    credential=self.admission.authorized(token)
                    owner=await asyncio.to_thread(self.store.owner_for,credential)
                    self.admission.authorized(token)
                    result=await asyncio.to_thread(self.execute,owner,data)
                    self.admission.authorized(token)
                    await socket.send(json.dumps(result))
        except Exception as error:
            try:await socket.send(json.dumps(dict(type='error',message=str(error) if isinstance(error,Rejected) else 'notes_unavailable')))
            except Exception:pass
        finally:await socket.close()


class NotesWorker:
    """One call at a time. Failed attempts never automatically return to pending."""
    def __init__(self,generator,admission,*,busy=lambda:False):
        self.generator,self.admission,self.busy=generator,admission,busy
        self.state='starting'
        self.last_failure=None
        self.completed=0

    def status(self):return dict(state=self.state,last_failure=self.last_failure,completed=self.completed)

    def pending(self,credentials):
        if not credentials:return None
        with self.generator.notes.store.connect() as db:
            row=db.execute("""SELECT n.owner,n.session FROM recording_notes n
                JOIN source s ON s.owner=n.owner AND s.session=n.session
                WHERE n.state='pending' AND s.deleted=0 AND n.revision=s.revision
                AND EXISTS(SELECT 1 FROM credential_owner c WHERE c.owner=n.owner
                    AND c.credential IN (%s)) ORDER BY n.rowid LIMIT 1""" % ','.join('?' for _ in credentials),credentials).fetchone()
            return tuple(row) if row else None

    async def step(self):
        if self.busy():return False
        job=await asyncio.to_thread(self.pending,self.admission.active_credentials())
        if job is None:return False
        self.state='running'
        try:
            if await self.generator.generate(*job):self.completed+=1
        except asyncio.CancelledError:raise
        except Exception:
            # Generator durably fails the attempt. Only an explicit retry can requeue it.
            try:current=await asyncio.to_thread(self.generator.notes.read,*job)
            except Rejected as error:
                if str(error)!='source_unavailable':raise
                current=None
            if current and current['state'] in ('pending','generating'):raise
            self.state='failed'
            self.last_failure=current['error'] if current else 'source_changed'
            print(json.dumps(dict(event='notes_attempt_failed')),flush=True)
        return True

    async def run(self):
        try:
            while True:
                if not await self.step():
                    self.state='idle'
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            self.state='stopped';raise
        except Exception:
            # Stop on infrastructure failure; job-local failures were durably recorded above.
            self.state='halted'
            self.last_failure='notes_service_failure'
            print(json.dumps(dict(event='notes_worker_halted',reason='notes_service_failure')),flush=True)
