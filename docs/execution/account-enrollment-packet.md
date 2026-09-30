# ACCOUNT-1: Google and Apple enrollment

## Recorded continuation — September 30, 2026

This packet preserves enrollment preparation and setup history. Real Google and Apple enrollment, populated local switching/deletion, both native automatic-refresh paths and local fresh-proof recovery now have bounded evidence. Recorded hosted candidate `208ca34b` runs schema 21 with accounts/deletion enabled; physical founder Google migration and provider switching passed. See [release handoff](testflight-release-handoff.md), [lifecycle evidence](../qa/account-lifecycle/README.md), [Apple recovery receipt](../qa/account-lifecycle/apple-fresh-proof-recovery.json) and [migration outcome](founder-account-migration.md). None is a fresh runtime check by this documentation pass.

PR159–177 remain candidate/unmerged checkpoints. Phase 1 is incomplete; independent-human isolation, capture/sign-out and revoked-provider/failure paths, physical deletion and retention/restore acceptance remain distinct gates. The Apple agreement was accepted and App Store record `6817680460` created; no TestFlight upload or working paywall is established. Earlier preview-only, schema-20 and “No Apps” observations below describe their dated checkpoints, not current implementation. Preserve the shared UI design system and complete Phase 1 before pricing, paywall, release preparation and pilot.

Prepared September 29, 2026 against main `6af767d`. Implementation packet, not delivered authentication.

## Decision and bounded outcome

Founder selected both providers, Google above Apple. A fresh Release installation should sign in through either provider, receive its own backend session, and reopen the same account after relaunch or reauthentication. Two accounts must never see each other's recordings, notes, chat, memory or local cached content. Existing founder credentials and data must remain intact until an explicit, verified migration.

## Implementation direction

Use official Google Sign-In for iOS/macOS and Apple's AuthenticationServices, with provider adapters separated from shared session state. Verify provider tokens on the existing backend using maintained verification libraries and explicit issuer/audience/expiry checks; never accept a client-supplied identity. Bind Apple authorization to a server challenge/nonce and prevent exchange replay. Keep provider secrets out of app bundles, browser JavaScript and logs.

Map `(issuer, subject)` to a stable internal account identity. Session rotation must not create a new memory owner. Matching email is insufficient for account linking; linking requires proof of both identities. Preserve existing owner mappings and budget ledgers. Do not automatically import the founder's local recordings into a newly signed-in account.

Keep authentication and refresh credentials in native Keychain storage. The shared UI receives safe account/loading/error state and sign-in actions, not credentials. Google appears first, Apple second, with equivalent accessibility and clear cancellation/retry feedback. Preserve the approved shared UI. Fail closed when deployment/provider configuration is absent.

The enrollment packet needs the owner-switch boundary from ACCOUNT-2: stop authenticated work and clear or partition cached notes, local recordings, drafts, chat, outboxes and in-flight responses before exposing another account. Full deletion/retention and existing-owner migration retain their own checkpoints; do not expose migration or claim complete account lifecycle prematurely.

## Configuration prerequisites

- Google Cloud project with configured consent/branding and native OAuth client IDs for `ai.voicecompanion.phone` and `ai.voicecompanion.mac`, plus a server audience/client ID for backend validation. Identify the actual project before creating credentials. No calendar, email, Drive or other data scopes are needed for login.
- Apple team `7HF6VDCZF7`, Sign in with Apple capabilities for the app identifiers and applicable signing profiles. Check current agreement status; only the founder accepts legal terms.
- Explicit backend/native environment pairing and callback configuration. Confirm provider configuration before any real-provider acceptance claim.

## Verification and checkpoint gates

Exercise signed-token validation locally with adversarial fixtures: wrong issuer/audience, expiry, invalid signature, replay, missing subject, cancellation, key rotation and unavailable provider. Verify stable owner mapping, session expiry/revocation/rotation and concurrent refresh. Exercise the actual local service to read synthetic notes/chat as two users and reject cross-owner reads/writes. These fixtures are not proof of real Google/Apple enrollment.

Run the actual UI for success/loading/cancel/error states, Google-before-Apple order, relaunch and owner-switch cleanup, including stale in-flight callbacks. Then verify both real providers on a fresh Release installation and with two actual users. Wait for founder readiness before manual device checks. No paid model call is needed to establish authentication or synthetic data isolation.

Open a focused PR with exact source/configuration, reproducible checks, sanitized receipts and limitations. Do not merge real enrollment as complete without provider/device evidence. `verify_feature.py access --checks-only` is supporting coverage, not account acceptance.

## Official references checked September 29

- [Google native setup](https://developers.google.com/identity/sign-in/ios/start-integrating)
- [Google backend token verification](https://developers.google.com/identity/sign-in/ios/backend-auth)
- [Apple capability setup](https://developer.apple.com/help/account/capabilities/about-sign-in-with-apple)

The native sign-up preview already orders Google before Apple. At this initial inspection neither preview button authenticated. The then-current backend's `Admission.enroll` issues developer credentials; production provider enrollment and refresh are absent.


## Provider setup progress — September 29

Created the dedicated Google Cloud project `ellis-voice-companion` (Ellis). OAuth branding is configured for an external testing audience, using the founder-approved temporary support/developer email until a domain is available. The founder accepted the Google policy and the console confirmed configuration creation. No extra Google data scopes, App Check or agent permissions were enabled. Tester selection remains open.

The five explicitly confirmed unrelated Google Cloud projects were shut down: `insurance-voice-agent-508905`, `treena-usetreena`, `keep-504920`, `rapid-sphinx-476102-u8`, and `gen-lang-client-0811543359`. Each returned a pending-deletion receipt for October 29, 2026; only Ellis remained in the active-project list. This was Google Cloud cleanup, not deletion of unrelated Apple identifiers or local repositories.

### Google OAuth clients created

All three approved clients returned successful creation receipts on September 29:

| Client | Type | Public client ID |
| --- | --- | --- |
| Ellis iPhone | iOS | `774278865935-knco8v1bf8u8qudkj3fn7bab73am87d6.apps.googleusercontent.com` |
| Ellis Mac | iOS (Google native SDK requirement) | `774278865935-2142r4ndqoruu9jcug5s8uk44q2aj7bq.apps.googleusercontent.com` |
| Ellis Backend | Web application | `774278865935-gjppp5pd2i4hpatuf8nctteb9m0adf9c.apps.googleusercontent.com` |

Native bundle/team values match the packet above. No browser origins or backend redirect URIs were added. These IDs are public configuration, not secrets. The backend client secret is not required for the planned ID-token verification flow and was not stored in the repository. OAuth client creation does not prove real sign-in; native/backend implementation and provider acceptance remain outstanding.


### Apple identifiers registered

Founder approved registration and Sign in with Apple capability on both bundle identifiers. Registered `Ellis iPhone` (`ai.voicecompanion.phone`) as the primary Sign in with Apple App ID under team `7HF6VDCZF7`. Registered `Ellis Mac` (`ai.voicecompanion.mac`) grouped with that primary, following Apple's [related-app grouping guidance](https://developer.apple.com/help/account/capabilities/group-apps-for-sign-in-with-apple). Both identifiers are visible in the account list after registration. No unrelated Apple identifiers were changed. Provisioning, native entitlements, provider token exchange and physical sign-in still require implementation/verification; identifier registration does not establish those capabilities.

### Apple agreement cleared

After the founder accepted the updated agreement, a fresh App Store Connect reload no longer displayed the Developer Program License Agreement warning. The Apps page still says No Apps. App record creation, archive/signing and TestFlight upload remain outstanding. The EU trader-status notice remains a distribution consideration, not evidence of completed compliance.

## First implementation checkpoint: stable identity storage

Schema 20 adds `(issuer, subject)` → owner mapping in the existing memory database. The server-only `owner_for_identity` operation atomically binds a fresh credential to the returning identity's owner, or creates an isolated owner for a new identity. Existing founder credentials cannot be adopted or reassigned. No email linking, enrollment endpoint, token verification, refresh service or native login is delivered by this storage checkpoint.

[Account identity QA](../qa/account-identity/README.md) records synthetic identity, migration, concurrency and actual local WebSocket isolation evidence. Hosted deployment remains unchanged. Do not run schema-19 binaries on an upgraded database or restore a historical backup over newer ledgers/deletions. At this checkpoint rollback targeted an accounts-disabled schema-20-compatible build and schema 21 was undeployed. The later recorded schema-21 deployment requires a compatible rollback; never use that historical schema-20 rollback against it.

## Founder constraint: preserve the established design system

September 29 clarification supersedes the earlier blanket UI-code freeze: functional frontend wiring for Google/Apple sign-in and necessary account/privacy pages are authorized. The current UI design system is the source of truth. Reuse existing components, styling, typography, colors, spacing and motion; preserve established screens and interactions. Do not redesign, restyle or reinterpret the app's visual character while preparing TestFlight. Google remains above Apple. Verify functional additions in the actual app against the existing design system.

Functional frontend work must reuse the existing components, animations, transitions, press feedback and haptics. Treat the established UI/UX system as the source of truth; no new visual or interaction system is authorized. Founder explicitly reaffirms proactive verified checkpoint merging. Founder authorizes $5 total for provider/API tests toward TestFlight readiness, without automatic paid retries. Preserve earlier ledgers; this does not cover hosting upgrades, subscriptions or other purchases. Record each run in the TestFlight provider-testing ledger before spending.

### Apple server key registered

September 29: founder explicitly approved the action-time key request. Registered `Ellis Sign in with Apple`, key ID `6JCPHWJT4A`, with only Sign in with Apple enabled, scoped to primary `ai.voicecompanion.phone` and its grouped Mac app. Registration initially encountered an expired portal session; the refreshed inventory confirmed no key existed before retrying. The final portal showed the registered key and completed download. The download event observer timed out, but the actual file was present in Downloads; it was validated as P-256 and moved to owner-only local credential storage outside all repositories. No private material appears in source, logs or screenshots. This does not establish deployed secret configuration or real Apple authentication.

### Historical configuration staging, superseded by enabled rollout

The registered Apple key and locally generated Fernet encryption key are configured on the existing Render voice-companion service with the selected Google/Apple client IDs. Per-variable API writes preserved every pre-existing setting, verified by readback; values are never recorded here. At that staging checkpoint `VOICE_ENABLE_ACCOUNTS=0` was set. Subsequently the backend was deployed with accounts enabled and both real providers passed basic Release-simulator enrollment; see [current native account QA](../qa/native-accounts/README.md). The signing key registration receipt is not account acceptance.
