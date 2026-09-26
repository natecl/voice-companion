# Bounded evidence writer and source-time applicability

Status: draft, unmerged and not deployed. Full writer acceptance is still blocked by an identity-quality miss. This is a bounded checkpoint within 3C, not completion of the memory rework. The hosted service still uses the old writer. Long-source chunk integration, duplicate consolidation, relative-date validity/expiry, semantic retrieval, main chat, and physical acceptance remain separate gates.

## Behavior and user experience

A supported statement can be retained without claiming to know whom it belongs to. Independent source support, modality and time checks remain required. Weak subject attribution stores the statement and its original evidence as unresolved, without an account-owner subject, personal-profile link, or invented identity link. A strong independent comparison with an established entity may establish continuity for another person; it does not retroactively establish account ownership or a personal relationship.

A completed change and an ongoing state are different representations of the same possible update. The writer preserves the original wording and extraction metadata. The relationship classifier routes possible replacements to an independent applicability question; its category alone never authorizes a correction. Application requires supported identity and an applicability verdict of at least 0.95 that the source reports a completed replacement as its latest observed state. An explicit future or tentative proposal cannot pass the application guard even if a model returns a positive applicability verdict.

“Current” here means latest supported knowledge at the source observation, not a guarantee that the world remains unchanged today. The stored `valid_from` is that observation boundary, not an invented event date. Historical-only episodes, reversals, future plans and added activities cannot automatically replace an ongoing property. Exact event times, relative dates and expiry remain checkpoint 4 work.

A supported possible replacement that is unresolved retains its target references. Current search, profile derivation and raw-source lifecycle views qualify the older claim as unresolved while that pending evidence remains. The old stored history is unchanged. Deleting a pending source removes its qualification; deleting evidence underlying an accepted correction still reopens the correction chain and never silently restores an old fact as current. These are backend read contracts, not proof of the future companion answer UX.

No new memory approval inbox, forgetting controls or separate capture workflow is introduced.

## Implementation boundary

- `EvidenceWriter` is opt-in and has no hosted startup wiring. Luna proposes evidence; Jev independently checks it; Python enforces ownership, source revisions, lifecycle and transaction boundaries.
- Independent pair questions use original excerpts, provenance, source times and claims. They exclude Luna's proposed action, predicted kind/scope, entity IDs, database state and earlier judgments. Identity questions additionally retain extracted name/relationship/qualifier descriptors, explicitly subject to the original excerpts; stripping these distinctions caused a blocked false identity proposal in QA. This prevents those hints from substituting for source evidence.
- Schema 8 adds `memory_fact_evidence`, retaining exact proposals and independent judgment diagnostics. Migration performs no model backfill, entity inference or alteration of legacy claims.
- Fact, mention, identity link, correction dependency and job completion commit in one SQLite transaction. Prior-source snapshots are checked before mutation. Source deletion, changed prior evidence or a late identity failure rolls the transaction back.
- Multiple facts and correction chains within one source can reference earlier accepted items in that same transaction. Pending changes within a source also qualify earlier facts.
- Source revision/deletion removes dependent extraction metadata along with existing invalidation behavior. Existing identity/correction revocation remains in force.
- Exact provider-request fingerprints permit replay of unchanged synthetic responses. Paid attempts continue to use the canonical ledger; there are no automatic paid retries.

This writer currently operates on one bounded source. Oversized extraction requests fail explicitly; this module does not silently truncate them or claim that the separate chunk pipeline is integrated. Candidate discovery remains bounded lexical/mention retrieval. Duplicate proposals stay unresolved until consolidation is implemented. These limits prevent rollout of the full rework.

## Verification record

The final local backend suite passed **171 tests**. Local coverage exercises atomic rollback, stale snapshots, source deletion, restart, additive migration, independent attribution, same-name separation, same-source correction chains, event-to-state chains, uncertain current reads, future/historical rejection and exact recorded-provider replay. No speech-to-text calls or physical recording tests are needed for this backend-only change.

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

## Latest review — September 26, 2026

The original detergent correction now applies correctly, with its original event wording, separate identity proof, previous history and source references intact. The planner integration also passed before the later identity contract changes; that earlier run is retained as development evidence, not silently promoted to proof of the final identity variant.

**Remaining blocking acceptance failure:** the third household source says “My other roommate Tessa uses citrus laundry detergent.” Source support and subject metadata passed, but Jev did not confidently distinguish that subject from the earlier Tessa. The model's first compact-input variant proposed the wrong same identity at 0.80, which the guard rejected. Restoring descriptors produced different at 0.60, still an abstention. A neutral question/original-only variant passed this case but regressed the other-person fixture. That experiment was rejected; version v9 remains the candidate. The third fact survives unresolved, the accepted correction is unchanged, and no false merge occurred. The strict positive identity gate is still failed. A local replay asserting this safe failure is a regression test, not a passing replacement for that gate.

Stop prompt iteration on these exposed cases. The next decision is whether to evaluate Luna for source-only identity resolution while retaining Jev's independent fact-support and lifecycle roles. This changes the founder's preferred judgment-role split and is not adopted in this PR. Do not merge this draft as a completed writer or start hosted rollout until the identity gate is resolved.

Canonical ledger after the final failed neutral-question experiment: **140 calls, $1.40 conservatively reserved; $0.60 remains of the approved $2** (Luna 43 calls/$0.43; Jev 97 calls/$0.97). No provider calls were made after that experiment. Replayed calls consume no additional provider allowance; the evaluator records which responses were reused and requires exact request fingerprints.
