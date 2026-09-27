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


def rework_settings(env):
    names=('VOICE_ENABLE_MEMORY_REWORK','VOICE_ENABLE_COMPANION','VOICE_ENABLE_SEMANTIC_INDEX')
    if any(env.get(name,'0') not in ('0','1') for name in names):raise ValueError('Invalid rework feature flag')
    rework,companion,semantic=(env.get(name)=='1' for name in names)
    if rework and any(env.get(name)!='1' for name in ('VOICE_ENABLE_MEMORY','VOICE_ENABLE_PERSONAL_LEARNING',
            'VOICE_ENABLE_MEMORY_LEARNING','VOICE_ENABLE_MEMORY_RECALL','VOICE_ENABLE_ASK')):
        raise ValueError('Memory rework requires memory, personal learning, learning, recall and Ask')
    if (companion or semantic) and not rework:raise ValueError('Companion and semantic indexing require memory rework')
    if semantic and not env.get('VOICE_EMBEDDING_CACHE'):raise ValueError('Semantic indexing requires a prewarmed cache')
    return rework,companion,semantic


def independent_verification_setting(env, rework_enabled):
    value=env.get('VOICE_ENABLE_INDEPENDENT_VERIFICATION','0')
    if value not in ('0','1') or (value=='1' and not rework_enabled):
        raise ValueError('Independent verification requires memory rework')
    return value=='1'


def retention_setting(env, companion_enabled):
    value=env.get('VOICE_RETAIN_RECORDING_MEMORIES','0')
    if value not in ('0','1') or (value=='1' and not companion_enabled):
        raise ValueError('Recording memory retention requires companion mode')
    return value=='1'


def notes_setting(env):
    value=env.get('VOICE_ENABLE_RECORDING_NOTES','0')
    if value not in ('0','1') or (value=='1' and env.get('VOICE_ENABLE_MEMORY')!='1'):
        raise ValueError('Recording notes require memory storage')
    return value=='1'


def notes_recall_setting(env):
    value=env.get('VOICE_ENABLE_NOTES_RECALL','0')
    required=('VOICE_ENABLE_RECORDING_NOTES','VOICE_ENABLE_MEMORY_REWORK','VOICE_ENABLE_MEMORY_RECALL')
    if value not in ('0','1') or (value=='1' and any(env.get(key)!='1' for key in required)):
        raise ValueError('Notes recall requires notes, memory rework and recall')
    return value=='1'


def validate_rework_allocations(admission, *, rollout=False, verification=False):
    import profile_budget as profile
    allocations=[(profile.REWORK_APPROVAL_ID,profile.REWORK_ALLOWANCE),
            (profile.CONSOLIDATION_APPROVAL_ID,profile.CONSOLIDATION_ALLOWANCE),
            (profile.MULTISOURCE_APPROVAL_ID,profile.MULTISOURCE_ALLOWANCE)]
    if rollout:allocations.append((profile.ROLLOUT_APPROVAL_ID,profile.ROLLOUT_ALLOWANCE))
    if verification:
        if not rollout:raise ValueError("Verification requires rollout allocation")
        allocations.append((profile.PREFERENCE_APPROVAL_ID,profile.PREFERENCE_ALLOWANCE))
        row=admission.db.execute("SELECT category,reserved FROM request WHERE id=?",(profile.VERIFICATION_APPROVAL_ID,)).fetchone()
        if row is None or tuple(row)!=("stt",profile.VERIFICATION_ALLOWANCE):
            raise ValueError("Verification rollout allocation is not reserved")
    for approval,amount in allocations:
        rows=admission.db.execute('SELECT category,reserved FROM request WHERE id IN (?,?,?)',
            (approval,approval+':ask',approval+':jev')).fetchall()
        if not rows or any(row[0] not in ('ask','jev') for row in rows) or sum(row[1] for row in rows)!=amount:
            raise ValueError('Rework allocation is not reserved in the global ledger')


async def main():
    notes_enabled=notes_setting(os.environ)
    notes_recall_enabled=notes_recall_setting(os.environ)
    rework_enabled,companion_enabled,semantic_enabled=rework_settings(os.environ)
    independent_verification=independent_verification_setting(os.environ,rework_enabled)
    retain_recording_memories=retention_setting(os.environ,companion_enabled)
    rollout_qa=os.environ.get('VOICE_ENABLE_ROLLOUT_QA','0')
    if rollout_qa not in ('0','1') or (rollout_qa=='1' and not rework_enabled):
        raise ValueError('Rollout QA requires memory rework')
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
        learning_worker = None
        indexing_worker = None
        indexing_task = None
        embedder = None
        companion = None
        notes = None
        notes_task = None
        notes_worker = None
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
            if notes_enabled and not answer_key:raise ValueError("Notes require provider credential")
            if notes_enabled:
                from notes_budget import NotesBudget
                notes_budget=NotesBudget(directory/"notes-budget.sqlite",store)
            memory = None
            if os.environ.get('VOICE_ENABLE_MEMORY') == '1':
                if semantic_enabled:
                    from local_embeddings import LocalEmbeddings
                    # Loading is explicitly enabled; startup cannot download model files.
                    embedder=await asyncio.to_thread(LocalEmbeddings,os.environ['VOICE_EMBEDDING_CACHE'],offline=True)
                memory_store = MemoryStore(directory / 'memory.sqlite', personal_learning=personal_enabled,
                    embedding_model=embedder.contract if embedder else None,
                    retain_recording_memories=retain_recording_memories)
                memory_store.recover_jobs()
                memory_store.maintain()
                memory = MemoryService(store, memory_store, generate_notes=notes_enabled)
                if notes_enabled:
                    from notes_generation import NotesGenerator
                    from notes_service import NotesService, NotesWorker
                    notes=NotesService(store,memory_store)
                    notes.notes.recover_interrupted()
                    notes_worker=NotesWorker(NotesGenerator(memory_store,MemoryModels(answer_key,"").extract,notes_budget),store)
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
                    if rework_enabled:validate_rework_allocations(store,rollout=rollout_qa=='1',verification=independent_verification)
                    budget = ProfileBudget(directory / 'memory-budget.sqlite',include_rework_allowance=rework_enabled,
                        include_consolidation_allowance=rework_enabled,include_multisource_allowance=rework_enabled,include_rollout_allowance=rollout_qa=='1',
                        independent_source_verification=independent_verification,
                        include_preference_allowance=independent_verification,include_verification_allowance=independent_verification)
                models = MemoryModels(answer_key, os.environ['TYPESAFE_API_KEY'])
                if learning_enabled:
                    if rework_enabled:
                        from memory_evidence_writer import EvidenceWriter
                        writer=EvidenceWriter(memory_store,models,budget,chunking=True,semantic_boundaries=True,
                            expiry=True,consolidation=True,independent_source_verification=independent_verification)
                    else:writer = MemoryWriter(memory_store, models, budget)
                    learning_worker = MemoryWorker(writer, store)

                if recall_enabled:
                    if ask is None:
                        raise ValueError('Recall requires Ask enabled')
                    if rework_enabled:
                        from indexed_recall import IndexedMemoryRecall
                        if notes_recall_enabled:
                            if not notes_enabled:raise ValueError('Notes recall requires notes generation enabled')
                            from notes_recall import NotesFirstRecall
                            ask.recall=NotesFirstRecall(memory_store,models,budget,embedder)
                        else:ask.recall=IndexedMemoryRecall(memory_store,models,budget,embedder,multi_source=True)
                    else:ask.recall = MemoryRecall(memory_store, models, budget)
            if semantic_enabled:
                from memory_indexing import IndexWorker
                indexing_worker=IndexWorker(memory_store,embedder,store)
                indexing_worker.recover()

            if companion_enabled:
                from companion_service import CompanionService
                companion=CompanionService(store,memory_store,Luna(answer_key),ask.recall)
                companion.chat.recover_interrupted()
            relay = Relay(key, admission=store, ask=ask, memory=memory,
                          learning_status=learning_worker.status if learning_worker else None,companion=companion,
                          indexing_status=indexing_worker.status if indexing_worker else None, notes=notes,
                          notes_status=notes_worker.status if notes_worker else None)
            if notes_worker:notes_worker.busy=lambda: relay.active
            async with serve(relay.handle, '0.0.0.0', int(os.environ.get('PORT', '10000')),
                             process_request=relay.authorize, max_size=64000, max_queue=8,
                             close_timeout=2, server_header=None):
                if notes_worker:notes_task=asyncio.create_task(notes_worker.run())
                if learning_worker:learning_task=asyncio.create_task(learning_worker.run())
                if indexing_worker:indexing_task=asyncio.create_task(indexing_worker.run())
                print('Internal transcription service ready', flush=True)
                await asyncio.Future()
        finally:
            if notes_task is not None:
                notes_task.cancel()
                with suppress(asyncio.CancelledError):await notes_task
            if indexing_task is not None:
                indexing_task.cancel()
                with suppress(asyncio.CancelledError):await indexing_task
            if learning_task is not None:
                learning_task.cancel()
                with suppress(asyncio.CancelledError):
                    await learning_task
            store.close()


if __name__ == '__main__':
    asyncio.run(main())
