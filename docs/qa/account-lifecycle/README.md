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

## Populated backend isolation and native preparation

`populated-backend-isolation.json` records actual TLS requests bound to the two
real enrolled QA owners, using separate synthetic request credentials revoked
after the check. Each owner has a unique fictional transcript, generated-note
fixture and completed-chat fixture. These are explicit seeded records, not
recorded speech or real model outputs. Both owners read their own note and chat;
foreign note IDs return `source_unavailable`; an attempted source deletion with
the other owner ID returns `memory_owner_mismatch`. Each foreign source remains
present. No generation worker or paid call runs.

Matching fictional local session files were seeded only in the dedicated
simulator's owner-scoped storage. The unchanged Release app was relaunched while
signed into Apple: `ellis-populated-apple-home.png` shows Apple's fictional
lantern answer and no Google compass answer. This is one-sided native history
evidence, not completed native switching or notes-cache acceptance. Both
providers' fictional content remains for the next explicitly ready manual QA:
open Apple's note, switch to Google, inspect its chat/library/note, then switch
back and verify Apple's content and owner cache clearing.

Reproduction helper: `scripts/qa/populated-account-isolation.py --directory
<private-QA-directory> --simulator <dedicated-simulator-id> --output
<sanitized-receipt-path>`. Requires the running real-account localhost server
and both real enrolled identities. It refuses an existing fixture manifest; do
not delete that guard to repeat a run. Private `isolation-fixtures.json` holds
owner/session mappings for inspecting the existing run and must not be committed.
The executed preparation was subsequently parameterized for these three paths
and formatted; the fixture actions and assertions are unchanged. Python
compilation and diff checks pass.

## Fixture correction during native Notes inspection

The first manual Apple note open correctly showed an unsynced source and no
cached summary (`fixture-timestamp-mismatch.png`). The fixture used the current
time locally but timestamp 100 on the server. Aligning the timestamps alone
was insufficient: Python fixture floats (`100.0`, `0.0`, `2.0`) and Swift integer
JSON representations produced different canonical payload hashes at the same
revision. This was cross-language fixture construction, not observed production
source corruption. The preparation helper now uses identical timestamp and
number representations for both sides.

For the existing run, both fictional server sources/notes were advanced to
revision 2 with matching native payloads. Local outboxes were staged with
`acknowledged=false`; no acknowledgment was fabricated. After relaunch, Apple's
actual native transport received a successful sync response and persisted
`acknowledged=true` for revision 2. Google remains to sync on its next login.
The earlier backend-isolation receipt describes revision 1 before this fixture
repair. Native Notes rendering/cache and switching still require inspection.
No production app code or UI was changed; no paid calls occurred.

## Native populated switching and cache clearing

After explicit readiness and the documented fixture repair, the founder opened
Apple's note, signed out, signed into Google, opened Google's note, then signed
out, returned to Apple and reopened its note. The agent inspected screenshots
and owner-scoped cache/session state at each step. This used the unchanged
Release simulator binary described above with real provider sign-ins and
explicit fictional content.

- Apple revision-2 lantern summary rendered and its ready cache entry matched
  Apple's owner/session (`apple-note-cache-before-switch.json`).
- After Apple sign-out, Apple had no active sessions and no cached JSON files.
  Google's original owner had one active session and its chat showed only the
  compass fixture (`google-switch-state.json`, Google home screenshot).
- Google revision-2 compass summary rendered and its cache entry matched
  Google's owner/session. Apple had no cached entries
  (`google-note-cache-before-switch.json`).
- After Google sign-out, Google had no active sessions and no cached entries;
  Apple had one active session and its original lantern chat returned
  (`apple-return-state.json`, Apple return screenshot).
- Reopening Apple's note displayed the correct summary and rebuilt only the
  Apple cache (`apple-note-cache-after-return.json`, reopened screenshot).

This proves the exercised native note/history switching and ready-summary
cache-clearing path for two distinct real provider identities on one simulator.
The source files remain owner-scoped on disk; this is access isolation and
cache clearing, not deletion of all local source files on sign-out. No model
recall request, interrupted capture switch, multi-window race, physical device
or independent second person's account was exercised. Do not treat this as
full `access` verifier acceptance or hosted rollout approval. Native automatic
refresh, provider recovery, populated account erasure, migration and remaining
release gates still require their own evidence.


## Populated Apple deletion and Google preservation

September 30 follow-up, same isolated real-provider server and unchanged signed
Release simulator binary. Founder confirmed readiness and used the native profile
Delete account action while Apple owned its fictional lantern source/note/chat.
The service completed deletion and its real Apple revocation call returned success
(counter advanced from one to two). All inventoried Apple owner rows were absent,
including the owner and provider grant; native account sessions/outbox contained
only deletion tombstones. Google rows in every inventoried memory owner table
matched their pre-deletion hashes. Budget, policy and request rows also matched.
The app showed deletion success and stayed signed out after terminate/relaunch.

Founder then signed into the same Google account and opened Fictional Google
compass. The server returned the original Google owner; all Google content hashes
still matched (new credential mapping expected). The note visibly retained its
summary. Another terminate/relaunch returned directly to signed-in home showing
Google's original fictional chat. See `populated-apple-deletion-result.json` and
`populated-apple-deleted.png`, `populated-apple-deleted-relaunch.png`,
`google-note-after-apple-deletion.png`, `google-preserved-relaunch.png`.

This proves populated Apple deletion with another real provider identity's local
QA data preserved. It does not prove populated Google deletion, real fresh-proof
deletion recovery, independent-human isolation, physical Release acceptance or
founder migration. Hosted data and the physical phone were unchanged; no paid
provider/model calls occurred. The Google account remains signed in in the local
QA simulator. Only seeded fictional data was erased.
