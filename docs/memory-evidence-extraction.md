# Memory rework checkpoint 3A — evidence extraction contract

`memory_evidence` supplies the versioned Luna extraction proposal contract for the reworked writer. It preserves subject scope, relationship/qualifiers, source narrator label, stated/tentative basis, temporal expression/status, and possible addition/correction. Exact quoted excerpts become locally calculated character spans after validation. A fabricated or non-unique excerpt fails; no guessed offsets enter storage.

Recording provenance cannot establish the account owner. Personal text establishes authorship but not that every fact concerns its author. Speaker labels describe evidence provenance, not biometric identity. Empty qualifiers means checked with none extracted; old null qualifiers remain unknown. The prompt addresses everyday relationships, study, work, appointments and interests without privileging a professional profile.

This module does not write memories, resolve cross-source identity, calculate temporal validity or change the running writer. Independent Jev judgments and application-owned transitions are the next integration gates. Schema conformance and exact excerpts do not prove semantic correctness.

## QA evidence

Development Mac Python 3.13, plus isolated synthetic QA on Render using the existing Luna adapter. Production database and deployment unchanged. Eleven local tests exercise parsing, source offsets, ambiguous/invalid excerpts, speaker provenance, field bounds, owner-attribution restrictions, recorded failure, recorded positive cases, and preservation of the legacy request contract.

```sh
python3 -m unittest discover -s Backend -p test_memory_evidence.py -v
```

Frozen extraction cases: explicit daughter preference correction, other same-name daughter, unidentified recorded first-person speaker, and a fresh historical relative/work fact. The full writer held-out gate remains pending; these are extraction checks, not proof of correct memory transitions.

Initial v2 response faithfully described the daughter but incorrectly set scope=author. Parser rejected it before any write. Preserved in `fixtures/memory_evidence/failed/ambiguous-scope.json`. The revised v2.1 prompt defines scope as the subject of the fact, not its source's authorship. All four final-contract cases passed, with original exact excerpts intact.

One oracle correction is explicit: the distinct daughter case originally required change=none. The recorded model response used addition while preserving the distinct-person qualifier. Both none and addition satisfy the actual acceptance requirement; correction does not. The test now accepts those two values. No model rerun was made for this oracle change and no false merge/replacement criterion was relaxed. Future lifecycle decisions cannot rely on this extraction label alone.

Five Luna calls total, $0.05 reserved including the rejected first response. Cumulative ledger: 75 calls, $0.75 reserved, $0.25 remaining in the existing $1 allocation. These are reservations, not verified billing. Every call used synthetic inputs; saved requests/responses support free replay. No automatic retries.

The request retains the existing model, reasoning and tier settings. Strict nested object schemas follow [OpenAI structured-output documentation](https://developers.openai.com/api/docs/guides/structured-outputs); independent application validation remains required.
