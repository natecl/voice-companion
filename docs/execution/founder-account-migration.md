# Founder account migration: decision and preparation

September 30, 2026. Read-only inspection; no migration implemented or executed.

Hosted memory remains schema 20. A fresh read-only SQLite inventory found two
legacy owners with content and separate Apple/Google enrolled owners. Counts
below include stored rows and are not a claim that every source is active.
No content, provider subjects, credentials or raw owner IDs were exported.

| Pseudonymous owner | Provider | Source rows | Note rows | Chat turns | Claim rows |
| --- | --- | --- | --- | --- | --- |
| 2dc1fb70ce3b | legacy | 23 | 4 | 8 | 0 |
| a120c666b0ed | legacy | 1 | 0 | 3 | 1 |
| 8edc6e32268c | Apple | 1 | 1 | 0 | 0 |
| c5bff466523a | Google | 0 | 0 | 0 | 0 |

These labels are SHA256(owner) prefixes for comparison only, not verified human
identity. Do not infer which legacy owner is the founder from row count. The
hosted Apple content means earlier empty-account assumptions must not be used
for migration. Local simulator fixtures are a separate database and do not
establish hosted content or migration readiness.

## Required founder choice

Choose where existing founder data belongs: Google, Apple, or one account
accessible through both. Both sign-in buttons working does not authorize
silently linking identities. A linked account requires explicit authenticated
proof of both providers; matching email alone is insufficient.

## Implementation requirements after selection

Identify the precise legacy source using the existing founder installation's
credential/owner binding and fresh authenticated destination proof. Prepare a
read-only plan including local sessions/outboxes/cache, hosted content, notes,
chat, retained knowledge, credentials, provider grants and all budget ledgers.
Preserve other legacy owners and the existing enrolled Apple recording/note.
If a destination already has content, define conflict handling without loss;
never overwrite it or assume it is disposable QA data.

Keep stable source/evidence references. Rehearse on coordinated private copies
and verify counts, content hashes, foreign keys, isolation and rollback. Freeze
or serialize account writes for the actual cutover. Invalidate obsolete sessions
and require reauthentication without resetting historical spending. Reconcile
owner-scoped local storage explicitly; automatic import on ordinary sign-in
remains prohibited. Apply only after the selected plan and real-path verification
are complete. Current work is stopped at the destination decision.
