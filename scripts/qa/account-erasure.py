#!/usr/bin/env python3
"""Local-only storage/session/socket replay. Never reads credentials or live data."""
import argparse
import asyncio
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Backend'))
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import InvalidStatus
from admission import Admission, Rejected
from account_tokens import GOOGLE, VerifiedIdentity
from account_sessions import AccountSessions
from account_erasure import erase_content
from companion_chat import CompanionChat
from memory_store import MemoryStore
from memory_service import MemoryService
from recording_notes import RecordingNotes
from relay import Relay


async def replay():
    results = {}
    with tempfile.TemporaryDirectory(prefix='ellis-erasure-qa-') as folder:
        folder = Path(folder)
        admission = Admission(folder / 'usage.sqlite', total_microusd=100, limits={'stt': (100, 20, 5)})
        try:
            store = MemoryStore(folder / 'memory.sqlite')
            accounts = AccountSessions(admission, store)
            def enroll(subject, suffix):
                challenge = accounts.challenge('google')
                return accounts.exchange(challenge['challenge'], 'google',
                    VerifiedIdentity(GOOGLE, subject, admission.clock() + 300), 'fictional-identity-token-' + suffix)
            first, other = enroll('fictional-a', 'a'), enroll('fictional-b', 'b')
            second_device = enroll('fictional-a', 'a-second-device')
            # A synthetic reservation exercises non-refundable history. No audio/API.
            reservation = admission.reserve(first['token'], 'stt')
            admission.finish(reservation, completed=True)
            usage_before = admission.db.execute('SELECT * FROM request').fetchall()
            source = dict(session_id='fictional-meeting', revision=1, captured_at=100., timezone='UTC', completed=True,
                          passages=[dict(id='p1', start=0., duration=2., text='Fictional Cedar meets at the pavilion.', speakers=[])])
            note = dict(title='Fictional Cedar', overview=dict(text='Meets at the pavilion.', passages=['p1']), sections=[])
            chat = CompanionChat(store)
            notes = RecordingNotes(store)
            relay = Relay('unused-no-provider', admission=admission, memory=MemoryService(admission, store))
            async with serve(relay.handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
                url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/memory'
                async def sync(account, *, owner=None):
                    async with connect(url, additional_headers={'Authorization': 'Bearer ' + account['token']}) as ws:
                        await ws.send(json.dumps(dict(version=1, operation='upsert', owner=owner or account['owner'], source=source)))
                        return json.loads(await ws.recv())
                for account in (first, other):
                    assert (await sync(account))['status'] == 'stored'
                    chat.start(account['owner'], 'question', 'Where is the fictional meeting?')
                    chat.complete(account['owner'], 'question', 'At the pavilion.')
                    notes.enqueue(account['owner'], source['session_id'], 1)
                    notes.complete(notes.claim(account['owner'], source['session_id']), note)
                assert (await sync(other, owner=first['owner']))['message'] == 'memory_owner_mismatch'
                results['populated_cross_owner_write_rejected'] = True
                other_chat = chat.page(other['owner'])
                other_notes = notes.read(other['owner'], source['session_id'])
                # Deliberate fixture orchestration, not a claimed deletion endpoint.
                accounts.sign_out(first['refresh_token'])
                accounts.sign_out(second_device['refresh_token'])
                erase_content(store, first['owner'])
                for account in (first, second_device):
                    try:
                        await sync(account)
                        raise AssertionError('Erased owner was authorized')
                    except InvalidStatus as error:
                        assert error.response.status_code == 401
                    try:
                        accounts.refresh(account['refresh_token'])
                        raise AssertionError('Erased owner refreshed')
                    except Rejected:
                        pass
                results['both_revoked_sessions_rejected_http_401_and_refresh'] = True
                assert (await sync(other))['status'] == 'unchanged'
                assert chat.page(other['owner']) == other_chat
                assert notes.read(other['owner'], source['session_id']) == other_notes
                assert store.source(other['owner'], source['session_id']) == source
                results['other_account_transcript_notes_and_chat_unchanged'] = True
                store = MemoryStore(store.path)
                with store.connect() as db:
                    for table in ('source', 'recording_notes', 'companion_turn', 'account_identity'):
                        assert db.execute(f'SELECT count(*) FROM {table} WHERE owner=?', (first['owner'],)).fetchone()[0] == 0
                    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
                results['content_and_provider_identity_absent_after_reopen'] = True
                assert admission.db.execute('SELECT * FROM request').fetchall() == usage_before
                results['reservation_rows_unchanged'] = True
                fresh = enroll('fictional-a', 'fresh')
                assert fresh['owner'] != first['owner']
                assert store.source(fresh['owner'], source['session_id']) is None
                assert CompanionChat(store).page(fresh['owner'])['turns'] == []
                results['fresh_provider_enrollment_has_new_empty_owner'] = True
        finally:
            admission.close()
    return dict(scope='local SQLite and WebSocket replay; synthetic identities and content',
                sqlite_version=sqlite3.sqlite_version, results=results, provider_calls=0,
                source_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in [ROOT / 'Backend/account_erasure.py', ROOT / 'Backend/memory_store.py', Path(__file__).resolve()]},
                not_proven=['deletion endpoint', 'provider revocation', 'native local erasure',
                            'operational backup retention', 'physical device', 'founder migration'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    receipt = asyncio.run(replay())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
