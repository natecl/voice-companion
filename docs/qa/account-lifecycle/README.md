# Real Google and Apple account lifecycle

September 30, 2026. Bounded Release simulator acceptance on source
`7f715477a15b92f65a4e0a31dbf3885baf17a20d`, dependent on draft PR164.
No production deployment or app UI changes in this checkpoint.

The founder explicitly confirmed readiness, completed each real provider sign-in,
and exercised the existing profile deletion confirmation for both accounts.
The agent inspected the native screen and backend state after each operation,
terminated/relaunched the app, and inspected the resulting screen again.

| Flow | Observed evidence |
| --- | --- |
| Google enrollment/relaunch | One Google identity and active session; home screen before and after relaunch; no second enrollment |
| Google deletion/relaunch | One successful real Google revocation call; identity removed, session revoked, deletion complete; signed-out screen after relaunch |
| Apple enrollment/relaunch | One successful real Apple code redemption; one Apple identity and active session; home screen after relaunch |
| Apple deletion/relaunch | One successful real Apple revocation call; identity removed and session revoked; signed-out screen after relaunch |

State after the initial deletion sequence: zero enrolled identities, zero active sessions, two completed
deletions. Historical session/deletion ledger rows remain. The provider success
responses establish accepted revocation requests; this run did not separately
probe the deleted grants afterward. The success counters instrument the actual
configured adapters; they do not substitute synthetic provider responses.
Google enrollment verifies its signed identity proof; the instrumentation counter
tracks Google revocation, not all Google network requests.

Sanitized receipts and screenshots are in this directory:
`google-enrollment-relaunch.json`, `google-deletion-relaunch.json`,
`apple-enrollment-relaunch.json`, `apple-deletion-relaunch.json`, and corresponding
`ellis-real-*.png` screenshots. Screenshots contain no account identifiers.

## Environment and reproduction

See [preparation](../account-lifecycle-preparation.md) for exact simulator,
source, binary digest, configuration and private runtime location. The normal
Release plist was restored after the QA-only localhost endpoint/deletion flag
build. Existing founder phone and hosted data were not changed. The harness
uses actual account service/storage/provider adapters, with all generation
reservations rejected and no model provider configured. Paid spend: $0.

Start `scripts/qa/real-account-server.py --output <new-private-directory>
--apple-key <protected-key-file>` with the backend requirements installed.
It reads the configured public Google client IDs from the app plists and uses
the existing Apple client/team/key identifiers. Trust its one-day localhost
certificate only on a dedicated simulator. Build/install Release with its
localhost account endpoint and deletion flag, restore source configuration,
and obtain readiness before real account interaction. Complete each provider's
sign-in, inspect durable state and home screen, relaunch, use profile deletion,
inspect revocation/deletion state and signed-out relaunch. Never publish tokens,
keys or the private output directory. Preserve existing QA databases on restart;
the harness intentionally refuses to overwrite them.

## Limits and remaining work

These were empty isolated accounts. This run does not prove populated erasure,
two-owner data/cache isolation, real expired-session refresh or fresh-proof
recovery, multi-window races, hosted rollout,
founder-data migration, backup retention or physical-device acceptance. Prior
synthetic tests remain supporting contract evidence, not substitutes for those
remaining checks. Distribution, privacy/support, plans and billing gates remain
open. Keep the dependent implementation drafts unmerged until their applicable
acceptance and review gates are satisfied.

## Google re-enrollment after deletion

The founder was instructed to reuse the same Google account and completed the
provider flow. One Google identity and one active session now exist, with a new
owner distinct from both deleted owners; the home screen was inspected. See
`google-reenrollment.json` and `ellis-real-google-reenrolled.png`. Original provider
subjects were erased, so same-account selection is founder-reported rather than
an independent comparison against a retained old subject. Real refresh and populated isolation remain open.

## Sign-out and Apple re-enrollment

The founder signed out of the new Google account, then was instructed to reuse
the same Apple account and completed its real provider flow. Google has zero
active sessions; Apple has one and its new owner differs from both deleted
owners. The Apple home screen was inspected. See `apple-reenrollment.json` and
`ellis-real-apple-reenrolled.png`. Both new identities remain enrolled in the
isolated database; only Apple is signed in. Same-provider-account selection has
the same evidence limit described above. This empty-account switch is not
populated cross-owner isolation acceptance. No further founder action is needed
for this completed sequence; prepare the remaining refresh/isolation checks
before requesting another manual session.

## Real backend session refresh and replay

`real-backend-refresh.json` records one refresh per provider over the running
localhost TLS account endpoint. `scripts/qa/real-session-refresh.py` creates
separate synthetic app-session families bound to the existing real QA owners,
expires only those access credentials, and sends actual refresh requests. Both
rotations preserve ownership and issue usable new access and refresh tokens.
Replaying each old refresh token returns `refresh_replayed`; the new token then
returns `unauthorized`, proving family revocation. Existing native sessions'
revocation flags are compared before/after and are unchanged. Test families are
revoked in cleanup even on failure.

The server observed exactly one successful `apple.validate_refresh` call using
the real stored Apple grant. Google app-session refresh uses the authenticated
local refresh secret and makes no Google provider request. No retries or paid
model calls occurred. The currently signed-in Apple native session remains the
only active session. This closes the backend real-grant refresh check; native
automatic expiry/Keychain rotation and revoked-provider recovery remain open.

Reproduce only against the isolated running QA server with both identities:

```sh
/tmp/ellis-auth-venv/bin/python scripts/qa/real-session-refresh.py \
  --directory <private-real-account-QA-directory> \
  --output <sanitized-receipt-path>
```

The script refuses non-local endpoints and uses the local certificate. It never
prints session secrets or reads native Keychain; assertions inspect the real
responses without logging their token payloads.
