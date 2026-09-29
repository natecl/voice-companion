# Stable provider identity storage — September 29, 2026

Bounded candidate on `codex/account-sign-in`, based on `6af767d`. This checkpoint adds storage for already-verified Google/Apple issuer+subject pairs. It does not expose an authentication endpoint or verify real provider tokens. No deployment, phone installation, paid model calls or production-data modification occurred.

## Reproduction and results

Python 3.13, websockets 15.0.1, temporary SQLite databases, fictional subjects and transcript content. Run from the checkout:

```sh
python3 -m unittest discover -s Backend -p test_account_identity.py -v
cd Backend
python3 -m unittest test_admission test_memory test_companion_chat test_memory_atomic test_memory_identity test_memory_retention test_memory_transitions test_recording_notes
```

Seven new checks and 87 affected regression checks pass. The real localhost WebSocket test executes Relay and MemoryService, writes a synthetic source as user A, opens a fresh credential for the same identity and observes `unchanged`, rejects user B's write/delete attempts with `memory_owner_mismatch`, and observes HTTP 401 after revoking A's old credential while the new credential still works. Direct source reads confirm user B has no source and A's source was not modified. The admission usage ledger remains empty.

Other checks cover concurrent first logins resolving to one owner, restart and backup continuity, issuer separation, malformed identity rejection, schema-19 upgrade preserving founder content, and refusal to adopt or reassign an existing credential. Email is not an input. The method is server-only and must be invoked only after cryptographic provider validation in the next slice.

The initial affected-regression run failed seven synthetic schema-downgrade fixtures because they retained the newly added table while marking the database as an older version. Corrected those fixtures to remove the schema-20 table and updated expected schema versions; the production migration remains strict. The rerun passes. An existing unclosed SQLite ResourceWarning appears in the admission regression run; no test failed from it.

## Inspection and limits

Identity and credential ownership commit in one SQLite transaction. A conflicting credential raises before any new identity or owner is inserted. There is no email merge or client-supplied owner, no change to budget reservations, and no automatic migration of founder data. Returning subjects are scoped to canonical provider issuers. The public service continues to accept only existing admission credentials; it does not call this new binding API from unverified client input.

Full account acceptance remains open: provider JWT validation, replay protection, session issuance/refresh, native Google-above-Apple UI wiring, Keychain lifecycle, cancellation and cache/outbox isolation, real provider/device QA, deletion and explicit founder migration. Schema 20 requires a predeployment database backup and deliberate rollback plan; schema 19 binaries reject the upgraded database. Feature gates remain unchanged.
