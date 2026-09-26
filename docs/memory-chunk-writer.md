# Evidence writer for long recordings

Status: backend integration verified; not deployed. This extends the bounded atomic writer from PR 41 through the existing deterministic/optional Jev chunk planner. It does not complete the whole memory rework or authorize hosted rollout.

## Delivered behavior

`EvidenceWriter(..., chunking=True, semantic_boundaries=True)` partitions oversized sources under the evidence extractor's actual request limit. Small sources retain their direct path. Existing callers keep chunking off unless explicitly enabled. The planner retains original passage IDs and character ranges, bounded context overlap, hard size limits and a 32-chunk cap. Semantic boundaries reuse Jev's existing independent boundary questions; uncertain boundaries retain overlap. These heuristics do not guarantee perfect topic segmentation.

Each chunk's extraction and source judgments are durably saved using a versioned contract. Exact mapped spans refer to the original transcript, including the correct occurrence of a quote repeated elsewhere in a long passage. Overlap-only proposals do not create a second memory; only identical proposals at identical source ranges are deduplicated. Semantic consolidation remains checkpoint 4 work.

All chunks finish before identity/correction resolution and the final source-wide transaction. A later chunk can correct an earlier one. Interrupted work leaves no partly published source. Explicit reviewed recovery reuses completed chunks and cached successful calls; an uncertain paid attempt is never silently retried. Source revision/deletion rejects late work. Old-writer chunk contracts cannot be reused by the new writer. No additional schema migration is required beyond the existing schema 8.

Verification requests contain cited passages rather than unrelated transcript turns. A comparison against a long prior passage uses the exact stored evidence span plus at most 200 characters on each side, preserving the complete cited quote and original provenance. Oversized individual comparisons still fail explicitly. Identity-size failures quarantine their source instead of stopping unrelated jobs; authentication, budget and unknown failures still halt paid processing.

## Provider responsibilities

- Luna extracts evidence. For recordings, the structured schema allows only named or unresolved subjects, and requires name presence to agree with that category. Application provenance is explicit. Recording speakers cannot become account owners.
- Luna with low reasoning verifies recording subject descriptions and resolves identity across candidate memories. This is an implementation extension within the approved identity role: a name mention, relationship to a recorded speaker, and qualifiers must match the cited text. Exact quoted evidence is required; self-reported confidence is not manufactured into a probability. Uncertainty does not authorize an identity link.
- Jev independently verifies fact support, stated/tentative status, temporal assertions, relation and correction applicability. Authenticated personal-text subject verification retains its previously verified Jev path. Extraction/answer model reasoning settings are unchanged.
- Application code enforces provenance, ownership, live source revisions, descriptors, exact spans and transactional lifecycle rules. A model verdict alone cannot bypass those guards.

The recording attribution extension follows a bounded comparison, not an assumption that one model is universally superior. Initial Luna extraction attempted unsupported account-relative scope; the parser rejected it. Constraining the output schema prevented this category. A later name/scope mismatch was also rejected, then prevented structurally. Jev's recording subject classification confused speaker-relative descriptions with account-owner relationships. Narrower evidence and focused questions did not meet the positive/negative gate consistently. Failed variants are retained under `fixtures/memory_evidence_chunks/failed*` and `aspects-failed*`; they are not passing evidence. No thresholds were lowered.

## Verification

Synthetic provider gates ran in isolated Render directories, most recently `/tmp/memory-chunk-writer-v8/Backend`, against synthetic QA databases. Production code and the canonical production memory database were untouched.

- `recording-identity/result.json`: all eight Luna attribution cases passed, covering named subjects, corrections, invented/missing qualifiers, wrong relationships, quoted subjects and anonymous first-person evidence.
- The focused Jev comparisons retain successful modality positives and negatives for assertions, uncertain plans, hypotheticals and unaccepted advice alongside their failed subject checks. Only the supported modality clarification was retained; the failed subject variants were superseded by the Luna identity role.
- `recorded/result.json`: the full long recording passed semantic chunking, same-person correction, original citations, no account-owner inference and unchanged-source gates. The prior swimming claim became historical and the later tennis claim became active. The successful run made seven new calls; unchanged extraction and boundary responses were reused only by exact request fingerprint. This is provider-backed integration with recorded-response reuse, not a wholly fresh benchmark.
- Local exact-request replay runs the final provider responses through the current planner, writer and SQLite transaction. Additional tests cover lossless coverage, overlap, repeated quote offsets, one long passage, atomic publication, reviewed restart, uncertain paid attempts, source revision/deletion, contract mismatch and queue isolation.

The final backend suite passed **200 tests** with `cd Backend && python3 -m unittest discover`. The broader suite still emits the previously observed unclosed SQLite ResourceWarning; no tests failed. No speech-to-text or physical-device behavior changed; those tests are reserved for the later approved rollout. Model fixtures are synthetic regression evidence, not a general accuracy or latency guarantee.

## Budget and next work

Canonical ledger: **191 provider calls, $1.91 conservatively reserved of the approved $2; $0.09 remains**. Luna: 73 calls/$0.73. Jev: 118 calls/$1.18. Reservations are not verified invoices. This checkpoint required no additional allowance and made no automatic paid retries.

Still pending: semantic duplicate consolidation, richer temporal validity and internal forgetting, semantic retrieval, main companion chat/library integration and approved hosted/physical acceptance. Cross-role identity aliases remain unresolved rather than forced into the current ledger. Long-recording backend success is not a claim that the installed app has received this rework.

Subsequent expiry QA used four more calls; see [current allowance](memory-expiry.md). The $0.09 balance above is historical.
