import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from websockets.asyncio.server import serve
from websockets.asyncio.client import connect
from websockets.exceptions import InvalidStatus
import relay

class RelayTests(unittest.IsolatedAsyncioTestCase):
    async def test_authentication_and_real_socket_forwarding(self):
        calls = []
        async def provider(ws):
            calls.append(True)
            await ws.send(json.dumps({'type': 'transcript.created'}))
            frame = await ws.recv()
            self.assertEqual(frame, bytes(3200))
            self.assertEqual(json.loads(await ws.recv()), {'type': 'audio.done'})
            await ws.send(json.dumps({'type': 'transcript.partial', 'text': 'Local fixture', 'start': 0, 'duration': .1}))
            await ws.send(json.dumps({'type': 'transcript.done'}))
        with tempfile.TemporaryDirectory() as directory:
            original_root, original_url = relay.ROOT, relay.URL
            relay.ROOT = Path(directory)
            (relay.ROOT / 'work').mkdir()
            try:
                async with serve(provider, '127.0.0.1', 0) as upstream:
                    relay.URL = f'ws://127.0.0.1:{upstream.sockets[0].getsockname()[1]}'
                    service = relay.Relay('fake-provider-key', 'test-client-token')
                    async with serve(service.handle, '127.0.0.1', 0, process_request=service.authorize) as server:
                        url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/stt'
                        with self.assertRaises(InvalidStatus) as error:
                            async with connect(url): pass
                        self.assertEqual(error.exception.response.status_code, 401)
                        self.assertEqual(calls, [])
                        async with connect(url, additional_headers={'Authorization': 'Bearer test-client-token'}) as client:
                            self.assertEqual(json.loads(await client.recv())['type'], 'transcript.created')
                            await client.send(bytes(3200))
                            await client.send(json.dumps({'type': 'audio.done'}))
                            self.assertEqual(json.loads(await client.recv())['text'], 'Local fixture')
                            self.assertEqual(json.loads(await client.recv())['type'], 'transcript.done')
                            await client.wait_closed()
                    self.assertEqual(len(calls), 1)
                    self.assertEqual(service.total_bytes, 3200)
                    self.assertFalse(service.active)
                    self.assertEqual(service.sessions, relay.MAX_SESSIONS)
                    async with serve(service.handle, '127.0.0.1', 0, process_request=service.authorize) as server:
                        url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/stt'
                        with self.assertRaises(InvalidStatus) as error:
                            async with connect(url, additional_headers={'Authorization': 'Bearer test-client-token'}): pass
                        self.assertEqual(error.exception.response.status_code, 429)
                    self.assertEqual(len(calls), 1)
            finally:
                relay.ROOT, relay.URL = original_root, original_url

    async def exercise_audio_limit(self, overflow=False, timeout=False):
        received = 0
        finalized = False
        async def provider(ws):
            nonlocal received, finalized
            await ws.send(json.dumps({'type': 'transcript.created'}))
            async for packet in ws:
                if isinstance(packet, bytes):
                    received += len(packet)
                else:
                    finalized = True
                    await ws.send(json.dumps({'type': 'transcript.done'}))
        with tempfile.TemporaryDirectory() as directory:
            original = relay.ROOT, relay.URL, relay.SESSION_TIMEOUT
            relay.ROOT = Path(directory)
            (relay.ROOT / 'work').mkdir()
            if timeout:
                relay.SESSION_TIMEOUT = 0.1
            try:
                async with serve(provider, '127.0.0.1', 0) as upstream:
                    relay.URL = f'ws://127.0.0.1:{upstream.sockets[0].getsockname()[1]}'
                    service = relay.Relay('fake-key', 'fixture')
                    async with serve(service.handle, '127.0.0.1', 0, process_request=service.authorize) as server:
                        url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/stt'
                        async with connect(url, additional_headers={'Authorization': 'Bearer fixture'}) as client:
                            self.assertEqual(json.loads(await client.recv())['type'], 'transcript.created')
                            if not timeout:
                                # Full PCM byte budget, sent quickly to test accounting without paid/wall-time audio.
                                for _ in range(relay.MAX_AUDIO_SECONDS):
                                    await client.send(bytes(32000))
                                await client.send(bytes(2) if overflow else json.dumps({'type': 'audio.done'}))
                            event = json.loads(await asyncio.wait_for(client.recv(), 5))
                            self.assertEqual(event['type'], 'error' if overflow or timeout else 'transcript.done')
                            await client.wait_closed()
                    self.assertFalse(service.active)
                    self.assertEqual(service.total_bytes, 0 if timeout else relay.MAX_BYTES)
                    self.assertEqual(received, service.total_bytes)
                    self.assertEqual(finalized, not overflow and not timeout)
                    ledger = json.loads((relay.ROOT / 'work/relay-usage.jsonl').read_text())
                    self.assertEqual(ledger['audio_seconds'], 0 if timeout else relay.MAX_AUDIO_SECONDS)
                    self.assertEqual(ledger['status'], 'TimeoutError' if timeout else 'ValueError' if overflow else 'completed')
            finally:
                relay.ROOT, relay.URL, relay.SESSION_TIMEOUT = original

    async def test_full_audio_budget_finalizes(self):
        await self.exercise_audio_limit()

    async def test_audio_over_budget_is_not_forwarded(self):
        await self.exercise_audio_limit(overflow=True)

    async def test_wall_timeout_closes_upstream(self):
        await self.exercise_audio_limit(timeout=True)

if __name__ == '__main__':
    unittest.main()
