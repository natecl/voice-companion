# Source-preserving consolidation — checkpoint 4E

Opt-in `EvidenceWriter(..., consolidation=True)` can attach a repeated current fact/preference to one existing claim. Luna must establish identity continuity and Jev must independently classify the fact as duplicate. Similarity, a shared name or recency is insufficient. The first path requires exactly one candidate, established matching identity, stated/current untimed evidence, matching fact kind and no expiry. Dated events, same-source repeats, truncated candidate pools, multiple possible targets, different qualifiers and ambiguous identities stay separate/unresolved. This is not a general duplicate-clustering algorithm or historical backfill.

Schema 9 retains a proposal and judgments per claim/owner/source/revision instead of one proposal per claim. Every source retains its original spans; comparison reads use the proposal belonging to that source when trimming long passages. Atomic writes validate prior snapshots before adding support. Incoming mentions are linked without rewriting old mentions. One consolidated memory presents multiple source links; correction targets the shared claim once.

Deleting a repeated source retains the original claim when its evidence/identity remains supported. Deleting the identity anchor retains surviving factual evidence as unresolved instead of claiming the identity is still proven. Removing the final source invalidates/scrubs the claim as before. Corrections retain their conservative reopening behavior on lost identity dependencies. Identity-independent survival after deleting an anchor is not claimed.

## Context fix and live evidence

The first live run safely abstained from consolidation: extraction quoted only the fact, excluding “To repeat what I told you before.” The identity model lacked that continuity evidence. Preserve this failed run in `Backend/fixtures/memory_consolidation/failed-v1/`. No thresholds were lowered.

The opt-in identity comparison now supplies the exact cited span plus up to 200 characters on each side from the original incoming passage. This follows the article's contextual-integrity principle. Target claims, source provenance and identity rules remain unchanged; extracted qualifiers and original text are still checked. Existing non-consolidation requests remain unchanged.

The revised live run replayed unchanged requests and spent only on changed/new requests. It learned swimming, consolidated its repeat into one claim with two sources, kept the other daughter Maya's painting fact separate, and replaced swimming with tennis once. All designated checks passed. Recorded requests/responses and inspected storage snapshots are in `Backend/fixtures/memory_consolidation/recorded/`.

## QA and migration

Local macOS/Python 3.13: six focused consolidation tests pass, including exact live-request replay through the real writer/SQLite store, deleting either supporting source, correction after consolidation, added interests, and migration of a populated schema-8 database with unchanged evidence. Integrity and foreign-key checks pass; migration queues no inference jobs. Full backend suite passed 220 tests before adding the final exact-replay case; the six-test focused suite then passed with that case. Existing ResourceWarnings remain separate cleanup.

Live QA used isolated scratch code and synthetic databases on the existing Render host with the canonical QA ledger. The production source database, app configuration and deployed code were not migrated or deployed. The feature defaults off. A production migration requires backup and the later approved rollout gate.

## Approved allowance

Founder approved an additional $0.20 and continued autonomous progression through verified checkpoints, stopping only for genuine founder-dependent gates. Approval `memory-consolidation-additional-2026-09-26-020` reserves $0.20 once in the global ledger before exposing it in the QA sub-ledger. Existing callers do not automatically receive it. Local tests verify idempotency and the hard cap; provisioning succeeded in the canonical ledgers.

New total cap: $2.20. This checkpoint used 16 calls (6 failed-run calls, 10 changed/new calls for the passing run). Cumulative **211 calls/$2.11 reserved; $0.09 remains**: Luna 82/$0.82, Jev 129/$1.29. Reservations are conservative, not invoices. No automatic retries or local authorization-ledger copies.

Next priority: retrieval and bounded context assembly, while keeping broader temporal-language and consolidation limitations explicit.
