"""Apple code redemption, refresh validation and revocation; no automatic retries."""
import json
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, HTTPRedirectHandler, build_opener

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from admission import Rejected


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Rejected('identity_provider_unavailable')


class AppleOAuth:
    def __init__(self, *, team_id, key_id, private_key, client_ids, clock=time.time):
        if any(not isinstance(v, str) or not re.fullmatch(r'[A-Z0-9]{10}', v) for v in (team_id, key_id)):
            raise ValueError('Apple team/key IDs are required')
        if not client_ids or any(not isinstance(v, str) or not v for v in client_ids):
            raise ValueError('Apple client IDs are required')
        key = serialization.load_pem_private_key(private_key.encode(), password=None)
        if not isinstance(key, ec.EllipticCurvePrivateKey) or not isinstance(key.curve, ec.SECP256R1):
            raise ValueError('Apple requires a P-256 signing key')
        self.team_id, self.key_id, self.key = team_id, key_id, key
        self.client_ids = tuple(client_ids)
        self.clock = clock
        self.opener = build_opener(NoRedirect())

    def _secret(self, client_id):
        if client_id not in self.client_ids:
            raise Rejected('invalid_identity_token')
        now = int(self.clock())
        return jwt.encode(dict(iss=self.team_id, sub=client_id, aud='https://appleid.apple.com',
                               iat=now, exp=now+300), self.key, algorithm='ES256', headers={'kid': self.key_id})

    def _post(self, endpoint, client_id, fields):
        fields = dict(fields, client_id=client_id, client_secret=self._secret(client_id))
        request = Request('https://appleid.apple.com/auth/' + endpoint,
                          data=urlencode(fields).encode(), method='POST',
                          headers={'Content-Type': 'application/x-www-form-urlencoded', 'Accept': 'application/json'})
        try:
            with self.opener.open(request, timeout=5) as response:
                raw = response.read(32769)
                if len(raw) > 32768:
                    raise Rejected('identity_provider_unavailable')
                if endpoint == 'revoke':
                    return None
                result = json.loads(raw)
                if not isinstance(result, dict) or 'error' in result:
                    raise Rejected('identity_provider_unavailable')
                return result
        except HTTPError as error:
            try:
                body = json.loads(error.read(32768))
                revoked = error.code == 400 and isinstance(body, dict) and body.get('error') == 'invalid_grant'
            except (ValueError, OSError):
                revoked = False
            finally:
                error.close()
            raise Rejected('provider_authorization_revoked' if revoked else 'identity_provider_unavailable') from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise Rejected('identity_provider_unavailable') from None

    @staticmethod
    def _token(value):
        if not isinstance(value, str) or not 1 <= len(value) <= 8192:
            raise Rejected('invalid_identity_token')
        return value

    def redeem(self, client_id, code):
        result = self._post('token', client_id, dict(grant_type='authorization_code', code=self._token(code)))
        # Caller must cryptographically verify this returned ID token and compare
        # its subject/audience/nonce with the independently verified native token.
        return dict(identity_token=self._token(result.get('id_token')),
                    refresh_token=self._token(result.get('refresh_token')))

    def validate_refresh(self, client_id, refresh_token):
        result = self._post('token', client_id, dict(grant_type='refresh_token', refresh_token=self._token(refresh_token)))
        if not isinstance(result.get('token_type'), str) or result['token_type'].lower() != 'bearer':
            raise Rejected('identity_provider_unavailable')
        self._token(result.get('access_token'))
        return result

    def revoke(self, client_id, refresh_token):
        self._post('revoke', client_id, dict(token_type_hint='refresh_token', token=self._token(refresh_token)))
