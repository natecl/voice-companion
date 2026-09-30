#!/usr/bin/env python3
"""Local real-provider lifecycle QA. Never opens hosted data or enables model spending.

Requires explicit readiness before interactive authentication/deletion. Private
output directory contains real local QA account data; never commit that directory.
"""
import argparse
import asyncio
from collections import Counter
import json
import os
from pathlib import Path
import plistlib
import signal
import sys
import threading

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Backend'))
from cryptography.fernet import Fernet
from websockets.asyncio.server import serve
from account_service import configured_accounts
from account_tls import certificate
from admission import Admission, Rejected
from companion_service import CompanionService
from memory_service import MemoryService
from memory_store import MemoryStore
from notes_service import NotesService
from relay import Relay


class AccountQAAdmission(Admission):
    def reserve(self, *args, **kwargs):
        raise Rejected('qa_generation_disabled')


async def main(output, apple_key):
    os.umask(0o077)
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    if (output/'usage.sqlite').exists():
        raise RuntimeError('Use a fresh private directory; existing account QA data is preserved')
    context = certificate(output)
    key = Fernet.generate_key()
    (output/'encryption.key').write_bytes(key)
    phone = plistlib.loads((ROOT/'App/Phone-Info.plist').read_bytes())
    mac = plistlib.loads((ROOT/'App/Mac-Info.plist').read_bytes())
    admission = AccountQAAdmission(output/'usage.sqlite', total_microusd=1, limits={'stt': (100,20,5), 'ask': (100,20,5)})
    memory = MemoryStore(output/'memory.sqlite')
    env = dict(VOICE_ENABLE_ACCOUNTS='1', VOICE_ENABLE_ACCOUNT_DELETION='1',
               VOICE_GOOGLE_SERVER_CLIENT_ID=phone['GIDServerClientID'],
               VOICE_GOOGLE_NATIVE_CLIENT_IDS=','.join([phone['GIDClientID'], mac['GIDClientID']]),
               VOICE_APPLE_CLIENT_IDS='ai.voicecompanion.phone,ai.voicecompanion.mac',
               VOICE_APPLE_TEAM_ID='7HF6VDCZF7', VOICE_APPLE_KEY_ID='6JCPHWJT4A',
               VOICE_APPLE_PRIVATE_KEY=apple_key.read_text(), VOICE_ACCOUNT_ENCRYPTION_KEY=key.decode())
    accounts = configured_accounts(env, admission, memory)
    calls, call_lock = Counter(), threading.Lock()
    def instrument(provider, method, label):
        original = getattr(provider, method)
        def invoke(*args, **kwargs):
            try:
                result = original(*args, **kwargs)
            except Exception:
                with call_lock: calls[label+'.failed'] += 1
                raise
            with call_lock: calls[label+'.ok'] += 1
            return result
        setattr(provider, method, invoke)
    for method in ('redeem', 'validate_refresh', 'revoke'): instrument(accounts.apple_oauth, method, 'apple.'+method)
    instrument(accounts.deletion.google, 'revoke', 'google.revoke')
    relay = Relay('unused-no-transcription-provider', admission=admission, accounts=accounts,
                  memory=MemoryService(admission, memory), notes=NotesService(admission, memory),
                  companion=CompanionService(admission, memory, provider=None))
    def snapshot():
        with memory.connect() as db:
            identities = {('google' if issuer == 'https://accounts.google.com' else 'apple'): count
                          for issuer, count in db.execute('SELECT issuer,count(*) FROM account_identity GROUP BY issuer')}
            schema = db.execute('PRAGMA user_version').fetchone()[0]
        with call_lock: provider_calls = dict(calls)
        result = dict(scope='isolated local real-provider QA', identity_counts=identities, schema=schema,
                      sessions=admission.db.execute('SELECT count(*) FROM account_session').fetchone()[0],
                      unrevoked_sessions=admission.db.execute('SELECT count(*) FROM account_session s JOIN credential c ON c.id=s.credential WHERE c.revoked=0').fetchone()[0],
                      deletions=dict(admission.db.execute('SELECT state,count(*) FROM account_deletion GROUP BY state').fetchall()),
                      provider_calls=provider_calls, model_spending_enabled=False)
        (output/'status.json').write_text(json.dumps(result, indent=2)+'\n')
    async def handle(socket):
        await relay.handle(socket)
        snapshot()
    stopped = asyncio.Event()
    for sig in (signal.SIGINT, signal.SIGTERM): asyncio.get_running_loop().add_signal_handler(sig, stopped.set)
    try:
        async with serve(handle, '127.0.0.1', 0, ssl=context, process_request=relay.authorize) as server:
            endpoint = f'wss://127.0.0.1:{server.sockets[0].getsockname()[1]}/account'
            (output/'endpoint.txt').write_text(endpoint+'\n')
            snapshot()
            print('Ready: local real-provider service; generation reservations disabled; waiting for explicit user readiness', flush=True)
            await stopped.wait()
    finally:
        snapshot()
        admission.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--apple-key', type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(main(args.output, args.apple_key))
