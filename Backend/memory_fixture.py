"""Local native integration fixture. Synthetic content only; never calls a provider."""
import asyncio
import json
import os
from pathlib import Path
import sys
from websockets.asyncio.server import serve
from admission import Admission
from memory_store import MemoryStore
from memory_service import MemoryService
from relay import Relay


async def main(directory):
    os.umask(0o077)
    directory.mkdir(parents=True, exist_ok=True)
    ledger = Admission(directory/'usage.sqlite', total_microusd=100, limits={'stt': (100,20,6)})
    try:
        store = MemoryStore(directory/'memory.sqlite')
        store.recover_jobs()
        credentials = directory/'fixture-credential.json'
        if credentials.exists():
            identifier, token = json.loads(credentials.read_text())
        else:
            identifier, token = ledger.enroll()
            credentials.write_text(json.dumps([identifier, token]))
        owner = store.owner_for(identifier)
        relay = Relay('never-used', admission=ledger, memory=MemoryService(ledger, store))
        async def handle(socket):
            await relay.handle(socket)
            with store.connect() as db:
                rows = [dict(r) for r in db.execute('SELECT session,revision,deleted,payload FROM source WHERE owner=?', (owner,))]
            report = {'sources': rows, 'usage': ledger.usage(), 'diagnostics': store.diagnostics(owner)}
            temp = directory/'report.tmp'
            temp.write_text(json.dumps(report))
            temp.replace(directory/'report.json')
        async with serve(handle, '127.0.0.1', 0, process_request=relay.authorize, max_size=64000) as server:
            port = server.sockets[0].getsockname()[1]
            config = {'url': f'ws://127.0.0.1:{port}/stt', 'token': token, 'memoryOwnerID': owner}
            temp = directory/'config.tmp'
            temp.write_text(json.dumps(config))
            temp.replace(directory/'config.json')
            await asyncio.Future()
    finally:
        ledger.close()


if __name__ == '__main__': asyncio.run(main(Path(sys.argv[1])))
