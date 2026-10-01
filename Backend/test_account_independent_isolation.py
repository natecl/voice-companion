"""Two independent fictional people over real loopback sockets; no provider calls.

Avery and Blake have separate provider subjects, owners and sessions. Revoking
one person's session must stop that person's in-flight content and paid input
at the next boundary, and must not change the other person's owner-scoped
results.
"""
import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from cryptography.fernet import Fernet
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import InvalidStatus

from account_sessions import AccountSessions
from account_tokens import VerifiedIdentity, GOOGLE
from admission import Admission
from ask import AskService
from companion_service import CompanionService
from memory_store import MemoryStore
from provider_grants import ProviderGrants
from relay import Relay

AVERY_PRIVATE = 'Avery private: the cello audition moved to Thursday.'
BLAKE_PRIVATE = 'Blake private: the bakery shift starts at six.'
AVERY_SPEECH = 'Avery speech after revocation.'
BLAKE_SPEECH = 'Blake speech.'
AVERY_QUESTION = 'What changed for Avery?'
BLAKE_QUESTION = 'What changed for Blake?'
PASSAGES = [dict(id='p1', start=0, text='Current conversation.')]


class People:
    def __init__(self, root):
        self.admission = Admission(root / 'usage.sqlite', total_microusd=100000,
                                   limits={'ask': (100000, 20, 10), 'stt': (100000, 20000, 6)})
        self.memory = MemoryStore(root / 'memory.sqlite')
        self.sessions = AccountSessions(self.admission, self.memory)
        self.grants = ProviderGrants(self.admission, Fernet.generate_key())
        self.avery = self.sign_in('fictional-person-avery')
        self.blake = self.sign_in('fictional-person-blake')
        assert self.avery['owner'] != self.blake['owner']

    def sign_in(self, subject, proof='first'):
        challenge = self.sessions.challenge('google')
        return self.sessions.exchange(challenge['challenge'], 'google',
            VerifiedIdentity(GOOGLE, subject, self.admission.clock() + 300), f'{subject}-{proof}')

    def credential(self, account):
        return self.admission.authorized(account['token'])

    def requests(self):
        return self.admission.db.execute(
            'SELECT credential_id,category,state FROM request ORDER BY started').fetchall()

    async def settled(self):
        # The server finishes a reservation after closing its client socket.
        for _ in range(200):
            if not self.admission.db.execute("SELECT 1 FROM request WHERE state='active'").fetchone():
                return
            await asyncio.sleep(.01)
        raise AssertionError('request still active')


def headers(account):
    return {'Authorization': 'Bearer ' + account['token']}


async def events(socket):
    return [json.loads(item) async for item in socket]


async def rejected(url, account):
    try:
        async with connect(url, additional_headers=headers(account)):
            return False
    except InvalidStatus as error:
        return error.response.status_code == 401


class OwnerRecall:
    """Returns only the requesting owner's past evidence; one owner can be held open."""
    def __init__(self, people):
        self.people, self.hold, self.validating = people, None, None
        self.entered, self.release = asyncio.Event(), asyncio.Event()
        self.private = {people.avery['owner']: AVERY_PRIVATE, people.blake['owner']: BLAKE_PRIVATE}

    async def prepare(self, credential, data):
        owner = await asyncio.to_thread(self.people.memory.owner_for, credential)
        if owner == self.hold:
            self.entered.set()
            await self.release.wait()
        return dict(status='available', sources=[dict(id='m1', start=0, text=self.private[owner])])

    async def validate(self, manifest):
        if self.validating:
            self.validating, hook = None, self.validating
            hook()


class ScriptedAnswers:
    """One scripted stream per question, so one person cannot consume another's."""
    def __init__(self, scripts):
        self.scripts, self.calls = scripts, []

    async def stream(self, data):
        self.calls.append(json.dumps(data))
        question = next(key for key in self.scripts if key in self.calls[-1])
        for step in self.scripts.pop(question):
            if callable(step):
                step()
            else:
                yield step


def answer(*texts):
    return [dict(type='delta', text=text) for text in texts] + [dict(type='completed')]


class IndependentPeopleAskTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def service(self, provider, recall=None):
        with tempfile.TemporaryDirectory() as directory:
            people = People(Path(directory))
            self.addCleanup(people.admission.close)
            ask = AskService(people.admission, provider(people), recall(people) if recall else None)
            relay = Relay('unused', admission=people.admission, ask=ask)
            async with serve(relay.handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
                yield people, ask, f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/ask'

    async def test_signout_during_recall_withholds_owner_context(self):
        scripts = lambda _: ScriptedAnswers({AVERY_QUESTION: answer('Avery answer after sign-out.'),
                                             BLAKE_QUESTION: answer('Blake answer.')})
        async with self.service(scripts, OwnerRecall) as (people, ask, url):
            avery_credential, blake_credential = people.credential(people.avery), people.credential(people.blake)
            ask.recall.hold = people.avery['owner']
            request = lambda question: json.dumps(dict(question=question, passages=PASSAGES,
                                                       memory=True, session_id='live-session'))
            async with connect(url, additional_headers=headers(people.avery)) as socket:
                await socket.send(request(AVERY_QUESTION))
                self.assertEqual(json.loads(await socket.recv())['type'], 'accepted')
                await asyncio.wait_for(ask.recall.entered.wait(), 2)
                people.sessions.sign_out(people.avery['refresh_token'])
                ask.recall.release.set()
                avery = await events(socket)
            self.assertEqual(avery, [dict(type='error', message='unauthorized')])
            self.assertTrue(await rejected(url, people.avery))
            await people.settled()

            async with connect(url, additional_headers=headers(people.blake)) as socket:
                await socket.send(request(BLAKE_QUESTION))
                blake = await events(socket)
            self.assertEqual([e['type'] for e in blake], ['accepted', 'context', 'delta', 'done'])
            self.assertEqual([s['text'] for s in blake[1]['sources']], [BLAKE_PRIVATE])
            self.assertNotIn(AVERY_PRIVATE, json.dumps(blake))
            self.assertEqual(len(ask.provider.calls), 1)
            self.assertNotIn(AVERY_PRIVATE, ask.provider.calls[0])
            self.assertEqual(people.requests(), [(avery_credential, 'ask', 'failed'),
                                                 (blake_credential, 'ask', 'completed')])

    async def test_signout_during_recall_validation_skips_paid_answer(self):
        scripts = lambda _: ScriptedAnswers({AVERY_QUESTION: answer('Avery answer after sign-out.'),
                                             BLAKE_QUESTION: answer('Blake answer.')})
        async with self.service(scripts, OwnerRecall) as (people, ask, url):
            avery_credential, blake_credential = people.credential(people.avery), people.credential(people.blake)
            ask.recall.validating = lambda: people.sessions.sign_out(people.avery['refresh_token'])
            request = lambda question: json.dumps(dict(question=question, passages=PASSAGES,
                                                       memory=True, session_id='live-session'))
            async with connect(url, additional_headers=headers(people.avery)) as socket:
                await socket.send(request(AVERY_QUESTION))
                avery = await events(socket)
            self.assertEqual([e['type'] for e in avery], ['accepted', 'context', 'error'])
            self.assertEqual(avery[-1], dict(type='error', message='unauthorized'))
            self.assertEqual(ask.provider.calls, [])
            await people.settled()

            async with connect(url, additional_headers=headers(people.blake)) as socket:
                await socket.send(request(BLAKE_QUESTION))
                blake = await events(socket)
            self.assertEqual([e['type'] for e in blake], ['accepted', 'context', 'delta', 'done'])
            self.assertNotIn(AVERY_PRIVATE, json.dumps(blake))
            self.assertEqual(len(ask.provider.calls), 1)
            await people.settled()
            self.assertEqual(people.requests(), [(avery_credential, 'ask', 'failed'),
                                                 (blake_credential, 'ask', 'completed')])

    async def test_provider_revocation_between_deltas_stops_next_delta(self):
        def provider(people):
            revoke = lambda: people.grants.revoke_local_owner(people.avery['owner'])
            return ScriptedAnswers({
                AVERY_QUESTION: [dict(type='delta', text='Avery first.'), revoke,
                                 dict(type='delta', text=AVERY_PRIVATE), dict(type='completed')],
                BLAKE_QUESTION: answer('Blake answer.')})
        async with self.service(provider) as (people, ask, url):
            request = lambda question: json.dumps(dict(question=question, passages=PASSAGES))
            async with connect(url, additional_headers=headers(people.avery)) as socket:
                await socket.send(request(AVERY_QUESTION))
                avery = await events(socket)
            self.assertEqual([e['text'] for e in avery if e['type'] == 'delta'], ['Avery first.'])
            self.assertEqual(avery[-1], dict(type='error', message='unauthorized'))
            self.assertTrue(await rejected(url, people.avery))
            await people.settled()

            async with connect(url, additional_headers=headers(people.blake)) as socket:
                await socket.send(request(BLAKE_QUESTION))
                blake = await events(socket)
            self.assertEqual([e['text'] for e in blake if e['type'] == 'delta'], ['Blake answer.'])
            self.assertEqual(blake[-1]['type'], 'done')
            self.assertNotIn(AVERY_PRIVATE, json.dumps(blake))


class Upstream:
    """Fake transcription provider. Connections arrive in person order."""
    def __init__(self):
        self.frames, self.hooks = [], {}
        self.received = asyncio.Event()

    async def __call__(self, socket):
        index, frames = len(self.frames), []
        self.frames.append(frames)
        await socket.send(json.dumps({'type': 'transcript.created'}))
        async for packet in socket:
            if isinstance(packet, bytes):
                frames.append(packet)
                self.received.set()
                await self.hooks.get(index, self.partial)(socket)
            else:
                await socket.send(json.dumps({'type': 'transcript.done', 'text': BLAKE_SPEECH}))

    async def partial(self, socket):
        await socket.send(json.dumps({'type': 'transcript.partial', 'text': BLAKE_SPEECH}))


class IndependentPeopleTranscriptionTests(unittest.IsolatedAsyncioTestCase):
    @asynccontextmanager
    async def service(self):
        upstream = Upstream()
        with tempfile.TemporaryDirectory() as directory:
            people = People(Path(directory))
            self.addCleanup(people.admission.close)
            async with serve(upstream, '127.0.0.1', 0) as provider:
                with patch('relay.URL', f'ws://127.0.0.1:{provider.sockets[0].getsockname()[1]}'):
                    relay = Relay('synthetic-key', admission=people.admission)
                    async with serve(relay.handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
                        yield people, upstream, f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/stt'

    async def blake_transcribes(self, people, upstream, url, avery_credential):
        await people.settled()
        blake_credential = people.credential(people.blake)
        async with connect(url, additional_headers=headers(people.blake)) as socket:
            self.assertEqual(json.loads(await socket.recv())['type'], 'transcript.created')
            await socket.send(bytes(3200))
            await socket.send(json.dumps({'type': 'audio.done'}))
            blake = await events(socket)
        self.assertEqual([e['type'] for e in blake], ['transcript.partial', 'transcript.done'])
        self.assertNotIn(AVERY_SPEECH, json.dumps(blake))
        self.assertEqual([len(frames) for frames in upstream.frames], [1, 1])
        await people.settled()
        self.assertEqual(people.requests(), [(avery_credential, 'stt', 'failed'),
                                             (blake_credential, 'stt', 'completed')])

    async def test_signout_before_upstream_event_withholds_transcript(self):
        async with self.service() as (people, upstream, url):
            avery_credential = people.credential(people.avery)
            async def revoke_then_transcribe(socket):
                people.sessions.sign_out(people.avery['refresh_token'])
                await socket.send(json.dumps({'type': 'transcript.partial', 'text': AVERY_SPEECH}))
            upstream.hooks[0] = revoke_then_transcribe
            async with connect(url, additional_headers=headers(people.avery)) as socket:
                self.assertEqual(json.loads(await socket.recv())['type'], 'transcript.created')
                await socket.send(bytes(3200))
                avery = await asyncio.wait_for(events(socket), 3)
            self.assertNotIn(AVERY_SPEECH, json.dumps(avery))
            self.assertEqual([e['type'] for e in avery], ['error'])
            await self.blake_transcribes(people, upstream, url, avery_credential)

    async def test_revoked_audio_is_not_forwarded_upstream(self):
        async with self.service() as (people, upstream, url):
            avery_credential = people.credential(people.avery)
            async def quiet(socket):
                pass
            upstream.hooks[0] = quiet
            async with connect(url, additional_headers=headers(people.avery)) as socket:
                self.assertEqual(json.loads(await socket.recv())['type'], 'transcript.created')
                await socket.send(bytes(3200))
                await asyncio.wait_for(upstream.received.wait(), 2)
                people.grants.revoke_local_owner(people.avery['owner'])
                await socket.send(bytes(3200))
                avery = await asyncio.wait_for(events(socket), 3)
            self.assertEqual([e['type'] for e in avery], ['error'])
            self.assertEqual([len(frames) for frames in upstream.frames], [1])
            await self.blake_transcribes(people, upstream, url, avery_credential)


class IndependentPeopleCompanionTests(unittest.IsolatedAsyncioTestCase):
    async def test_revoked_turn_stays_failed_and_owners_stay_separate(self):
        with tempfile.TemporaryDirectory() as directory:
            people = People(Path(directory))
            self.addCleanup(people.admission.close)
            avery_owner, blake_owner = people.avery['owner'], people.blake['owner']
            provider = ScriptedAnswers({
                AVERY_QUESTION: [dict(type='delta', text='Avery first.'),
                                 lambda: people.grants.revoke_local_owner(avery_owner),
                                 dict(type='delta', text='Avery after revocation.'), dict(type='completed')],
                BLAKE_QUESTION: answer('Blake answer.')})
            companion = CompanionService(people.admission, people.memory, provider)
            context = dict(memory=False, attachment=None, live=None)
            for owner, text in ((avery_owner, AVERY_PRIVATE), (blake_owner, BLAKE_PRIVATE)):
                companion.chat.start(owner, 'saved', text, context=context)
                companion.chat.complete(owner, 'saved', 'Noted.')
            relay = Relay('unused', admission=people.admission, companion=companion)

            def ask(question_id, question):
                return json.dumps(dict(operation='ask', question_id=question_id, question=question, **context))

            async with serve(relay.handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
                url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/companion'

                async def exchange(account, request):
                    async with connect(url, additional_headers=headers(account)) as socket:
                        await socket.send(request)
                        return await events(socket)

                history = json.dumps({'operation': 'history', 'before': None})
                avery = await exchange(people.avery, ask('in-flight', AVERY_QUESTION))
                self.assertEqual([e['text'] for e in avery if e['type'] == 'delta'], ['Avery first.'])
                self.assertEqual(avery[-1], dict(type='error', message='unauthorized'))
                self.assertTrue(await rejected(url, people.avery))
                await people.settled()

                blake = await exchange(people.blake, ask('blake-question', BLAKE_QUESTION))
                self.assertEqual(blake[-1]['type'], 'done')
                self.assertNotIn(AVERY_PRIVATE, provider.calls[1])
                blake_history = (await exchange(people.blake, history))[0]
                self.assertEqual([t['question'] for t in blake_history['turns']], [BLAKE_PRIVATE, BLAKE_QUESTION])
                self.assertNotIn(AVERY_PRIVATE, json.dumps(blake_history))

                again = people.sign_in('fictional-person-avery', proof='second')
                self.assertEqual(again['owner'], avery_owner)
                replay = await exchange(again, ask('in-flight', AVERY_QUESTION))
                self.assertEqual([e['type'] for e in replay], ['existing'])
                self.assertEqual(replay[0]['turn']['state'], 'failed')
                self.assertIsNone(replay[0]['turn']['answer'])
                avery_history = (await exchange(again, history))[0]
                self.assertEqual([(t['question'], t['state']) for t in avery_history['turns']],
                                 [(AVERY_PRIVATE, 'complete'), (AVERY_QUESTION, 'failed')])
                self.assertNotIn(BLAKE_PRIVATE, json.dumps(avery_history))
            self.assertEqual(len(provider.calls), 2)


if __name__ == '__main__':
    unittest.main()
