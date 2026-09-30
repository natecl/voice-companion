#!/usr/bin/env python3
"""Exercise local account refresh with real enrolled providers; no token output.

Creates separate synthetic app-session families for existing real QA identities.
Never reads native Keychain or changes the app's original sessions. One refresh
per provider, no automatic retries. Requires the real-account-server directory.
"""
import argparse
import asyncio
import json
from pathlib import Path
import ssl
import sys
from urllib.parse import urlparse
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Backend'))
from account_sessions import AccountSessions
from admission import Admission
from memory_store import MemoryStore
from websockets.asyncio.client import connect


async def run(directory, output):
    endpoint = (directory / 'endpoint.txt').read_text().strip()
    parsed = urlparse(endpoint)
    assert parsed.scheme == 'wss' and parsed.hostname == '127.0.0.1'
    assert parsed.path == '/account' and not parsed.username and not parsed.query
    context = ssl.create_default_context(cafile=str(directory / 'cert.pem'))
    assert (directory / 'usage.sqlite').is_file()
    assert (directory / 'memory.sqlite').is_file()
    admission = Admission(directory / 'usage.sqlite', total_microusd=1,
                          limits={'stt': (100, 20, 5), 'ask': (100, 20, 5)})
    memory = MemoryStore(directory / 'memory.sqlite')
    sessions = AccountSessions(admission, memory)
    existing = dict(admission.db.execute('SELECT id,revoked FROM credential'))
    families, results = [], {}

    async def refresh(token):
        async with connect(endpoint, ssl=context, open_timeout=5) as socket:
            await socket.send(json.dumps(dict(version=1, operation='refresh', refresh_token=token)))
            return json.loads(await asyncio.wait_for(socket.recv(), timeout=15))

    try:
        with memory.connect() as db:
            identities = list(db.execute('SELECT issuer,owner FROM account_identity'))
        assert len(identities) == 2, 'Expected the two real QA identities'
        for issuer, owner in identities:
            provider = {'https://accounts.google.com': 'google', 'https://appleid.apple.com': 'apple'}[issuer]
            family = str(uuid.uuid4())
            families.append(family)
            with admission.transaction():
                credential, access = admission.enroll(lifetime_seconds=1)
                memory.owner_for(credential, existing_owner=owner)
                original = sessions._session(credential, access, owner, family, admission.clock()+3600)
                admission.db.execute('UPDATE credential SET expires=0 WHERE id=?', (credential,))
            rotated = await refresh(original['refresh_token'])
            assert rotated.get('type') == 'account_result', 'Refresh failed; inspect sanitized server status'
            assert rotated['owner'] == owner
            assert rotated['refresh_token'] != original['refresh_token']
            assert admission.authorized(rotated['token'])
            replay = await refresh(original['refresh_token'])
            assert replay == {'type': 'error', 'message': 'refresh_replayed'}
            rejected = await refresh(rotated['refresh_token'])
            assert rejected == {'type': 'error', 'message': 'unauthorized'}
            results[provider] = dict(expired_access_refreshed=True, owner_preserved=True,
                                     refresh_rotated=True, replay_revoked_family=True)
        now = dict(admission.db.execute('SELECT id,revoked FROM credential'))
        assert all(now[key] == value for key, value in existing.items())
        receipt = dict(scope='localhost TLS backend with real provider grants and synthetic app sessions',
                       results=results, preexisting_sessions_unchanged=True,
                       paid_calls=0, limitations=['Not native timer/Keychain refresh acceptance',
                       'Google app refresh does not contact Google; Apple validates its stored real grant'])
        output.write_text(json.dumps(receipt, indent=2)+'\n')
        print(json.dumps(receipt, indent=2))
    finally:
        with admission.transaction():
            for family in families:
                sessions._revoke_family(family)
        admission.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(run(args.directory, args.output))
