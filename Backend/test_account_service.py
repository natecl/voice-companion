import json
from pathlib import Path
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from websockets.asyncio.client import connect
from websockets.asyncio.server import serve
from websockets.exceptions import InvalidStatus

from account_tokens import AccountTokenVerifier, GOOGLE, APPLE
from account_sessions import AccountSessions
from account_service import AccountService
from provider_grants import ProviderGrants
from cryptography.fernet import Fernet
from admission import Admission, Rejected
from memory_store import MemoryStore
from relay import Relay


class AccountSocketTests(unittest.IsolatedAsyncioTestCase):
    async def test_signed_exchange_refresh_replay_and_signout_over_real_sockets(self):
        with tempfile.TemporaryDirectory() as d:
            admission = Admission(Path(d)/'usage.sqlite', total_microusd=100, limits={'stt':(100,20,3)})
            self.addCleanup(admission.close)
            memory = MemoryStore(Path(d)/'memory.sqlite')
            verifier = AccountTokenVerifier(google_audience='backend', google_presenters=['phone'], apple_audiences=['phone'])
            key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
            for provider in verifier.keys:
                verifier.keys[provider] = Mock()
                verifier.keys[provider].get_signing_key_from_jwt.return_value = SimpleNamespace(key=key.public_key())
            apple = Mock()
            grants = ProviderGrants(admission, Fernet.generate_key())
            accounts = AccountService(AccountSessions(admission, memory), verifier, apple_oauth=apple, grants=grants)
            relay = Relay('unused', admission=admission, accounts=accounts)
            async with serve(relay.handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
                url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/account'
                async def request(**data):
                    async with connect(url) as socket:
                        await socket.send(json.dumps(dict(version=1, **data)))
                        return json.loads(await socket.recv())
                sessions = []
                for provider in ('google', 'apple'):
                    challenge = await request(operation='challenge', provider=provider)
                    now = int(time.time())
                    claims = dict(iss=GOOGLE if provider=='google' else APPLE, sub='synthetic-user',
                                  aud='backend' if provider=='google' else 'phone', iat=now, exp=now+300,
                                  nonce=challenge['nonce'])
                    token = jwt.encode(claims, key, algorithm='RS256', headers={'kid':'fixture'})
                    extra = {}
                    if provider == 'apple':
                        extra['authorization_code'] = 'synthetic-code'
                        missing = await request(operation='exchange', provider=provider,
                                                challenge=challenge['challenge'], identity_token=token)
                        self.assertEqual(missing['message'], 'invalid_account_request')
                        apple.redeem.assert_not_called()
                        for changed in ({'sub': 'different-user'}, {'nonce': 'different-nonce'}):
                            wrong = jwt.encode(dict(claims, **changed), key, algorithm='RS256', headers={'kid':'fixture'})
                            apple.redeem.return_value = dict(identity_token=wrong, refresh_token='wrong-refresh')
                            rejected = await request(operation='exchange', provider=provider,
                                                     challenge=challenge['challenge'], identity_token=token, **extra)
                            self.assertEqual(rejected['message'], 'invalid_identity_token')
                        apple.redeem.return_value = dict(identity_token=token, refresh_token='synthetic-apple-refresh')
                    session = await request(operation='exchange', provider=provider,
                                            challenge=challenge['challenge'], identity_token=token, **extra)
                    self.assertEqual(session['type'], 'account_result')
                    admission.authorized(session['token'])
                    sessions.append(session)
                    replay = await request(operation='exchange', provider=provider,
                                           challenge=challenge['challenge'], identity_token=token)
                    self.assertEqual(replay['message'], 'invalid_account_challenge')
                self.assertNotEqual(sessions[0]['owner'], sessions[1]['owner'])
                fresh = await request(operation='refresh', refresh_token=sessions[0]['refresh_token'])
                self.assertEqual(fresh['owner'], sessions[0]['owner'])
                replay = await request(operation='refresh', refresh_token=sessions[0]['refresh_token'])
                self.assertEqual(replay['message'], 'refresh_replayed')
                self.assertEqual((await request(operation='refresh', refresh_token=fresh['refresh_token']))['message'], 'unauthorized')
                apple.validate_refresh.side_effect = Rejected('provider_authorization_revoked')
                revoked = await request(operation='refresh', refresh_token=sessions[1]['refresh_token'])
                self.assertEqual(revoked['message'], 'provider_authorization_revoked')
                with self.assertRaises(Rejected):
                    admission.authorized(sessions[1]['token'])
                self.assertEqual(len(grants.apple_for(sessions[1]['owner'])), 1)
                self.assertNotIn(b'synthetic-apple-refresh', (Path(d)/'usage.sqlite').read_bytes())
                await request(operation='sign_out', refresh_token=sessions[1]['refresh_token'])
                self.assertEqual((await request(operation='refresh', refresh_token=sessions[1]['refresh_token']))['message'], 'unauthorized')
                self.assertEqual((await request(operation='challenge', provider='google', owner='attacker'))['message'], 'invalid_account_request')
                with self.assertRaises(InvalidStatus):
                    async with connect(url, origin='https://untrusted.example'): pass
                accounts.attempts = 60
                with self.assertRaises(InvalidStatus):
                    async with connect(url): pass
            self.assertEqual(admission.usage(), [])

    async def test_disabled_endpoint_stays_closed(self):
        relay = Relay('unused', token='unused')
        async with serve(relay.handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
            url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/account'
            with self.assertRaises(InvalidStatus) as error:
                async with connect(url): pass
            self.assertEqual(error.exception.response.status_code, 404)


class AccountConfigurationTests(unittest.TestCase):
    def test_default_disabled_and_incomplete_configuration_fails_closed(self):
        from account_service import configured_accounts
        self.assertIsNone(configured_accounts({}, None, None))
        with self.assertRaises(ValueError):
            configured_accounts({'VOICE_ENABLE_ACCOUNTS': 'yes'}, None, None)
        with self.assertRaises(ValueError):
            configured_accounts({'VOICE_ENABLE_ACCOUNTS': '1'}, None, None)
        with self.assertRaises(ValueError):
            configured_accounts({'VOICE_ENABLE_ACCOUNTS': '1'}, None, object())


if __name__ == '__main__': unittest.main()
