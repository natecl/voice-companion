import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from websockets.asyncio.server import serve
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus
from admission import Admission
from relay import Relay
from ask import AskService


class HostedRelayTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def service(self, budget=40000, stall_finalization=False, answer_provider=None):
        self.calls = 0
        self.audio_frames = 0
        self.closed = asyncio.Event()
        self.finalizing = asyncio.Event()
        async def provider(ws):
            self.calls += 1
            try:
                await ws.send('{"type":"transcript.created"}')
                async for packet in ws:
                    if isinstance(packet, bytes):
                        self.assertEqual(packet, bytes(3200))
                        self.audio_frames += 1
                    else:
                        self.assertEqual(json.loads(packet), {'type': 'audio.done'})
                        self.finalizing.set()
                        if not stall_finalization:
                            await ws.send('{"type":"transcript.done"}')
            finally:
                self.closed.set()
        with tempfile.TemporaryDirectory() as directory:
            store = Admission(Path(directory) / 'usage.sqlite', total_microusd=budget,
                              limits={'stt': (budget, 20000, 6), 'ask': (budget, 3000, 20)})
            owner, token = store.enroll()
            try:
                async with serve(provider, '127.0.0.1', 0) as upstream:
                    with patch('relay.URL', f'ws://127.0.0.1:{upstream.sockets[0].getsockname()[1]}'):
                        ask = AskService(store, answer_provider) if answer_provider else None
                        relay = Relay('synthetic-key', admission=store, ask=ask)
                        async with serve(relay.handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
                            yield store, owner, token, f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/stt'
            finally:
                store.close()

    async def test_repeated_sessions_then_budget_rejection_before_upstream(self):
        async with self.service() as (store, owner, token, url):
            with self.assertRaises(InvalidStatus):
                async with connect(url):
                    pass
            self.assertEqual(self.calls, 0)
            for _ in range(2):
                async with connect(url, additional_headers={'Authorization': 'Bearer ' + token}) as ws:
                    self.assertEqual(json.loads(await ws.recv())['type'], 'transcript.created')
                    await ws.send(bytes(3200))
                    await ws.send('{"type":"audio.done"}')
                    self.assertEqual(json.loads(await ws.recv())['type'], 'transcript.done')
                    await ws.wait_closed()
                # Wait for handler cleanup rather than racing server finalization.
                for _ in range(100):
                    if not store.db.execute("SELECT 1 FROM request WHERE state='active'").fetchone():
                        break
                    await asyncio.sleep(.01)
            async with connect(url, additional_headers={'Authorization': 'Bearer ' + token}) as ws:
                self.assertEqual(json.loads(await ws.recv())['message'], 'budget_limit')
            self.assertEqual(self.calls, 2)
            self.assertEqual(store.usage(), [('stt', 2, 40000)])

    async def test_active_revocation_closes_upstream_and_prevents_new_connection(self):
        async with self.service() as (store, owner, token, url):
            async with connect(url, additional_headers={'Authorization': 'Bearer ' + token}) as ws:
                await ws.recv()
                store.revoke(owner)
                event = json.loads(await asyncio.wait_for(ws.recv(), 3))
                self.assertEqual(event['type'], 'error')
                await asyncio.wait_for(self.closed.wait(), 2)
            with self.assertRaises(InvalidStatus):
                async with connect(url, additional_headers={'Authorization': 'Bearer ' + token}):
                    pass
            self.assertEqual(self.calls, 1)

    async def test_revocation_during_finalization_closes_upstream(self):
        async with self.service(stall_finalization=True) as (store, owner, token, url):
            async with connect(url, additional_headers={'Authorization': 'Bearer ' + token}) as ws:
                await ws.recv()
                await ws.send('{"type":"audio.done"}')
                await asyncio.wait_for(self.finalizing.wait(), 2)
                store.revoke(owner)
                self.assertEqual(json.loads(await asyncio.wait_for(ws.recv(), 3))['type'], 'error')
                await asyncio.wait_for(self.closed.wait(), 2)

    async def test_client_disconnect_closes_upstream(self):
        async with self.service() as (store, owner, token, url):
            async with connect(url, additional_headers={'Authorization': 'Bearer ' + token}) as ws:
                await ws.recv()
            await asyncio.wait_for(self.closed.wait(), 2)
            self.assertEqual(self.calls, 1)

    async def test_cancelling_concurrent_ask_keeps_audio_stream_alive(self):
        closed = asyncio.Event()
        class Answer:
            async def stream(self, data):
                try:
                    yield {'type': 'delta', 'text': 'Tuesday'}
                    await asyncio.Future()
                finally: closed.set()
        async with self.service(answer_provider=Answer()) as (store, owner, token, url):
            headers={'Authorization':'Bearer '+token}
            async with connect(url, additional_headers=headers) as recording:
                await recording.recv()
                await recording.send(bytes(3200))
                async with connect(url.replace('/stt','/ask'), additional_headers=headers) as answer:
                    await answer.send(json.dumps({'question':'When?', 'passages':[{'id':'p1','start':0,'text':'Tuesday'}]}))
                    self.assertEqual(json.loads(await answer.recv())['type'],'accepted')
                    self.assertEqual(json.loads(await answer.recv())['type'],'delta')
                    await recording.send(bytes(3200))
                await asyncio.wait_for(closed.wait(),2)
                await recording.send(bytes(3200))
                await recording.send('{"type":"audio.done"}')
                self.assertEqual(json.loads(await recording.recv())['type'],'transcript.done')
                await recording.wait_closed()
            self.assertEqual(self.audio_frames,3)
            self.assertEqual(self.calls,1)
            self.assertEqual(store.usage(),[('ask',1,3000),('stt',1,20000)])


if __name__ == '__main__':
    unittest.main()
