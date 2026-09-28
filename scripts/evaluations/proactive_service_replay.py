"""Local authenticated socket/storage acceptance, with explicitly synthetic model output.

This harness is not a production endpoint or a semantic model-quality evaluation.
"""
import asyncio
import json
from pathlib import Path
import tempfile
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from companion_chat import CompanionChat
from companion_context import assemble
from memory_store import MemoryStore
from proactive_service import ProactiveService
from proactive_replay import recording


class SyntheticModel:
    calls=0
    async def extract(self,request):
        self.calls+=1
        state=json.loads(request['input'])
        return dict(usage={},data=dict(decision='contribute',
            text='An earlier note mentioned Alex waking at three each morning.',
            evidence_ids=[state['sources'][0]['id']]))


class NoPaidBudget:
    def reserve(self,*args):pass
    def finish(self,*args):pass


async def run():
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'memory.sqlite'
        store=MemoryStore(path,clock=lambda:300.)
        owner=store.owner_for('synthetic-replay');other=store.owner_for('other')
        store.put_source(owner,recording('prior','Alex has been waking at three each morning.'))
        live=recording('live','We are discussing Alex waking at three with the doctor.',completed=False)
        model=SyntheticModel();service=ProactiveService(store,model,NoPaidBudget())
        async def handle(socket):
            # Fixed synthetic credentials: ownership is resolved on the server, never from a payload.
            resolved={'Bearer replay':owner,'Bearer other':other}.get(socket.request.headers.get('Authorization'))
            if resolved is None:
                await socket.close(1008);return
            request=json.loads(await socket.recv())
            result=await service.evaluate(resolved,request,lambda:True)
            await socket.send(json.dumps(result))
        async with serve(handle,'127.0.0.1',0,max_size=64000) as server:
            url=f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}'
            async def request(token):
                async with connect(url,additional_headers={'Authorization':'Bearer '+token}) as socket:
                    await socket.send(json.dumps(live));return json.loads(await socket.recv())
            first=await request('replay');duplicate=await request('replay');isolated=await request('other')
        assert first['type']=='contribution'
        assert duplicate==dict(type='existing',state='complete',turn=first['turn_id'])
        assert isolated['type']=='silence' and model.calls==1
        reopened=CompanionChat(MemoryStore(path)).page(owner)['turns']
        assert len(reopened)==1 and reopened[0]['question']=='' and reopened[0]['answer']==first['text']
        followup=assemble(store,owner,'What did that earlier note say?')['data']
        assert len(followup['history'])==1 and 'user' not in followup['history'][0]
        assert any(s['session_id']=='prior' for s in followup['sources'])
        store.delete_source(owner,'prior')
        assert CompanionChat(store).page(owner)['turns'][0]['answer']==first['text']
        assert CompanionChat(store).context(owner)['turns']==[]
        return dict(transport='actual local websocket; synthetic provider',persisted_messages=len(reopened),
            replay_deduplicated=True,owner_isolation=True,followup_original_evidence=True,
            deleted_note_preserves_answer=True,synthetic_model_calls=model.calls,paid_calls=0,
            hosted_route_enabled=False,native_integration=False)


if __name__=='__main__':print(json.dumps(asyncio.run(run()),indent=2))
