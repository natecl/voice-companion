"""Provider ID-token validation. Call off the event loop: JWKS lookup can block.

This module verifies identity, not authorization-code redemption, replay protection
or session issuance. Those checks belong to the enrollment transaction.
"""
from dataclasses import dataclass
import hmac

import jwt
from admission import Rejected

GOOGLE = 'https://accounts.google.com'
APPLE = 'https://appleid.apple.com'


@dataclass(frozen=True)
class VerifiedIdentity:
    issuer: str
    subject: str
    expires: int
    audience: str = ""


class AccountTokenVerifier:
    def __init__(self, *, google_audience, google_presenters, apple_audiences):
        if not isinstance(google_audience, str) or not google_audience.strip():
            raise ValueError('Google server audience is required')
        for values in (google_presenters, apple_audiences):
            if not isinstance(values, (tuple, list)) or not values or any(
                    not isinstance(v, str) or not v.strip() for v in values):
                raise ValueError('Explicit native client audiences are required')
        self.google_audience = google_audience
        self.google_presenters = tuple(google_presenters)
        self.apple_audiences = tuple(apple_audiences)
        # URLs are fixed configuration; never take a key URL from a token header.
        self.keys = {
            'google': jwt.PyJWKClient('https://www.googleapis.com/oauth2/v3/certs',
                                      timeout=5, lifespan=300),
            'apple': jwt.PyJWKClient('https://appleid.apple.com/auth/keys',
                                     timeout=5, lifespan=300),
        }

    def verify(self, provider, token, *, expected_nonce=None):
        if not isinstance(provider, str) or provider not in self.keys or not isinstance(token, str) or not 1 <= len(token) <= 16384:
            raise Rejected('invalid_identity_token')
        if provider == 'apple' and (not isinstance(expected_nonce, str) or
                                    not 32 <= len(expected_nonce) <= 256):
            raise Rejected('invalid_identity_token')
        try:
            header = jwt.get_unverified_header(token)
            if header.get('alg') != 'RS256' or not isinstance(header.get('kid'), str) or not 1 <= len(header['kid']) <= 256:
                raise Rejected('invalid_identity_token')
            key = self.keys[provider].get_signing_key_from_jwt(token)
            issuers = (GOOGLE, 'accounts.google.com') if provider == 'google' else (APPLE,)
            audiences = (self.google_audience,) if provider == 'google' else self.apple_audiences
            claims = jwt.decode(token, key.key, algorithms=['RS256'], issuer=issuers,
                                audience=audiences, options={'require': ['iss', 'aud', 'sub', 'iat', 'exp']})
            # ID tokens for these native flows must target one configured audience.
            if not isinstance(claims['aud'], str) or claims['aud'] not in audiences:
                raise Rejected('invalid_identity_token')
            if any(type(claims[k]) is not int for k in ('iat', 'exp')) or claims['exp'] <= claims['iat']:
                raise Rejected('invalid_identity_token')
            subject = claims['sub']
            if not isinstance(subject, str) or not 1 <= len(subject) <= 255 or any(
                    ord(c) < 33 or ord(c) > 126 for c in subject):
                raise Rejected('invalid_identity_token')
            if provider == 'google':
                if expected_nonce is not None:
                    nonce = claims.get('nonce')
                    if not isinstance(nonce, str) or not hmac.compare_digest(nonce.encode(), expected_nonce.encode()):
                        raise Rejected('invalid_identity_token')
                # If Google supplies an authorized presenter, it must be ours.
                if 'azp' in claims and claims['azp'] not in (*self.google_presenters, self.google_audience):
                    raise Rejected('invalid_identity_token')
            else:
                nonce = claims.get('nonce')
                if not isinstance(nonce, str) or not hmac.compare_digest(nonce.encode(), expected_nonce.encode()):
                    raise Rejected('invalid_identity_token')
            return VerifiedIdentity(GOOGLE if provider == 'google' else APPLE, subject, claims['exp'], claims['aud'])
        except jwt.PyJWKClientConnectionError:
            raise Rejected('identity_provider_unavailable') from None
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            # Never expose JWTs, subjects, key material or vendor diagnostics.
            raise Rejected('invalid_identity_token') from None
