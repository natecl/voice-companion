# ACCOUNT-1: Google and Apple enrollment

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

The native sign-up preview already orders Google before Apple. Neither preview button currently authenticates. The current backend's `Admission.enroll` issues developer credentials; production provider enrollment and refresh are absent.


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

[Account identity QA](../qa/account-identity/README.md) records synthetic identity, migration, concurrency and actual local WebSocket isolation evidence. Hosted deployment remains unchanged. Do not roll schema 20 back to schema 19 binaries against the upgraded database; use the predeployment backup if a future deployment needs rollback.
