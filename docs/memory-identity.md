# Memory rework checkpoint 1B — source-backed identity storage

This checkpoint delivers structured mentions, opaque entities and evidence-backed links. It does not yet replace the legacy model identity judgments or complete identity-dependent lifecycle transitions (checkpoint 1C).

## Stored contract

Schema 5 adds four tables: `memory_mention`, `memory_entity`, `memory_identity_link`, and `memory_identity_support`. A mention belongs to one claim and original source passage/revision. Its description preserves name, relationship, distinguishing qualifiers and an optional source speaker label. The person mentioned and the speaker remain different concepts. A fresh entity is an opaque referent, never proof that the subject is the account owner.

Claim commit writes mentions atomically with claim support. The existing writer now preserves the name/relationship already extracted and records qualifiers as null (not yet extracted). Null is not equivalent to an empty qualifier list. Speaker identity remains unknown; original transcript speaker labels remain in source evidence. No new extraction or linking inference is run.

`IdentityStore.link` is an internal storage boundary for an accepted identity decision, not a client endpoint or semantic classifier. No anchor means a fresh entity. Connecting a mention to an existing entity requires an active anchor link and live source evidence for both mentions. Optional additional bridge evidence is tracked too. Known differing relationships/qualifiers and incomplete qualifier metadata block a link. Equal names never automatically connect anything. These conservative rules do not yet handle relationship changes or aliases semantically; that is later model integration.

A repeated identical decision is idempotent. Reassigning an active mention or silently changing the evidence/rubric is rejected. The graph only points to already-active links, so it cannot introduce a dependency cycle. Owner/source revision checks and writes occur in one SQLite transaction.

Search results expose independent `identity_status` and `entity_id`: legacy_unverified, unresolved, or established. Established means the live mentions have compatible supported entity links; it does not mean biometric verification, account-owner identity, or claim truth. Legacy subject strings are preserved, never backfilled into entities. Current legacy model request construction removes these new annotations until its independently evaluated replacement is ready; a regression test proves the request is unchanged.

## Source change and deletion

Within the source invalidation transaction:

- Scrub descriptions of affected mentions and mark them invalid.
- Invalidate links relying on the source, including a separate bridge source.
- Invalidate all links depending on those anchors transitively.
- Remove identity-support references to the changed source. Remaining live claims become identity-unresolved as appropriate; they are not silently reassigned.
- Preserve independent surviving support. For a duplicate claim with two source mentions, deleting one source does not erase an independently supported surviving identity link.

Opaque IDs may remain for stale-write diagnostics; deleted descriptive content is scrubbed. Original claim support/tombstone behavior remains in force. This is not a claim about historical backup erasure.

## Behavioral QA

Python 3.13 on the development Mac; all writes use temporary SQLite databases. No paid calls, live data changes, app installs or deployment.

```sh
python3 -m unittest discover -s Backend -p 'test_memory_identity.py' -v
python3 -m unittest discover -s Backend -q
```

Eleven focused tests exercise actual store transactions: same-name separation, opaque identity, accepted fixture linking, restart/idempotency, qualifier/relationship/unknown metadata guards, anonymous speaker protection, cross-owner denial, bridge deletion and transitive invalidation, source revision and descriptor scrubbing, atomic rollback, duplicate support and schema-4 migration. Migration preserves legacy IDs, account identity and deletion tombstones, makes no backfill, and passes SQLite integrity/foreign-key checks. Existing Maya replay now also verifies structured mention persistence through the actual writer.

Full backend suite: 98 tests passed. Shared-schema, read-contract and legacy provider-payload compatibility justify the broader run. Provider judgments in these tests are saved or synthetic; link quality has not been evaluated against a live identity model. Local relay/audio fixture logs are not provider usage.

## Remaining gates and rollout

1C must connect lifecycle changes to their identity evidence so that a correction depending on a revoked identity can be reopened safely. Until then, the legacy writer still uses its old subject contract for lifecycle transitions; storing the new identity ledger does not fix that entire path. New model link decisions, qualifier extraction and qualified identity retrieval also require later checkpoints. Do not enable this as a completed semantic identity solution.

Migration is additive with no paid reprocessing. Old schema-4 binaries reject schema 5. Hosted schema remains unchanged; deployment still requires the concrete rollout gate and compatible backup/migration verification.
