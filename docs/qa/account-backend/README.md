# Backend account protocol and QA

September 29, 2026. Based on merged ownership checkpoint `74a8a9e` (PR157). Candidate backend only; no deployment or native sign-in acceptance. UI files are unchanged.

## Contract

`/account` is a native WebSocket endpoint, one JSON request per connection. Every request has integer `version: 1` and `operation`. Exact allowed payload fields:

- `challenge`: `provider` (`google` or `apple`). Returns challenge, nonce and five-minute expiry. Pass the returned nonce verbatim to Apple's authorization request.
- `exchange`: `provider`, `challenge`, `identity_token`. Verifies RS256 signature against fixed provider JWKS URLs, configured issuer/audience, expiry/issued-at, bounded subject, Google authorized presenter when supplied, and Apple server nonce. Returns owner, one-hour access token, refresh token and expiries. Each challenge and ID token can be exchanged once.
- `refresh`: `refresh_token`. Rotates once and revokes old access; preserves owner and the original 30-day refresh-family deadline. Replaying an old refresh token revokes that whole login family, including its latest access token. Native code must serialize refresh and reauthenticate after an uncertain/lost response rather than retry rotation automatically.
- `sign_out`: `refresh_token`. Idempotently revokes that login family, including when given a consumed refresh token. Other login families remain valid.

Tokens are sent only in the TLS-protected WebSocket body, never URLs or logs. SQLite stores token digests, not raw access/refresh/provider tokens. Provider signature lookup has a five-second network timeout and cached keys. Two concurrent account operations, a 12-second request deadline, 20KB message bounds, a 60-connection/minute process-wide limit and at most 1,000 live challenges bound this initial pilot endpoint. Browser Origin requests are rejected. These limits are not a claim of production-scale abuse protection.

Enable only with explicit `VOICE_ENABLE_ACCOUNTS=1`, memory storage and all public client configuration:

- `VOICE_GOOGLE_SERVER_CLIENT_ID`
- `VOICE_GOOGLE_NATIVE_CLIENT_IDS` (comma-separated)
- `VOICE_APPLE_CLIENT_IDS` (comma-separated)

Default is disabled/HTTP 404. Incomplete enabled configuration fails startup. No environment setting was changed in the live service.

## Verification

Python 3.13 in an isolated virtualenv, installed `Backend/requirements.txt` including PyJWT 2.15.1. Run:

```sh
python -m unittest discover -s Backend -p 'test_account_*.py' -v
cd Backend
python -m unittest test_relay test_admission test_hosted_startup test_memory
```

22 account tests and 31 impacted regression tests pass. The account socket suite uses actual RSA signatures with fictional Google/Apple claims and injected test public keys. It starts the real Relay/AccountService on localhost and observes successful exchange for both providers, distinct owners, refresh continuity, challenge replay failure, refresh replay family revocation, sign-out denial, strict input rejection, Origin rejection and rate limiting. It also verifies disabled-endpoint HTTP 404. No live provider or paid model calls occur; admission usage remains empty.

Other tests cover invalid signature/issuer/audience/subject/time/algorithm, missing Apple nonce, unavailable key provider, stored-token secrecy, original refresh-family expiry, idempotent sign-out, stable owner mapping and memory-write failure rolling back credential issuance. Existing admission regression emits an unclosed SQLite ResourceWarning. Relay regression cost estimates describe synthetic local upstream traffic, not paid calls.

## Remaining release gates

Live provider tokens, JWKS rotation/network integration, native UI wiring, secure Keychain lifecycle and refresh serialization, owner-switch cancellation/cache isolation, Apple authorization-code redemption and provider refresh/revocation, external revocation handling, account deletion, founder migration and physical Release tests remain incomplete. ID-token verification alone does not implement the whole Apple account lifecycle. Check current official provider requirements during that integration.

Admission and memory use separate databases. A failed/crashed exchange may leave an unreachable memory credential mapping, but no committed access token; identity mapping remains stable. Do not reset stores to recover. Preserve backup/rollback plans and all spending history before deployment.

Sources checked: [Google backend authentication](https://developers.google.com/identity/sign-in/ios/backend-auth), [Apple user verification](https://developer.apple.com/documentation/signinwithapple/verifying-a-user), [PyJWT API](https://pyjwt.readthedocs.io/en/stable/api.html).
