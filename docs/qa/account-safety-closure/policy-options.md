# Unselected account safety contract options

October 1, 2026. These are reviewable proposals, not founder decisions or implemented behavior. Shared-file ownership, configuration, credentials, deployment and destructive actions require their own authorization. No acceptance requirement is waived here.

## Managed content copies

Choose an explicit duration, for example **7 days** (shorter copy exposure, shorter recovery window) or **30 days** (longer recovery window, longer exposure). Neither is selected. A concrete proposed operational shape is daily coordinated SQLite snapshots plus hourly scans of registered expiries, with inspected failure/status receipts and an operator responsible for interrupted pruning. The existing module does not schedule snapshot creation. Its expiry scans are delayed by downtime, contention and fail-closed errors, so either duration is a target rather than an unconditional wall-clock erasure maximum.

Before enablement: inventory and classify the 488 observed nested copies, separately identify downloadable/off-host copies and owners, preserve spending/deletion history, decide each copy class's retention and verify provider disk-snapshot policy. Directory-name matches authorize no removal. The managed module will not adopt historical or unknown copies automatically. Provider snapshots and physical remnants are separate from application-copy expiry.

Inspect a matching deployment/configuration and coordinated backup before enabling any schedule. Rehearse deletion-safe quarantine using independently established current authority; do not activate a restored pair merely because its hashes validate. The current module has no restore activation path and rejects general historical-content reconciliation.

## Google external consent

**Current contract:** Ellis app sessions follow local refresh-secret state and the fixed 30-day family deadline. Sign-out, replay, local-owner revocation and deletion revoke locally. Google refresh does not poll external consent; successful final revoke response is an accepted request, not proof of propagation. This boundary needs explicit product acceptance if retained.

**Separate implementation option:** configure a Google Cross-Account Protection receiver and verify security-event signatures, issuer, audience and subject before ending only the corresponding owner's open sessions. Cover supported session/token revocation events, duplicate `jti`, stale/replayed/invalid events, unknown/deleted subjects, concurrent refresh and unrelated-owner preservation. Persist inspectable, content-minimal event outcomes. Do not invent an email-derived owner mapping or automatic identity linking.

[Google's official RISC documentation](https://developers.google.com/identity/protocols/risc) describes `sessions-revoked` and `tokens-revoked` responses, warns events can be permanently missed after limited delivery retries, and states that security events are not currently sent for Google Workspace users. Therefore even this option does not justify an instantaneous, guaranteed or all-account consent-removal claim. Explicit Workspace coverage/fallback would need its own reviewed contract before policy selection. Receiver registration and project/service-account configuration are new prerequisites; no credentials or permissions are requested by this document. A reviewed reconciliation/fallback contract would be a further decision.

## Final Google grant binding

**Current limit:** after content erasure, the deletion-secret holder submits an opaque Google grant. The server's accepted revocation response is not proof that the grant belongs to the deleted subject or configured Ellis client. A separate valid identity token alongside an arbitrary refresh token would not fix that binding.

**Reviewable implementation option:** redeem a Google server authorization code at the backend under the configured OAuth client; verify provider-issued identity against the expected issuer/audience/nonce/subject from the same authorized exchange, then keep the resulting encrypted server-owned grant bound to that identity through deletion. Fresh-proof recovery must establish the same retained identity before replacing its grant. Reject wrong client/subject, reused code, missing/unverified identity and uncertain provider responses without releasing the deletion reservation. Keep completion idempotent across lost responses, preserve spending, and never automatically retry paid/provider operations.

The native adapter already captures `serverAuthCode`; the native transport includes `authorization_code` only for Apple and omits it for Google. The backend explicitly rejects Google exchange/recovery requests containing `authorization_code` (`Backend/account_service.py:76`). This option would therefore require a deliberate protocol extension, bounded backend/native/provider/storage changes, OAuth client configuration, independently reviewed cryptographic linkage and real-provider evidence. It is intentionally **not** implemented in this lane and may intersect H1b-owned schema/runtime files.

The alternative is explicit acceptance of the current limited finalization contract with accurate product/operational wording; tests cannot make that decision. Review the concrete implementation and failure semantics before asking Nathan to select a policy or grant new configuration/deployment access.
