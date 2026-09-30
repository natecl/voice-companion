#!/usr/bin/env python3
"""Isolated TLS account service for native deletion QA; all identities/providers are fictional."""
import argparse
import asyncio
from datetime import datetime, timedelta, timezone
import ipaddress
import json
from pathlib import Path
import signal
import ssl
import sys
import tempfile
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'Backend'))
from cryptography import x509
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
from websockets.asyncio.server import serve
from account_tokens import GOOGLE, VerifiedIdentity
from account_sessions import AccountSessions
from account_deletion import AccountDeletion
from account_service import AccountService
from admission import Admission, Rejected
from memory_store import MemoryStore
from provider_grants import ProviderGrants
from relay import Relay
from test_memory import source


def certificate(folder):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Ellis fictional local QA')])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now-timedelta(minutes=1))
            .not_valid_after(now+timedelta(days=1)).add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False).sign(key, hashes.SHA256()))
    (folder/'cert.pem').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (folder/'key.pem').write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    (folder/'key.pem').chmod(0o600)
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(folder/'cert.pem', folder/'key.pem')
    return context


async def main(output):
    output.mkdir(parents=True, exist_ok=True)
    context = certificate(output)
    stopped = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM): loop.add_signal_handler(sig, stopped.set)
    with tempfile.TemporaryDirectory(prefix='ellis-native-deletion-') as temporary:
        root = Path(temporary)
        admission = Admission(root/'usage.sqlite', total_microusd=100, limits={'stt':(100,20,5)})
        store = MemoryStore(root/'memory.sqlite')
        sessions = AccountSessions(admission, store)
        sequence = 0
        def enroll(subject):
            nonlocal sequence
            sequence += 1
            proof = VerifiedIdentity(GOOGLE, subject, admission.clock()+300, 'fictional-client')
            return sessions.exchange(sessions.challenge('google')['challenge'], 'google', proof, 'fictional-proof-'+str(sequence))
        target, other = enroll('fictional-google-subject'), enroll('fictional-other')
        for account in (target, other): store.put_source(account['owner'], source())
        grants = ProviderGrants(admission, Fernet.generate_key())
        google = Mock()
        google.revoke.side_effect = [Rejected('identity_provider_unavailable'), None]
        deletion = AccountDeletion(sessions, grants, Mock(), google)
        service = AccountService(sessions, Mock(), grants=grants, deletion=deletion)
        relay = Relay('unused', admission=admission, accounts=service)
        requests = 0
        blocked_between_phases = False
        async def handle(socket):
            nonlocal requests, blocked_between_phases
            requests += 1
            await relay.handle(socket)
            row = admission.db.execute('SELECT state FROM account_deletion WHERE owner=?', (target['owner'],)).fetchone()
            if row and row[0] == 'pending':
                try: enroll('fictional-google-subject')
                except Rejected as error:
                    assert str(error) == 'account_deletion_pending'
                    blocked_between_phases = True
                else: raise AssertionError('Re-enrollment escaped pending deletion')
        try:
            async with serve(handle, '127.0.0.1', 0, ssl=context, process_request=relay.authorize) as server:
                port = server.sockets[0].getsockname()[1]
                config = dict(endpoint=f'wss://127.0.0.1:{port}/account', provider='google', session=target,
                              googleGrant=dict(subject='fictional-google-subject', token='fictional-google-grant'))
                (output/'account.json').write_text(json.dumps(config))
                print('Ready: isolated TLS native deletion fixture', flush=True)
                await stopped.wait()
            assert blocked_between_phases
            assert admission.db.execute('SELECT state FROM account_deletion WHERE owner=?', (target['owner'],)).fetchone()[0] == 'complete'
            assert store.source(target['owner'], 'session-a') is None
            assert store.source(other['owner'], 'session-a') == source()
            admission.authorized(other['token'])
            assert enroll('fictional-google-subject')['owner'] != target['owner']
            assert requests == 3, requests  # erase, failed finalization, successful finalization
            assert google.revoke.call_count == 2
            assert all(call.args == ('fictional-google-grant',) for call in google.revoke.call_args_list)
            result = dict(status='passed', native_requests=requests, fictional_provider_calls=google.revoke.call_count,
                          reenrollment_blocked_until_revocation=True, other_owner_preserved=True,
                          content_erased=True, fresh_owner_after_completion=True, paid_calls=0)
            (output/'result.json').write_text(json.dumps(result, indent=2)+'\n')
            print(json.dumps(result), flush=True)
        finally: admission.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    asyncio.run(main(parser.parse_args().output))
