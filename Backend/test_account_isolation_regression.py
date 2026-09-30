"""Synthetic SQLite/local-socket authorization regressions; no provider calls."""
import asyncio
import json
from pathlib import Path
import tempfile
import threading
import unittest

from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from account_sessions import AccountSessions
from account_tokens import VerifiedIdentity, GOOGLE
from admission import Admission
from companion_service import CompanionService
from memory_store import MemoryStore
from relay import Relay


class NoProvider:
    async def stream(self, request):
        raise AssertionError('This read-only regression must not call a provider')
        yield


class AccountIsolationRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_signed_out_open_socket_cannot_read_history(self):
        await self.read_after_signout('history', 'recv')

    async def test_signed_out_during_history_read_cannot_receive_result(self):
        await self.read_after_signout('history', 'read')

    async def test_signed_out_open_socket_cannot_replay_saved_answer(self):
        await self.read_after_signout('ask', 'recv')

    async def read_after_signout(self, operation, boundary):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            admission = Admission(root / 'usage.sqlite', total_microusd=100,
                                  limits={'ask': (100, 20, 3)})
            self.addCleanup(admission.close)
            memory = MemoryStore(root / 'memory.sqlite')
            sessions = AccountSessions(admission, memory)
            challenge = sessions.challenge('google')
            account = sessions.exchange(challenge['challenge'], 'google',
                VerifiedIdentity(GOOGLE, 'synthetic-owner', admission.clock() + 300),
                'synthetic-proof')
            companion = CompanionService(admission, memory, NoProvider())
            companion.chat.start(account['owner'], 'saved-question', 'Synthetic private question',
                                 context=dict(memory=False, attachment=None, live=None))
            companion.chat.complete(account['owner'], 'saved-question', 'Synthetic private answer')
            relay = Relay('unused', admission=admission, companion=companion)
            waiting = asyncio.Event()
            reading, release = threading.Event(), threading.Event()
            self.addCleanup(release.set)
            if boundary == 'read':
                original_page = companion.chat.page
                def blocked_page(*args, **kwargs):
                    result = original_page(*args, **kwargs)
                    reading.set()
                    if not release.wait(3): raise TimeoutError('test read barrier')
                    return result
                companion.chat.page = blocked_page

            class ObservedSocket:
                """Signal the actual recv boundary without changing its behavior."""
                def __init__(self, socket): self.socket = socket
                def __getattr__(self, name): return getattr(self.socket, name)
                async def recv(self):
                    waiting.set()
                    return await self.socket.recv()

            async def handle(socket):
                await relay.handle(ObservedSocket(socket))

            async with serve(handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
                url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/companion'
                async with connect(url, additional_headers={'Authorization': 'Bearer ' + account['token']}) as socket:
                    await asyncio.wait_for(waiting.wait(), 2)
                    request = ({'operation': 'history', 'before': None} if operation == 'history' else
                               dict(operation='ask', question_id='saved-question', question='Synthetic private question',
                                    memory=False, attachment=None, live=None))
                    if boundary == 'recv':
                        sessions.sign_out(account['refresh_token'])
                    await socket.send(json.dumps(request))
                    if boundary == 'read':
                        self.assertTrue(await asyncio.to_thread(reading.wait, 2))
                        sessions.sign_out(account['refresh_token'])
                        release.set()
                    result = json.loads(await socket.recv())
                    self.assertEqual(result.get('type'), 'error', result)
                    self.assertEqual(result.get('message'), 'unauthorized', result)
            self.assertEqual(admission.usage(), [])

    async def test_revocation_between_provider_deltas_blocks_next_delta(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            admission = Admission(root / 'usage.sqlite', total_microusd=100,
                                  limits={'ask': (100, 20, 3)})
            self.addCleanup(admission.close)
            memory = MemoryStore(root / 'memory.sqlite')
            sessions = AccountSessions(admission, memory)
            challenge = sessions.challenge('google')
            account = sessions.exchange(challenge['challenge'], 'google',
                VerifiedIdentity(GOOGLE, 'synthetic-owner', admission.clock() + 300),
                'synthetic-proof')

            class RevokingProvider:
                async def stream(self, request):
                    yield dict(type='delta', text='Before sign-out.')
                    # No await: the periodic monitor cannot rescue a missing
                    # authorization check at the next content emission boundary.
                    sessions.sign_out(account['refresh_token'])
                    yield dict(type='delta', text='Private content after sign-out.')
                    yield dict(type='completed')

            companion = CompanionService(admission, memory, RevokingProvider())
            relay = Relay('unused', admission=admission, companion=companion)
            async with serve(relay.handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
                url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/companion'
                async with connect(url, additional_headers={'Authorization': 'Bearer ' + account['token']}) as socket:
                    await socket.send(json.dumps(dict(operation='ask', question_id='fresh-question',
                        question='Synthetic question', memory=False, attachment=None, live=None)))
                    events = [json.loads(item) async for item in socket]
            self.assertEqual([event['text'] for event in events if event['type'] == 'delta'], ['Before sign-out.'])
            self.assertEqual(events[-1], dict(type='error', message='unauthorized'))
            self.assertEqual(companion.chat.page(account['owner'])['turns'][0]['state'], 'failed')
            self.assertEqual(admission.usage(), [('ask', 1, 20)])
