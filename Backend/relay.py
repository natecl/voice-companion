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
from pathlib import Path
from websockets.asyncio.server import serve
from websockets.asyncio.client import connect

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'work/relay-client.json'
URL = ('wss://api.x.ai/v1/stt?model=grok-voice-transcribe-2.0&sample_rate=16000'
       '&encoding=pcm&interim_results=true&diarize=true&language=en')
MAX_BYTES = 60 * 32000

class Relay:
    def __init__(self, key, token):
        self.key, self.token = key, token
        self.active = False
        self.total_bytes = 0
        self.sessions = 0

    def authorize(self, connection, request):
        if request.path == '/health':
            return connection.respond(http.HTTPStatus.OK, 'ready\n')
        if request.path != '/stt':
            return connection.respond(http.HTTPStatus.NOT_FOUND, 'Not found\n')
        supplied = request.headers.get('Authorization', '')
        if not hmac.compare_digest(supplied, 'Bearer ' + self.token):
            return connection.respond(http.HTTPStatus.UNAUTHORIZED, 'Unauthorized\n')
        if self.active or self.sessions >= 3 or self.total_bytes >= MAX_BYTES * 3:
            return connection.respond(http.HTTPStatus.TOO_MANY_REQUESTS, 'Development limit reached\n')

    async def handle(self, client):
        # Recheck after handshake to avoid two accepted clients racing.
        if self.active or self.sessions >= 3 or self.total_bytes >= MAX_BYTES * 3:
            await client.close(1008, 'Development limit reached')
            return
        self.active = True
        self.sessions += 1
        started, sent = time.monotonic(), 0
        status = 'incomplete'
        try:
            async with asyncio.timeout(70):
                async with connect(URL, additional_headers={'Authorization': 'Bearer ' + self.key},
                                   open_timeout=10, close_timeout=2, max_size=2**20) as upstream:
                    async def send_audio():
                        nonlocal sent
                        async for packet in client:
                            if isinstance(packet, bytes):
                                if len(packet) % 2 or sent + len(packet) > MAX_BYTES or self.total_bytes + len(packet) > MAX_BYTES * 3:
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

                    outgoing = asyncio.create_task(send_audio())
                    incoming = asyncio.create_task(receive_events())
                    try:
                        done, _ = await asyncio.wait([outgoing, incoming], return_when=asyncio.FIRST_COMPLETED)
                        for task in done:
                            task.result()
                        if incoming not in done:
                            await asyncio.wait_for(incoming, timeout=10)
                        status = 'completed'
                    finally:
                        for task in (outgoing, incoming):
                            if not task.done(): task.cancel()
                        await asyncio.gather(outgoing, incoming, return_exceptions=True)
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
            print('Development relay ready; 60-second sessions, three-session / 180-second process cap.', flush=True)
            await asyncio.Future()
    finally:
        CONFIG.unlink(missing_ok=True)
        phone_config.unlink(missing_ok=True)

if __name__ == '__main__':
    asyncio.run(main())
