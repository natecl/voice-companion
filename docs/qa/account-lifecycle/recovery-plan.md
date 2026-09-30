# Real fresh-proof recovery check

Prepared September 30; not executed. Use only the existing isolated localhost
service and Ellis Real Account Lifecycle simulator, whose current Google account
has zero sources, notes and chat turns. The physical phone stays on hosted Google.

Expected outcome: after an accepted deletion loses its original client receipt,
normal enrollment remains blocked; fresh Google proof recovers only deletion
authority, finishes real grant revocation, and leaves the app signed out. It must
not create a new content session or restore erased data.

Obtain founder readiness before beginning. Explain that the simulator uses real
Google authorization and final revocation may require Google reauthorization in
other Ellis installations; hosted content is not part of this erasure.

1. Preserve fresh private SQLite backups and the session/budget baseline. Confirm
   the same local TLS endpoint, running generation-disabled server and empty QA
   owner. Do not restart or replace its databases.
2. Create one separate synthetic app-session family for that existing real QA
   identity, following the existing backend refresh fixture's pattern. Send one
   `delete_account` request through the local TLS endpoint and stop at
   `awaiting_google_revocation`. Retain the original receipt privately for recovery
   from test failure, but never stage it in native Keychain. This is intentional
   interrupted-client setup, not proof of a real network outage.
3. Confirm pending identity reservation, erased content, revoked old sessions and
   unchanged budget/policy/request history. No Google revocation is requested by
   this preparation. Inspect uncertain results before any retry.
4. Founder signs out in the simulator and uses the same Google account. Normal
   enrollment should show the finish-deletion recovery instruction. A second
   provider sign-in supplies fresh proof to the actual recovery endpoint.
5. Inspect the actual Google revocation outcome, complete deletion state, released
   identity reservation, no newly issued content session, native tombstones and
   signed-out restart. Preserve sanitized receipts and failure evidence.

This closes only the exercised real Google fresh-proof recovery path. It does
not establish Apple native recovery, independent-human isolation, backup expiry
or physical erasure. Do not reuse the plan against hosted founder data.
