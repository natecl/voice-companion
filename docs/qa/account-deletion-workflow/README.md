# Account deletion workflow candidate — September 30

Depends on PR160 `ec59b1e`, which depends on draft PR159. Branch `codex/account-deletion-workflow`. This adds a local backend deletion path; it is **not enabled, deployed or wired into the app**, and does not complete account erasure or TestFlight acceptance.

## Contract

With `VOICE_ENABLE_ACCOUNT_DELETION=1`, the account socket accepts exactly `version: 1`, `operation: delete_account`, `refresh_token`, and `confirmation: delete_account`. No supplied owner is accepted. Default is off. The existing account refresh secret authenticates the request. The app must obtain explicit user confirmation and persist the pending deletion receipt before sending; those native changes are still pending.

Before any external call, the service stores a durable pending record, blocks the provider identity from enrollment, and revokes every app session belonging to that owner. Relay closes/cancels only that owner's active content sockets/tasks and waits for their cleanup. It then revokes each stored Apple grant, removes each successfully revoked encrypted grant, invokes the atomic storage eraser, and commits completion. No request or reservation rows are removed or refunded.

Account mutation operations are serialized within the hosted process, which already requires an exclusive process lock. Idle sockets do not hold that mutation lock. Provider identity is checked before Apple code redemption and again before session issuance, so pending deletion cannot obtain a replacement app session/grant through enrollment. Pending-identity hashes survive restart and the independent content-store commit; completion removes these hashes. Content-free owner/request-digest completion records remain for idempotency.

A timeout, lost reply or provider failure never reports success. The same original refresh secret can explicitly retry an already-accepted deletion after app-session expiry, with no restored content access. Successful grants are not revoked again on retry; a lost provider response may require repeating its revocation. Apple documents HTTP 200 for tokens that were already invalidated at its [revocation endpoint](https://developer.apple.com/documentation/signinwithapplerestapi/revoke-tokens); the adapter now requires that status rather than accepting any successful HTTP response. No automatic retries occur. Actual Apple behavior remains unverified here.

## Evidence

Fictional local content/identities, temporary SQLite databases, actual localhost WebSockets, and fixture Apple responses. No private credentials, production database mutations, device changes or paid calls.

```sh
PYTHONPATH=Backend /tmp/ellis-auth-venv/bin/python -m unittest discover -s Backend -p 'test_account*.py'
PYTHONPATH=Backend /tmp/ellis-auth-venv/bin/python -m unittest test_apple_oauth test_provider_grants test_relay test_hosted_relay test_hosted_startup test_companion_service test_proactive_service test_notes_service
/tmp/ellis-auth-venv/bin/python scripts/qa/account-deletion.py --output docs/qa/account-deletion-workflow/replay.json
```

44 account tests pass, including ten new deletion tests: all-device revocation, unaffected second account, preserved charges, provider failure/restart, partial grant completion, failed quiescence, interrupted cross-database completion, invalid/unwired requests, actual socket isolation/cancellation, pending Apple enrollment rejection before redemption, explicit default-off configuration and idle-socket behavior. Some cases combine multiple assertions in one test.

41 impacted adapter/relay/chat/proactive/notes/startup checks pass, including the new exact HTTP-status check. These suites use local fixtures; their synthetic transcription-cost log fields do not represent actual spending. The existing storage erasure suite continues to cover late thread results and schema-21 content removal.

The [endpoint replay receipt](replay.json) includes source hashes. An actual deletion socket request revoked both app sessions, invoked fixture Apple revocation once, erased content, and returned the same completion on retry. Old content sockets were then rejected with HTTP 401. The second owner's transcript, notes and chat reopened unchanged; synthetic reservation rows were unchanged; a fresh enrollment received a new empty owner. Live provider verification is not inferred from this replay.

Review caught mutation locking before frame receipt; it was moved after parsing and a real idle-socket regression check now passes. All checks apply to the resulting code.

## Required before enablement

- Native explicit confirmation, durable pending receipt, owner-safe local recording/cache/outbox cleanup, and generation guards so retrying an old deletion cannot clear a newly signed-in account.
- Recovery after uninstall/loss of the original deletion secret. Current pending identities remain blocked; a newly verified provider-proof recovery flow is required before release. Do not tell users to bypass this by signing into another provider.
- Actual Apple grant revocation and physical-device failure/relaunch checks.
- Backup expiration/redaction and restore-time deletion replay; operational replicas and provider retention must not be mislabeled as erased.
- Review the entire dependency chain, pending-worker behavior and live data volume before a paired rollout. Keep a schema-21-compatible rollback. The older live schema-20 binary cannot be used against an upgraded content database.

No UI, plans/prices, founder migration, backup deletion or live account deletion is delivered by this checkpoint.
