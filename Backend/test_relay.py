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
                    service.sessions = 3
                    async with serve(service.handle, '127.0.0.1', 0, process_request=service.authorize) as server:
                        url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/stt'
                        with self.assertRaises(InvalidStatus) as error:
                            async with connect(url, additional_headers={'Authorization': 'Bearer test-client-token'}): pass
                        self.assertEqual(error.exception.response.status_code, 429)
                    self.assertEqual(len(calls), 1)
            finally:
                relay.ROOT, relay.URL = original_root, original_url

if __name__ == '__main__':
    unittest.main()
