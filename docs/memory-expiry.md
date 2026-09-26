# Independently verified expiry — checkpoint 4D

Opt-in `EvidenceWriter(..., expiry=True)` adds one bounded Jev decision for a supported current, stated claim with a whole temporal expression `through YYYY-MM-DD`. The existing extractor preserves the original expression; the existing independent support, modality and time gates still run. No extra call occurs when the expression is unsupported. The default writer remains unchanged; this is not hosted enablement or backfill.

Jev determines whether the inclusive through-date ends applicability of the entire claim, separately from event dates, nearby facts, negation, quotations and hypotheticals. Only `ends` with probability >=0.95 and confidence >=0.60 authorizes expiry. Abstention preserves the source and claim without inventing an end date. Code computes the exclusive end at next local midnight using the source IANA timezone; invalid dates/timezones, ambiguous or nonexistent midnight and boundaries before capture are rejected. The boundary is recomputed inside the atomic commit, and the judgment is saved with its version. Late deletion/revision still invalidates the job. Provider failures stop the job rather than silently commit an unverified expiry.

Expiry excludes current applicability at read time and allows internal maintenance to persist the expired state. It preserves historical evidence and never implies an event was completed. Stable facts do not decay. No user-facing memory management is added.

## Evidence and allowance

September 26, 2026. Synthetic QA ran in an isolated scratch directory on the existing Render host, using the canonical `/var/data/voice-companion/memory-budget.sqlite` ledger. No app deployment, runtime flags or user-source database changed. Code and fixtures were copied to scratch; only synthetic evidence and canonical QA reservations were written.

Six frozen role cases passed in one live Jev batch: temporary stay and temporary access accepted; a nearby pool-pass date, negated stay, nearby festival date and quoted example rejected. Then the actual writer used Luna extraction, Jev support verification and Jev expiry verification on `I am staying in Boston through 2026-09-30.` It stored valid_until=1790827200 (October 1 midnight New York). At that instant current search excluded it; history and original source remained. Recorded evidence lives in `Backend/fixtures/memory_expiry/recorded/`.

Four paid calls, no retries: one Luna and three Jev. Canonical cumulative reservations: **195 calls, $1.95 of $2; $0.05 remains** (Luna 74/$0.74, Jev 121/$1.21). These conservative reservations are not invoices. This supersedes the balance in memory-chunk-writer.md.

Local macOS/Python 3.13: exact-request replay through real writer/SQLite reproduces expiry and original-source retention; deleting the source during the final judgment prevents any late commit. Recorded negative judgments do not produce expiry. Boundary tests cover inclusive dates, DST arithmetic, unsupported dates, future/tentative proposals. `python3 -m unittest test_memory_expiry` reproduces the focused checks; `python3 -m unittest discover` passes all 215 backend tests. Existing SQLite ResourceWarnings remain separate cleanup. Real model evidence is bounded to these fixtures, not a general accuracy guarantee or native-device acceptance.

## Limits and next work

This first verified path supports explicit ISO through-dates only. Month-name dates without a year, weekdays, `until` boundaries, compound expressions and richer conversational expiry remain unresolved; no regex guesses a missing year. Future or tentative plans do not acquire expiry through this path. Consolidation and the reworked retrieval/context assembly are still pending. The complete memory rework is not deployed.
