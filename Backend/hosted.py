"""Single-instance internal service. Requires persistent storage and explicit caps."""
import asyncio
import fcntl
import os
from pathlib import Path
from admission import Admission
from relay import Relay
from websockets.asyncio.server import serve


async def main():
    os.umask(0o077)
    directory = Path(os.environ['VOICE_DATA_DIR'])
    directory.mkdir(parents=True, exist_ok=True)
    # Keep this descriptor open until all connections and the ledger are closed.
    with (directory / 'service.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        key = os.environ['XAI_API_KEY'].strip()
        if not key:
            raise ValueError('Missing provider key')
        store = Admission(directory / 'usage.sqlite',
                          total_microusd=int(os.environ['VOICE_STT_BUDGET_MICROUSD']),
                          limits={'stt': (int(os.environ['VOICE_STT_BUDGET_MICROUSD']), 20000, 6)})
        try:
            store.recover_interrupted()
            relay = Relay(key, admission=store)
            async with serve(relay.handle, '0.0.0.0', int(os.environ.get('PORT', '10000')),
                             process_request=relay.authorize, max_size=64000, max_queue=8,
                             close_timeout=2, server_header=None):
                print('Internal transcription service ready', flush=True)
                await asyncio.Future()
        finally:
            store.close()


if __name__ == '__main__':
    asyncio.run(main())
