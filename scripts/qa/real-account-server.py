#!/usr/bin/env python3
"""Local real-provider lifecycle QA. Never opens hosted data or enables model spending.

Requires explicit readiness before interactive authentication/deletion. Private
output directory contains real local QA account data; never commit that directory.
"""
import argparse
import asyncio
from collections import Counter
from contextlib import closing
import json
import fcntl
import ssl
import sqlite3
from urllib.parse import urlparse
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
from memory_store import MemoryStore, VERSION as MEMORY_VERSION
from notes_service import NotesService
from relay import Relay


class AccountQAAdmission(Admission):
    def reserve(self, *args, **kwargs):
        raise Rejected('qa_generation_disabled')


def validate_resume_databases(output):
    """Refuse empty/damaged/wrong-schema state before constructors can create it.

    This verifies an existing QA schema, not a backup identity or a migration.
    The caller holds server.lock; no read-write database is opened here.
    """
    required = {
        'usage.sqlite': {
            'budget': {'id', 'cap'},
            'policy': {'category', 'cap', 'reservation', 'daily'},
            'credential': {'id', 'digest', 'expires', 'revoked'},
            'request': {'id', 'credential_id', 'category', 'started', 'reserved', 'state'},
            'account_challenge': {'digest', 'provider', 'expires'},
            'account_exchange': {'digest', 'expires'},
            'account_session': {'credential', 'family', 'owner', 'refresh_digest', 'refresh_expires', 'consumed'},
            'apple_grant': {'owner', 'client', 'ciphertext'},
            'account_deletion': {'owner', 'request_digest', 'state'},
            'deletion_recovery': {'owner', 'digest'},
            'google_deletion': {'owner', 'content_erased'},
            'deleting_identity': {'digest', 'owner'},
        },
        'memory.sqlite': {
            'owner': {'id'},
            'credential_owner': {'credential', 'owner'},
            'account_identity': {'issuer', 'subject', 'owner'},
            'source': {'owner', 'session', 'revision', 'digest', 'payload', 'deleted'},
            'erased_account': {'owner', 'erased_at'},
            'erased_account_credential': {'credential', 'owner'},
        },
    }
    for name, tables in required.items():
        path = (output / name).absolute()
        try:
            with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
                if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                    raise ValueError('integrity')
                if name == 'memory.sqlite' and db.execute('PRAGMA user_version').fetchone()[0] != MEMORY_VERSION:
                    raise ValueError('version')
                existing = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not tables.keys() <= existing:
                    raise ValueError('tables')
                for table, columns in tables.items():
                    # Table names are the fixed identifiers above, never input.
                    if not columns <= {row[1] for row in db.execute(f'PRAGMA table_info({table})')}:
                        raise ValueError('columns')
                if db.execute('PRAGMA foreign_key_check').fetchone() is not None:
                    raise ValueError('foreign keys')
        except (sqlite3.DatabaseError, ValueError):
            raise RuntimeError(f'Resume requires an intact existing QA schema: {name}') from None


async def main(output, apple_key, resume=False):
    os.umask(0o077)
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    with (output/'server.lock').open('a') as process_lock:
        fcntl.flock(process_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        await run_locked(output, apple_key, resume)


async def run_locked(output, apple_key, resume):
    port = 0
    previous_calls = {}
    if resume:
        for name in ('usage.sqlite', 'memory.sqlite', 'cert.pem', 'key.pem', 'encryption.key', 'endpoint.txt', 'status.json'):
            path = output/name
            if path.is_symlink() or not path.is_file():
                raise RuntimeError('Resume requires intact original QA files')
        validate_resume_databases(output)
        endpoint = urlparse((output/'endpoint.txt').read_text().strip())
        if (endpoint.scheme, endpoint.hostname, endpoint.path) != ('wss', '127.0.0.1', '/account') or not endpoint.port or endpoint.username or endpoint.password or endpoint.query or endpoint.fragment:
            raise RuntimeError('Invalid original localhost endpoint')
        port = endpoint.port
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(output/'cert.pem', output/'key.pem')
        key = (output/'encryption.key').read_bytes()
        Fernet(key)
        previous = json.loads((output/'status.json').read_text())
        if previous.get('scope') != 'isolated local real-provider QA' or previous.get('model_spending_enabled') is not False:
            raise RuntimeError('Unrecognized QA state')
        previous_calls = previous['provider_calls']
        if not isinstance(previous_calls, dict) or any(type(v) is not int or v < 0 for v in previous_calls.values()):
            raise RuntimeError('Invalid provider call counters')
    else:
        if (output/'usage.sqlite').exists():
            raise RuntimeError('Use --resume to preserve an existing QA service')
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
    calls, call_lock = Counter(previous_calls), threading.Lock()
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
        async with serve(handle, '127.0.0.1', port, ssl=context, process_request=relay.authorize) as server:
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
    parser.add_argument('--resume', action='store_true', help='Reuse original databases, keys, certificate, counters and port')
    args = parser.parse_args()
    asyncio.run(main(args.output, args.apple_key, args.resume))
