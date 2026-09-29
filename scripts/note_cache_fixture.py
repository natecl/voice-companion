#!/usr/bin/env python3
"""Fictional loopback cache QA only; never forwards to paid providers.

Use a fresh /tmp/voice-note-cache-qa directory. Run populate first; stop it
before offline tests, then use read to serve the same owner/token/port.
"""
import argparse
import asyncio
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
BASE = Path('/tmp/voice-note-cache-qa')
sys.path.insert(0, str(ROOT / 'Backend'))

async def read_server():
    from websockets.asyncio.server import serve
    from admission import Admission
    from memory_store import MemoryStore
    from notes_service import NotesService
    from memory_service import MemoryService
    from companion_service import CompanionService
    from companion_fixture import Provider  # Fixed fictional output; no model client.
    config = json.loads((BASE / 'config.json').read_text())
    url = urlparse(config['url'])
    assert url.scheme == 'ws' and url.hostname == '127.0.0.1' and url.path == '/stt'
    ledger = Admission(BASE / 'usage.sqlite', total_microusd=30000, limits={'ask': (30000, 3000, 20)})
    store = MemoryStore(BASE / 'memory.sqlite')
    notes = NotesService(ledger, store)
    memory = MemoryService(ledger, store, generate_notes=False)
    companion = CompanionService(ledger, store, Provider())
    async def handle(socket):
        if socket.request.path == '/notes':
            while (BASE / 'hold-update').exists() and not (BASE / 'release-update').exists():
                await asyncio.sleep(.05)
            await asyncio.sleep(.2)
            class ObservedSocket:
                request = socket.request
                async def recv(self): return await socket.recv()
                async def close(self): await socket.close()
                async def send(self, raw):
                    response = json.loads(raw)
                    with (BASE / 'notes-responses.jsonl').open('a') as log:
                        log.write(json.dumps({key: response[key] for key in ('type', 'message', 'revision') if key in response}) + '\n')
                    await socket.send(raw)
            await notes.handle(ObservedSocket())
        elif socket.request.path == '/memory':
            await memory.handle(socket)
        else:
            await companion.handle(socket)
    async with serve(handle, '127.0.0.1', url.port, max_size=64000):
        await asyncio.Future()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['populate', 'read', 'update', 'outdated', 'ready', 'stage', 'source-revision', 'source-delete'])
    parser.add_argument('--stage', help='Exact UI test method name; only that staged test runs')
    args = parser.parse_args()
    BASE.mkdir(exist_ok=True)
    if args.stage:
        (BASE / 'stage.txt').write_text(args.stage)
    if args.mode == 'populate':
        if (BASE / 'config.json').exists():
            parser.error('Use a fresh fixture directory; move prior QA evidence aside first.')
        subprocess.run([sys.executable, str(ROOT / 'Backend/companion_fixture.py'), str(BASE), '--ui', '--notes'], check=True)
    elif args.mode == 'read':
        asyncio.run(read_server())
    elif args.mode in ('source-revision', 'source-delete'):
        from memory_store import MemoryStore
        store = MemoryStore(BASE / 'memory.sqlite')
        with store.connect() as db:
            sources = [(row['owner'], json.loads(row['payload'])) for row in db.execute('SELECT owner,payload FROM source WHERE deleted=0')]
        for owner, source in sources:
            if args.mode == 'source-delete':
                store.delete_source(owner, source['session_id'])
            else:
                source['revision'] += 1
                store.put_source(owner, source, generate_notes=False, learn=False)
    elif args.mode in ('update', 'outdated', 'ready'):
        if args.mode == 'update':
            (BASE / 'release-update').unlink(missing_ok=True)
            (BASE / 'hold-update').touch()
        # Fixed path belongs only to this fictional fixture; no configurable database path.
        with sqlite3.connect(BASE / 'memory.sqlite') as db:
            if args.mode == 'outdated':
                db.execute("UPDATE recording_notes SET state='outdated',payload=NULL,error='source_changed'")
            else:
                text = 'Maya enjoys swimming.' + (' Updated saved fixture.' if args.mode == 'update' else '')
                payload = dict(title='Maya’s updated swimming note' if args.mode == 'update' else 'Maya’s swimming', overview=dict(text=text, passages=['p1']), sections=[])
                db.execute("UPDATE recording_notes SET state='ready',payload=?,error=NULL", (json.dumps(payload),))

if __name__ == '__main__':
    main()
