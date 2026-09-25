"""Single-instance internal service. Requires persistent storage and explicit caps."""
import asyncio
import fcntl
import json
from contextlib import suppress
import os
from pathlib import Path
from service_policy import open_ledger
from ask import AskService, Luna
from relay import Relay
from memory_store import MemoryStore
from profile_budget import ProfileBudget, APPROVAL_ID as PROFILE_APPROVAL_ID, ALLOCATION as PROFILE_ALLOCATION
from memory_service import MemoryService
from memory_budget import MemoryBudget, APPROVAL_ID, ALLOCATION
from memory_models import MemoryModels
from memory_writer import MemoryWriter, MemoryWorker
from memory_recall import MemoryRecall
from websockets.asyncio.server import serve


async def main():
    os.umask(0o077)
    directory = Path(os.environ['VOICE_DATA_DIR'])
    # Keep this descriptor open until all connections and the ledger are closed.
    with (directory / 'service.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        key = os.environ['XAI_API_KEY'].strip()
        if not key:
            raise ValueError('Missing provider key')
        store = open_ledger(migrate=True)
        learning_task = None
        try:
            store.recover_interrupted()
            answer_key = os.environ.get('OPENAI_API_KEY', '').strip()
            enabled = os.environ.get('VOICE_ENABLE_ASK') == '1'
            if enabled and not answer_key:
                raise ValueError('Ask enabled without provider credential')
            ask = AskService(store, Luna(answer_key)) if enabled else None
            personal_enabled = os.environ.get('VOICE_ENABLE_PERSONAL_LEARNING') == '1'
            if personal_enabled and os.environ.get('VOICE_ENABLE_MEMORY_LEARNING') != '1':
                raise ValueError('Personal learning requires memory learning')
            memory = None
            if os.environ.get('VOICE_ENABLE_MEMORY') == '1':
                memory_store = MemoryStore(directory / 'memory.sqlite', personal_learning=personal_enabled)
                memory_store.recover_jobs()
                memory_store.maintain()
                memory = MemoryService(store, memory_store)
            learning_enabled = os.environ.get('VOICE_ENABLE_MEMORY_LEARNING') == '1'
            recall_enabled = os.environ.get('VOICE_ENABLE_MEMORY_RECALL') == '1'
            if learning_enabled or recall_enabled:
                if memory is None or not answer_key or not os.environ.get('TYPESAFE_API_KEY'):
                    raise ValueError('Learning requires memory and both provider credentials')
                # Administrative receipt is provisioned separately; startup never grants itself spend.
                receipt = json.loads((directory / 'memory-allocation.json').read_text())
                allocation = store.db.execute('SELECT category,reserved FROM request WHERE id=?', (APPROVAL_ID,)).fetchone()
                if allocation is None or tuple(allocation) != ('jev', ALLOCATION):
                    raise ValueError('Learning allocation is not reserved in the global ledger')
                if not (directory / 'memory-budget.sqlite').exists():
                    raise ValueError('Transfer the canonical learning subledger before enablement')
                budget = MemoryBudget(directory / 'memory-budget.sqlite', receipt)
                if personal_enabled:
                    allocation = store.db.execute('SELECT category,reserved FROM request WHERE id=?', (PROFILE_APPROVAL_ID,)).fetchone()
                    if allocation is None or tuple(allocation) != ('ask', PROFILE_ALLOCATION):
                        raise ValueError('Profile QA allocation is not reserved')
                    budget = ProfileBudget(directory / 'memory-budget.sqlite')
                models = MemoryModels(answer_key, os.environ['TYPESAFE_API_KEY'])
                if learning_enabled:
                    writer = MemoryWriter(memory_store, models, budget)
                    learning_task = asyncio.create_task(MemoryWorker(writer, store).run())
                if recall_enabled:
                    if ask is None:
                        raise ValueError('Recall requires Ask enabled')
                    ask.recall = MemoryRecall(memory_store, models, budget)
            relay = Relay(key, admission=store, ask=ask, memory=memory)
            async with serve(relay.handle, '0.0.0.0', int(os.environ.get('PORT', '10000')),
                             process_request=relay.authorize, max_size=64000, max_queue=8,
                             close_timeout=2, server_header=None):
                print('Internal transcription service ready', flush=True)
                await asyncio.Future()
        finally:
            if learning_task is not None:
                learning_task.cancel()
                with suppress(asyncio.CancelledError):
                    await learning_task
            store.close()


if __name__ == '__main__':
    asyncio.run(main())
