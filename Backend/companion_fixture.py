"""Native socket QA: actual service/storage, synthetic provider, no external calls."""
import asyncio
import json
import os
from pathlib import Path
import sys
from websockets.asyncio.server import serve
from admission import Admission
from companion_service import CompanionService
from memory_store import MemoryStore

class Provider:
    async def stream(self, data):
        yield dict(type='delta', text='Maya swims. [[p1]]' if data['sources'] else 'Hello from the saved companion.')
        if data['question']=='Wait forever':await asyncio.Future()
        yield dict(type='completed')

async def main(directory):
    os.umask(0o077)
    ledger = Admission(directory/'usage.sqlite', total_microusd=30000, limits={'ask':(30000,3000,20)})
    credential, token = ledger.enroll()
    store = MemoryStore(directory/'memory.sqlite')
    service = CompanionService(ledger, store, Provider())
    async with serve(service.handle, '127.0.0.1', 0, max_size=64000) as server:
        config = dict(url=f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/stt', token=token,
                      memoryOwnerID=store.owner_for(credential))
        temp = directory/'config.tmp'
        temp.write_text(json.dumps(config));temp.replace(directory/'config.json')
        await asyncio.Future()

if __name__ == '__main__': asyncio.run(main(Path(sys.argv[1])))
