"""Real RSA signatures with synthetic claims; never calls a live identity provider."""
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
from admission import Rejected
from account_tokens import AccountTokenVerifier, GOOGLE, APPLE


class AccountTokenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.other = rsa.generate_private_key(public_exponent=65537, key_size=2048)

    def setUp(self):
        self.verifier = AccountTokenVerifier(google_audience='backend', google_presenters=['phone', 'mac'],
                                              apple_audiences=['ai.voicecompanion.phone', 'ai.voicecompanion.mac'])
        self.verifier.keys = {p: Mock() for p in ('google', 'apple')}
        for client in self.verifier.keys.values():
            client.get_signing_key_from_jwt.return_value = SimpleNamespace(key=self.key.public_key())
        now = int(time.time())
        self.claims = dict(iss=GOOGLE, sub='synthetic-user', aud='backend', iat=now, exp=now+300, azp='phone')

    def token(self, claims=None, key=None):
        return jwt.encode(self.claims if claims is None else claims, key or self.key,
                          algorithm='RS256', headers={'kid': 'fixture'})

    def test_google_canonical_identity_and_no_email_dependency(self):
        for issuer in (GOOGLE, 'accounts.google.com'):
            identity = self.verifier.verify('google', self.token(self.claims | {'iss': issuer, 'email': 'ignored@example.test'}))
            self.assertEqual((identity.issuer, identity.subject), (GOOGLE, 'synthetic-user'))
            self.assertFalse(hasattr(identity, 'email'))

    def test_claim_and_signature_rejections(self):
        changes = [{'iss': 'https://evil.test'}, {'aud': 'other-app'}, {'aud': ['backend', 'other-app']},
                   {'sub': ''}, {'sub': 4}, {'exp': 0}, {'iat': int(time.time())+500},
                   {'exp': str(int(time.time())+300)}, {'azp': 'unrelated-client'}]
        for change in changes:
            with self.subTest(change=change), self.assertRaisesRegex(Rejected, '^invalid_identity_token$'):
                self.verifier.verify('google', self.token(self.claims | change))
        with self.assertRaisesRegex(Rejected, '^invalid_identity_token$'):
            self.verifier.verify('google', self.token(key=self.other))
        for field in ('iss', 'aud', 'sub', 'iat', 'exp'):
            claims = self.claims.copy(); del claims[field]
            with self.subTest(missing=field), self.assertRaises(Rejected):
                self.verifier.verify('google', self.token(claims))

    def test_apple_requires_matching_server_nonce_and_native_audience(self):
        nonce = 'a' * 64
        for audience in ('ai.voicecompanion.phone', 'ai.voicecompanion.mac'):
            claims = self.claims | dict(iss=APPLE, aud=audience, nonce=nonce)
            identity = self.verifier.verify('apple', self.token(claims), apple_nonce=nonce)
            self.assertEqual(identity.issuer, APPLE)
            for expected in (None, 'b'*64):
                with self.assertRaisesRegex(Rejected, '^invalid_identity_token$'):
                    self.verifier.verify('apple', self.token(claims), apple_nonce=expected)
            del claims['nonce']
            with self.assertRaises(Rejected):
                self.verifier.verify('apple', self.token(claims), apple_nonce=nonce)

    def test_malformed_and_algorithm_confusion_fail_before_key_fetch(self):
        for token in ('', 'bad', 'x'*16385, jwt.encode(self.claims, 'synthetic-secret'*4, algorithm='HS256', headers={'kid':'fixture'})):
            with self.assertRaises(Rejected):
                self.verifier.verify('google', token)
        self.verifier.keys['google'].get_signing_key_from_jwt.assert_not_called()

    def test_provider_failure_is_safe_and_recoverable(self):
        client = self.verifier.keys['google']
        client.get_signing_key_from_jwt.side_effect = jwt.PyJWKClientConnectionError('private diagnostics')
        with self.assertRaisesRegex(Rejected, '^identity_provider_unavailable$'):
            self.verifier.verify('google', self.token())
        client.get_signing_key_from_jwt.side_effect = None
        self.assertEqual(self.verifier.verify('google', self.token()).subject, 'synthetic-user')

    def test_missing_configuration_fails_closed(self):
        with self.assertRaises(ValueError):
            AccountTokenVerifier(google_audience='', google_presenters=['phone'], apple_audiences=['phone'])


class JWKSIntegrationTests(unittest.TestCase):
    def test_real_jwks_fetch_cache_rotation_and_unknown_key(self):
        import json
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        first = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        second = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        state = {'keys': [], 'requests': 0}
        def jwk(key, kid):
            value = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
            return dict(value, kid=kid, alg='RS256', use='sig')
        state['keys'] = [jwk(first, 'first')]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                state['requests'] += 1
                body = json.dumps({'keys': state['keys']}).encode()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            def log_message(self, *_): pass
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            verifier = AccountTokenVerifier(google_audience='backend', google_presenters=['phone'], apple_audiences=['phone'])
            verifier.keys['google'] = jwt.PyJWKClient(f'http://127.0.0.1:{server.server_port}/keys', timeout=1)
            now = int(time.time())
            claims = dict(iss=GOOGLE, aud='backend', sub='synthetic', iat=now, exp=now+300)
            token = jwt.encode(claims, first, algorithm='RS256', headers={'kid':'first'})
            for _ in range(2): self.assertEqual(verifier.verify('google', token).subject, 'synthetic')
            self.assertEqual(state['requests'], 1)
            state['keys'] = [jwk(second, 'second')]
            rotated = jwt.encode(claims, second, algorithm='RS256', headers={'kid':'second'})
            with self.assertRaisesRegex(Rejected, '^invalid_identity_token$'):
                verifier.verify('google', rotated)
            self.assertEqual(state['requests'], 1)
            # Preserve the library's anti-abuse cooldown; advance fixture time.
            after_cooldown = time.monotonic() + 31
            with patch('jwt.jwks_client.time.monotonic', return_value=after_cooldown):
                self.assertEqual(verifier.verify('google', rotated).subject, 'synthetic')
            self.assertEqual(state['requests'], 2)
            with self.assertRaisesRegex(Rejected, '^invalid_identity_token$'):
                verifier.verify('google', token)
        finally:
            server.shutdown(); server.server_close(); thread.join()


if __name__ == '__main__': unittest.main()
