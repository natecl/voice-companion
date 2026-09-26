# Bounded evidence writer and source-time applicability

Status: bounded backend acceptance passed; not deployed. This is a bounded checkpoint within 3C, not completion of the memory rework. The hosted service still uses the old writer. Long-source chunk integration, duplicate consolidation, relative-date validity/expiry, semantic retrieval, main chat, and physical acceptance remain separate gates.

## Behavior and user experience

A supported statement can be retained without claiming to know whom it belongs to. Independent source support, modality and time checks remain required. Weak subject attribution stores the statement and its original evidence as unresolved, without an account-owner subject, personal-profile link, or invented identity link. A strong independent comparison with an established entity may establish continuity for another person; it does not retroactively establish account ownership or a personal relationship.

A completed change and an ongoing state are different representations of the same possible update. The writer preserves the original wording and extraction metadata. The relationship classifier routes possible replacements to an independent applicability question; its category alone never authorizes a correction. Application requires supported identity and an applicability verdict of at least 0.95 that the source reports a completed replacement as its latest observed state. An explicit future or tentative proposal cannot pass the application guard even if a model returns a positive applicability verdict.

“Current” here means latest supported knowledge at the source observation, not a guarantee that the world remains unchanged today. The stored `valid_from` is that observation boundary, not an invented event date. Historical-only episodes, reversals, future plans and added activities cannot automatically replace an ongoing property. Exact event times, relative dates and expiry remain checkpoint 4 work.

A supported possible replacement that is unresolved retains its target references. Current search, profile derivation and raw-source lifecycle views qualify the older claim as unresolved while that pending evidence remains. The old stored history is unchanged. Deleting a pending source removes its qualification; deleting evidence underlying an accepted correction still reopens the correction chain and never silently restores an old fact as current. These are backend read contracts, not proof of the future companion answer UX.

No new memory approval inbox, forgetting controls or separate capture workflow is introduced.

## Implementation boundary

- `EvidenceWriter` is opt-in and has no hosted startup wiring. Luna proposes evidence and separately resolves identity with low reasoning; Jev independently checks fact support and lifecycle; Python enforces ownership, source revisions, lifecycle and transaction boundaries.
- Independent pair questions use original excerpts, provenance, source times and claims. They exclude Luna's proposed action, predicted kind/scope, entity IDs, database state and earlier judgments. Identity questions additionally retain extracted name/relationship/qualifier descriptors, explicitly subject to the original excerpts; stripping these distinctions caused a blocked false identity proposal in QA. This prevents those hints from substituting for source evidence.
- Schema 8 adds `memory_fact_evidence`, retaining exact proposals and independent judgment diagnostics. Migration performs no model backfill, entity inference or alteration of legacy claims.
- Fact, mention, identity link, correction dependency and job completion commit in one SQLite transaction. Prior-source snapshots are checked before mutation. Source deletion, changed prior evidence or a late identity failure rolls the transaction back.
- Multiple facts and correction chains within one source can reference earlier accepted items in that same transaction. Pending changes within a source also qualify earlier facts.
- Source revision/deletion removes dependent extraction metadata along with existing invalidation behavior. Existing identity/correction revocation remains in force.
- Exact provider-request fingerprints permit replay of unchanged synthetic responses. Paid attempts continue to use the canonical ledger; there are no automatic paid retries.

This writer currently operates on one bounded source. Oversized extraction requests fail explicitly; this module does not silently truncate them or claim that the separate chunk pipeline is integrated. Candidate discovery remains bounded lexical/mention retrieval. Duplicate proposals stay unresolved until consolidation is implemented. These limits prevent rollout of the full rework.

## Verification record

The final local backend suite passed **181 tests**. Local coverage exercises atomic rollback, stale snapshots, source deletion, restart, additive migration, independent attribution, same-name separation, same-source correction chains, event-to-state chains, uncertain current reads, future/historical rejection and exact recorded-provider replay. No speech-to-text calls or physical recording tests are needed for this backend-only change.

Provider evidence is synthetic and bounded. The checked-in fixtures retain both failures and successful iterations:

- Initial generic attribution discarded supported facts; the writer now separates fact retention from verified identity.
- The cat extraction wrapped another subject's property as an author fact. The versioned extraction prompt now centers the subject that actually owns the property; the four subject-centered examples passed.
- The entailment question was treating an omitted relationship detail as a false statement. A focused eight-case positive/negative batch passed the source-entailment contract.
- The original planner correction failed when the independent comparison included extraction action hints and database metadata. Evidence-only comparison passed the focused identity/lifecycle cases and the full planner correction/other-person flow.
- The detergent case exposed both a routed-but-unchecked replacement and an ambiguous meaning of “now.” The final contract uses a separate authorization verdict about latest source-observed knowledge. Earlier failed responses remain in the repository; they are not relabeled as passes.
- A ten-case applicability batch includes valid ongoing changes, historical episodes, reversals, future plans, tentative/hypothetical changes and added activities. The final source-time batch passed all ten cases. The full household flow passed its original correction but failed the strict expectation that the distinct third person becomes an active memory; that fact is preserved unresolved and is not merged with the prior person.

Cases exposed during diagnosis are development/regression evidence, not untouched held-out benchmarks. These checks establish a bounded integration and critical negative behavior, not general model accuracy or probability calibration. Future retrieval and answer acceptance must still verify how these states reach the user.

## Allowance and rollout

The founder explicitly approved an additional $1, bringing this QA allocation to $2. It is provisioned once in the canonical profile ledger, after reserving the corresponding global allowance. The old runtime does not automatically receive the extension. Each reservation is a conservative $0.01 per provider call, not a verified invoice.

No hosted deployment, production schema migration, automatic backfill or public release is included. Render auto-deploy remains off. Physical QA waits for founder readiness at the later rollout checkpoint.

## Identity role decision and final review — September 26, 2026

The founder authorized the recommended identity-role comparison. Luna now resolves source-only identity with **low reasoning**; Jev retains independent source support, subject attribution, modality, time, relation and applicability judgments. Extraction and answer reasoning settings did not change. The identity contract returns same/different/uncertain with exact source quotes, not fabricated confidence probabilities. Quotes establish provenance, not correctness by themselves. Application guards still enforce ownership, source revisions, compatible descriptors and atomic writes.

The failed Jev and Luna variants remain recorded. Jev's compact variant proposed a wrong same-person link at 0.80; restored descriptors produced different at 0.60; a neutral question regressed another case. Luna with reasoning disabled initially passed the household sequence, but a later integration run incorrectly matched “other roommate Tessa.” The descriptor guard prevented that merge and retained the fact unresolved. These runs are failures, not evidence of final acceptance.

Review also found two flawed early comparison oracles: different relationship roles alone do not establish different people, and a passage mentioning a sister and her same-named friend needs a specified target claim. The v2 oracle review is preserved. The low-reasoning 18-case screen failed one missing-target case. The final input contract rejects missing target claims before inference; it does not guess whom a multi-person passage concerns. The final 16-case fixture supplies explicit targets, preserving its same/different/uncertain expectations. Missing-target rejection is covered separately without a paid call.

Final evidence:

- `fixtures/memory_identity_model/targeted/result.json`: all 16 source-only identity cases passed with low reasoning. Cases cover corrections, same-name distinct people, names alone, anonymous speakers, role overlap and quoted subject selection.
- `fixtures/memory_evidence_writer/luna-low-household/`: original memory, correction and distinct same-name roommate all passed. The old claim is historical, the correction uses the same entity, and the distinct person has a separate active entity.
- `fixtures/memory_evidence_writer/luna-low-routine/`: equivalent three-step planner scenario passed. Both writer runs each made two fresh identity calls; unchanged extraction and Jev responses were replayed only on exact request matches.
- `python3 -m unittest discover` from `Backend`: **181 passed**, including exact final provider-request replay through storage, missing-target rejection, bounded request splitting, malformed/unsupported quotes, rollback and deletion. Python emitted an unclosed SQLite ResourceWarning during the broader suite; no test failed. No new speech-to-text or physical-device claims are made.

The final paid gates ran in isolated synthetic stores on Render, using code under `/tmp/memory-identity-luna-v6/Backend`; production code and database were not changed. Local final replay also covers the subsequently corrected identity request-size batching code. These exposed examples are regression/integration evidence, not a held-out benchmark or guarantee of general accuracy.

Cross-role identity aliases are not yet represented by the ledger: a differing descriptor retains the new fact unresolved rather than failing the source or bypassing the guard. Long-source chunk integration, consolidation and later rework checkpoints remain pending. This checkpoint is the bounded writer only.

Canonical ledger after these gates: **156 calls, $1.56 conservatively reserved; $0.44 remains of the approved $2** (Luna 58 calls/$0.58; Jev 98 calls/$0.98). Reservations are not invoices. There were no automatic retries or extra allowances.
