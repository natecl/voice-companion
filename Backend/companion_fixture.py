"""Native socket QA: actual service/storage, synthetic provider, no external calls."""
import asyncio
import json
import os
from pathlib import Path
import sys
from websockets.asyncio.server import serve
from admission import Admission
from companion_service import CompanionService
from memory_store import MemoryStore
from memory_service import MemoryService

class Provider:
    async def stream(self, data):
        yield dict(type='delta', text='Maya swims. [[p1]]' if data['sources'] else 'Hello from the saved companion.')
        if data['question']=='Wait forever':await asyncio.Future()
        if '--ui' in sys.argv:await asyncio.sleep(.6)
        yield dict(type='completed')

async def main(directory):
    os.umask(0o077)
    ledger = Admission(directory/'usage.sqlite', total_microusd=30000, limits={'ask':(30000,3000,20)})
    credential, token = ledger.enroll()
    store = MemoryStore(directory/'memory.sqlite',retain_recording_memories='--retained' in sys.argv)
    if '--retained' in sys.argv:
        from retention_fixture import seed
        await seed(store,store.owner_for(credential),directory/'retention')
    service = CompanionService(ledger, store, Provider())
    notes_enabled='--notes' in sys.argv
    memory=MemoryService(ledger,store,generate_notes=notes_enabled)
    notes_service=None
    if notes_enabled:
        from notes_service import NotesService,NotesWorker
        from notes_generation import NotesGenerator
        class FixtureBudget:
            def reserve(self,*args):pass
            def finish(self,*args):pass
        async def note_provider(request):
            await asyncio.sleep(.5)
            for title, summary in [
                ('Product planning', 'Test the first version with five people.'),
                ('Walk with Sam', 'A simple direction for the launch.'),
                ('Ideas for the weekend', 'A few places to explore and things to try.'),
                ('Design review', 'Keep capture simple and chat close by.'),
            ]:
                if summary in json.dumps(request):
                    sections = []
                    if title == 'Product planning':
                        sections = [dict(heading='Agreed next steps', items=[dict(text='Put together a first version.', passages=['p1']), dict(text='Compare feedback on Friday.', passages=['p1'])]), dict(heading='Still to clarify', items=[dict(text='Who will invite the participants?', passages=['p1'])])]
                    return dict(data=dict(title=title,overview=dict(text=summary,passages=['p1']),sections=sections),usage={})
            return dict(data=dict(title='Maya’s swimming',overview=dict(text='Maya enjoys swimming.',passages=['p1']),sections=[]),usage={})
        notes_service=NotesService(ledger,store)
        worker=NotesWorker(NotesGenerator(store,note_provider,FixtureBudget()),ledger)
        asyncio.create_task(worker.run())
    proactive=None
    if '--proactive' in sys.argv:
        from proactive_service import ProactiveService
        from proactive_socket import ProactiveSocketService
        store.put_source(store.owner_for(credential), dict(session_id='prior',revision=1,captured_at=100.,
            timezone='UTC',completed=True,passages=[dict(id='p1',start=0.,duration=2.,speakers=[],
                text='Alex has been waking at three each morning.')]))
        class ProactiveModel:
            async def extract(self,request):
                await asyncio.sleep(.25)
                state=json.loads(request['input'])
                return dict(usage={},data=dict(decision='contribute',
                    text='Earlier, Alex mentioned waking at three each morning. That may be worth bringing up.',
                    evidence_ids=[state['sources'][0]['id']]))
        class FreeBudget:
            def reserve(self,*args):pass
            def finish(self,*args):pass
        proactive=ProactiveSocketService(ledger,ProactiveService(store,ProactiveModel(),FreeBudget()))
    async def handle(socket):
        if socket.request.path=='/proactive' and proactive:
            await proactive.handle(socket);return
        if socket.request.path=='/notes' and notes_service:await notes_service.handle(socket)
        elif socket.request.path=='/notes':
            await socket.send(json.dumps(dict(type='error',message='notes_disabled')));await socket.close()
        elif socket.request.path=='/memory':await memory.handle(socket)
        else:await service.handle(socket)
    async with serve(handle, '127.0.0.1', 0, max_size=64000) as server:
        config = dict(url=f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/stt', token=token,
                      memoryOwnerID=store.owner_for(credential))
        temp = directory/'config.tmp'
        temp.write_text(json.dumps(config));temp.replace(directory/'config.json')
        await asyncio.Future()

if __name__ == '__main__': asyncio.run(main(Path(sys.argv[1])))
