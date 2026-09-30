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

## Founder decision

The founder selected Google for the existing development data and confirmed
that Google and Apple remain separate accounts with persistent sign-in. No
account linking is included. Preserve Apple data and unrelated legacy owners;
verify the exact legacy source and Google destination before any cutover.

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
are complete. The destination decision is resolved; source identification and migration
implementation/rehearsal remain unfinished.

## Verified physical source

A read-only copy of the paired iPhone's existing `VoiceCompanion` application
support directory contains four saved sessions, all bound to legacy label
`2dc1fb70ce3b`, and 20 outbox records for that same owner, all acknowledged.
This matches the hosted legacy owner's label. No raw owner IDs, content or
credentials were committed. See the [sanitized inventory](../qa/account-lifecycle/founder-source-inventory.json).
The private copy is under the protected local Ellis QA directory; it is an
inspection snapshot, not a coordinated cutover backup. The phone was not reset,
updated or modified.

## Preferred migration design to verify

Preserve this legacy owner's stable ID and its content references; explicitly
bind the verified selected Google identity to it rather than rewriting every
source/chat/memory row. This requires proving that Google's current owner is
empty across the full data inventory at cutover, revoking stale Google sessions,
and keeping the superseded owner unavailable without losing budget history.
Never use ordinary enrollment to perform this reassignment. The founder's four
local sessions and outbox can retain their original owner references while
moving into managed owner-scoped storage through a verified one-time migration.

Still needed: implementation, coordinated backups/rehearsal, proof of the
selected hosted Google identity, transition from the legacy app state to Google
sign-in, stale-write handling and actual native/server cutover acceptance.
No mapping, credentials, live files or ledgers have been changed.
