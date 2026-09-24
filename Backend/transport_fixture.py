"""Loopback-only WebSocket fault fixture. Never connects to any external service."""
import asyncio
import json
import http
from pathlib import Path
import sys
from websockets.asyncio.server import serve

async def main():
    port_file, report_file = map(Path, sys.argv[1:])
    async def handle(socket):
        report = {'connected': True, 'closed': False, 'audio_bytes': 0, 'audio_done': False}
        def save():
            temporary = report_file.with_suffix('.tmp')
            temporary.write_text(json.dumps(report))
            temporary.replace(report_file)
        save()
        mode = socket.request.path
        try:
            if mode in ('/ready-timeout', '/stop-connecting'):
                await socket.wait_closed()
                return
            await socket.send(json.dumps({'type': 'transcript.created'}))
            if mode == '/premature':
                await socket.send(json.dumps({'type': 'transcript.done'}))
                await socket.wait_closed()
                return
            async for packet in socket:
                if isinstance(packet, bytes):
                    report['audio_bytes'] += len(packet)
                    save()
                    await socket.send(json.dumps({'type': 'transcript.partial', 'text': 'Preserved fixture words',
                                                  'start': 0, 'duration': 1}))
                    if mode == '/drop':
                        socket.transport.abort()
                        return
                    if mode == '/error':
                        await socket.send(json.dumps({'type': 'error', 'message': 'Fixture provider failure'}))
                        await socket.wait_closed()
                        return
                else:
                    assert json.loads(packet) == {'type': 'audio.done'}
                    report['audio_done'] = True
                    save()
                    if mode == '/complete':
                        await socket.send(json.dumps({'type': 'transcript.done'}))
                    await socket.wait_closed()
                    return
        finally:
            report['closed'] = True
            save()
    def authorize(connection, request):
        if request.path == '/reject':
            report_file.write_text(json.dumps({'connected': False, 'closed': True, 'audio_bytes': 0}))
            return connection.respond(http.HTTPStatus.UNAUTHORIZED, 'Fixture rejected authorization\n')

    async with serve(handle, '127.0.0.1', 0, process_request=authorize) as server:
        port_file.write_text(str(server.sockets[0].getsockname()[1]))
        await asyncio.Future()

if __name__ == '__main__':
    asyncio.run(main())
