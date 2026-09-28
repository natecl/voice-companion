"""Bounded development relay with optional encrypted LAN access. Not a production deployment."""
import argparse
import asyncio
from contextlib import AsyncExitStack
import ssl
import hmac
import http
import json
import secrets
import time
from admission import Rejected
from pathlib import Path
from websockets.asyncio.server import serve
from websockets.asyncio.client import connect

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'work/relay-client.json'
URL = ('wss://api.x.ai/v1/stt?model=grok-voice-transcribe-2.0&sample_rate=16000'
       '&encoding=pcm&interim_results=true&diarize=true&language=en')
MAX_AUDIO_SECONDS = 310  # App stops at 300; allow capture scheduling/queued frames.
MAX_BYTES = MAX_AUDIO_SECONDS * 32000
MAX_SESSIONS = 1
SESSION_TIMEOUT = 330  # Connection setup + capture + bounded finalization.

class Relay:
    def __init__(self, key, token=None, *, admission=None, ask=None, memory=None, learning_status=None, companion=None, indexing_status=None, notes=None, notes_status=None, proactive=None):
        self.key, self.token = key, token
        self.admission = admission
        self.ask = ask
        self.memory = memory
        self.companion = companion
        self.proactive = proactive
        self.notes = notes
        self.notes_status = notes_status
        self.indexing_status = indexing_status
        self.learning_status = learning_status
        self.active = False
        self.total_bytes = 0
        self.sessions = 0

    def authorize(self, connection, request):
        if request.path == '/health/notes':
            status=self.notes_status() if self.notes_status else {'state':'disabled'}
            return connection.respond(http.HTTPStatus.OK,json.dumps(status)+'\n')
        if request.path == '/health/indexing':
            status = self.indexing_status() if self.indexing_status else {'state':'disabled'}
            return connection.respond(http.HTTPStatus.OK,json.dumps(status)+'\n')
        if request.path == '/health/learning':
            status = self.learning_status() if self.learning_status else {'state': 'disabled'}
            return connection.respond(http.HTTPStatus.OK, json.dumps(status) + '\n')
        if request.path == '/health':
            return connection.respond(http.HTTPStatus.OK, 'ready\n')
        if request.path != '/stt' and not (request.path == '/ask' and self.ask is not None) and not (request.path == '/memory' and self.memory is not None) and not (request.path == '/companion' and self.companion is not None) and not (request.path == '/notes' and self.notes is not None) and not (request.path == '/proactive' and self.proactive is not None):
            return connection.respond(http.HTTPStatus.NOT_FOUND, 'Not found\n')
        try:
            supplied = request.headers.get('Authorization', '')
        except Exception:
            return connection.respond(http.HTTPStatus.UNAUTHORIZED, 'Unauthorized\n')
        if self.admission is not None:
            try:
                self.admission.authorized(supplied.removeprefix('Bearer ') if supplied.startswith('Bearer ') else '')
            except Rejected:
                return connection.respond(http.HTTPStatus.UNAUTHORIZED, 'Unauthorized\n')
            except Exception:
                return connection.respond(http.HTTPStatus.SERVICE_UNAVAILABLE, 'Authorization unavailable\n')
            return
        if not hmac.compare_digest(supplied, 'Bearer ' + self.token):
            return connection.respond(http.HTTPStatus.UNAUTHORIZED, 'Unauthorized\n')
        if self.active or self.sessions >= MAX_SESSIONS or self.total_bytes >= MAX_BYTES:
            return connection.respond(http.HTTPStatus.TOO_MANY_REQUESTS, 'Development limit reached\n')

    async def handle(self, client):
        if client.request.path == "/notes" and self.notes is not None:
            return await self.notes.handle(client)
        if client.request.path == "/proactive" and self.proactive is not None:
            return await self.proactive.handle(client)
        if client.request.path == "/companion" and self.companion is not None:
            return await self.companion.handle(client)
        if client.request.path == "/memory" and self.memory is not None:
            return await self.memory.handle(client)
        if client.request.path == "/ask" and self.ask is not None:
            return await self.ask.handle(client)
        reservation = None
        token = None
        if self.admission is not None:
            try:
                token = client.request.headers.get('Authorization', '').removeprefix('Bearer ')
                reservation = self.admission.reserve(token, 'stt')
            except Exception as error:
                reason = str(error) if isinstance(error, Rejected) else 'authorization_unavailable'
                await client.send(json.dumps({'type': 'error', 'message': reason}))
                await client.close(1008, reason)
                return
        # Recheck after handshake to avoid two accepted clients racing.
        if self.admission is None and (self.active or self.sessions >= MAX_SESSIONS or self.total_bytes >= MAX_BYTES):
            await client.close(1008, 'Development limit reached')
            return
        self.active = True
        self.sessions += 1
        started, sent = time.monotonic(), 0
        status = 'incomplete'
        try:
            async with asyncio.timeout(SESSION_TIMEOUT):
                async with connect(URL, additional_headers={'Authorization': 'Bearer ' + self.key},
                                   open_timeout=2 if self.admission is not None else 10,
                                   close_timeout=2, max_size=2**20) as upstream:
                    if self.admission is not None:
                        self.admission.authorized(token)
                    async def send_audio():
                        nonlocal sent
                        async for packet in client:
                            if isinstance(packet, bytes):
                                if len(packet) % 2 or sent + len(packet) > MAX_BYTES or (self.admission is None and self.total_bytes + len(packet) > MAX_BYTES):
                                    raise ValueError('Audio limit or format error')
                                sent += len(packet)
                                self.total_bytes += len(packet)
                                await upstream.send(packet)
                            elif json.loads(packet) == {'type': 'audio.done'}:
                                await upstream.send(packet)
                                return
                            else:
                                raise ValueError('Unsupported control message')
                        raise ConnectionError('Client disconnected')

                    async def receive_events():
                        async for event in upstream:
                            await client.send(event)
                            kind = json.loads(event).get('type')
                            if kind == 'transcript.done':
                                return
                            if kind == 'error':
                                raise RuntimeError('Upstream error')
                        raise ConnectionError('Upstream ended without completion')

                    async def monitor_access():
                        while True:
                            await asyncio.sleep(1)
                            self.admission.authorized(token)

                    outgoing = asyncio.create_task(send_audio())
                    incoming = asyncio.create_task(receive_events())
                    tasks = [outgoing, incoming]
                    if self.admission is not None:
                        tasks.append(asyncio.create_task(monitor_access()))
                    try:
                        done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
                        for task in done:
                            task.result()
                        if incoming not in done:
                            remaining = [task for task in tasks if task is not outgoing]
                            finished, _ = await asyncio.wait(remaining, timeout=10,
                                                             return_when=asyncio.FIRST_COMPLETED)
                            if not finished:
                                raise TimeoutError('Finalization timed out')
                            for task in finished:
                                task.result()
                        status = 'completed'
                    finally:
                        for task in tasks:
                            if not task.done(): task.cancel()
                        await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as error:
            status = type(error).__name__
            try:
                await client.send(json.dumps({'type': 'error', 'message': 'Transcription connection ended. Received text is preserved.'}))
            except Exception:
                pass  # Client may already have disconnected; cleanup still runs.
        finally:
            self.active = False
            await client.close()
            record = {'status': status, 'audio_seconds': sent / 32000,
                      'elapsed_seconds': round(time.monotonic() - started, 3),
                      'estimated_audio_cost_usd': sent / 32000 * .20 / 3600,
                      'billing_verified': False}
            if reservation is not None:
                # Do not release the durable active slot until upstream cleanup.
                self.admission.finish(reservation, completed=status == 'completed')
                record['request_id'] = reservation
            else:
                with (ROOT / 'work/relay-usage.jsonl').open('a') as ledger:
                    ledger.write(json.dumps(record) + '\n')
            print(json.dumps(record), flush=True)

async def main():
    values = dict(line.split('=', 1) for line in (ROOT / '.env').read_text().splitlines()
                  if '=' in line and not line.lstrip().startswith('#'))
    key = values.get('XAI_API_KEY', '').strip().strip('\"\'')
    if not key: raise SystemExit('XAI_API_KEY is missing')
    token = secrets.token_urlsafe(32)
    CONFIG.parent.mkdir(exist_ok=True)
    CONFIG.touch(mode=0o600, exist_ok=True)
    CONFIG.chmod(0o600)
    CONFIG.write_text(json.dumps({'url': 'ws://127.0.0.1:8766/stt', 'token': token}))
    relay = Relay(key, token)
    parser = argparse.ArgumentParser()
    parser.add_argument('--lan', action='store_true')
    args = parser.parse_args()
    phone_config = ROOT / 'work/relay-phone.json'
    try:
        async with AsyncExitStack() as stack:
            await stack.enter_async_context(serve(relay.handle, '127.0.0.1', 8766, process_request=relay.authorize,
                                                 max_size=64000, max_queue=8, close_timeout=2))
            if args.lan:
                settings = json.loads((ROOT / 'work/lan-tls/settings.json').read_text())
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.minimum_version = ssl.TLSVersion.TLSv1_2
                context.load_cert_chain(ROOT / 'work/lan-tls/server.pem', ROOT / 'work/lan-tls/server.key')
                await stack.enter_async_context(serve(relay.handle, settings['host'], 8767, ssl=context,
                    process_request=relay.authorize, max_size=64000, max_queue=8, close_timeout=2))
                phone_config.touch(mode=0o600, exist_ok=True)
                phone_config.chmod(0o600)
                phone_config.write_text(json.dumps({'url': f"wss://{settings['host']}:8767/stt", 'token': token,
                                                   'rootCertificate': settings['certificate']}))
            print(f'Development relay ready; {MAX_AUDIO_SECONDS}-second audio cap, {MAX_SESSIONS} attempt per process, {SESSION_TIMEOUT}-second wall timeout.', flush=True)
            await asyncio.Future()
    finally:
        CONFIG.unlink(missing_ok=True)
        phone_config.unlink(missing_ok=True)

if __name__ == '__main__':
    asyncio.run(main())
