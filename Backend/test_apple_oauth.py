import io
import json
import unittest
from urllib.error import HTTPError
from urllib.parse import parse_qs
from unittest.mock import Mock

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from admission import Rejected
from apple_oauth import AppleOAuth, NoRedirect


class AppleOAuthTests(unittest.TestCase):
    def setUp(self):
        self.key = ec.generate_private_key(ec.SECP256R1())
        pem = self.key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                     serialization.NoEncryption()).decode()
        self.client = AppleOAuth(team_id='TEAM123456', key_id='KEY1234567', private_key=pem, client_ids=['app.phone'])
        self.client.opener = Mock()

    def respond(self, value):
        self.client.opener.open.return_value = io.BytesIO(json.dumps(value).encode())
        self.client.opener.open.return_value.status = 200

    def test_redemption_request_and_real_client_secret_signature(self):
        self.respond(dict(id_token='synthetic-id-token', refresh_token='synthetic-refresh'))
        result = self.client.redeem('app.phone', 'synthetic-code')
        self.assertEqual(result['refresh_token'], 'synthetic-refresh')
        request = self.client.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://appleid.apple.com/auth/token')
        self.assertEqual(request.method, 'POST')
        body = parse_qs(request.data.decode())
        self.assertEqual(body['grant_type'], ['authorization_code'])
        claims = jwt.decode(body['client_secret'][0], self.key.public_key(), algorithms=['ES256'],
                            audience='https://appleid.apple.com', issuer='TEAM123456')
        self.assertEqual(claims['sub'], 'app.phone')
        self.assertEqual(claims['exp']-claims['iat'], 300)
        self.assertEqual(jwt.get_unverified_header(body['client_secret'][0])['kid'], 'KEY1234567')

    def test_refresh_and_revocation_use_refresh_token_in_body_only(self):
        self.respond(dict(access_token='synthetic-access', token_type='Bearer'))
        self.client.validate_refresh('app.phone', 'synthetic-refresh')
        self.respond({})
        self.client.revoke('app.phone', 'synthetic-refresh')
        request = self.client.opener.open.call_args.args[0]
        self.assertEqual(request.full_url, 'https://appleid.apple.com/auth/revoke')
        self.assertEqual(parse_qs(request.data.decode())['token_type_hint'], ['refresh_token'])

    def test_revocation_requires_apple_success_status(self):
        self.respond({})
        self.client.opener.open.return_value.status = 202
        with self.assertRaisesRegex(Rejected, 'identity_provider_unavailable'):
            self.client.revoke('app.phone', 'synthetic-refresh')
        self.client.opener.open.assert_called_once()

    def test_invalid_grant_is_safe_and_never_retried(self):
        self.client.opener.open.side_effect = HTTPError('https://appleid.apple.com/auth/token', 400,
            'private provider detail', {}, io.BytesIO(b'{"error":"invalid_grant"}'))
        with self.assertRaisesRegex(Rejected, '^provider_authorization_revoked$'):
            self.client.validate_refresh('app.phone', 'synthetic-refresh')
        self.assertEqual(self.client.opener.open.call_count, 1)

    def test_bad_client_missing_tokens_and_redirects_fail_closed(self):
        with self.assertRaises(Rejected): self.client.redeem('attacker', 'code')
        self.client.opener.open.assert_not_called()
        self.respond({})
        with self.assertRaises(Rejected): self.client.redeem('app.phone', 'code')
        with self.assertRaises(Rejected):
            NoRedirect().redirect_request(None, None, 302, '', {}, 'https://attacker.test')


if __name__ == '__main__': unittest.main()
