# Independent source verification — candidate, not deployed

Founder direction: keep our memory backend and address its verification rejection. The gbrain comparison is closed as an adoption decision for now. Ordinary recording deletion retaining memory remains a separately approved, unimplemented contract change; this slice does not mix deletion changes into verifier QA.

## Diagnosed failure and smallest candidate

For the saved Juniper recording, the deployed verifier returns supported probabilities of 0.66 for fact support, 0.77 for stated modality and 0.56 for current-as-reported time. All fall below the unchanged 0.90 gates. The extractor correctly proposes the preference. Lowering one threshold or changing storage does not resolve this failure safely.

The previously paid atomic Jev screen classifies the same fragment as stated at 0.99 and current at 1.0, while factual entailment remains 0.77. A separate previously approved Sol low-reasoning screen passed 17 factual-support cases. This is supporting evidence for separating the tasks, not proof the new composed writer is correct.

The candidate flag `independent_source_verification=False` remains off by default and has no hosted wiring:

1. Luna extracts proposals and original evidence as before.
2. GPT-6 Sol low independently judges the claim from original passages and returns supported/contradicted/uncertain plus original passage IDs. No self-reported probability is invented. Supported citations must be nonempty and present in the proposal's persisted evidence. Extra context cannot silently become uncited support.
3. Jev separately classifies stated/tentative/hypothetical/absent and source-reported temporal status. Application code compares these with the proposal at the existing 0.90 gates. Explicit temporal expressions retain the old independent expression check. A genuinely uncertain temporal representation remains unresolved rather than being promoted to current.
4. Existing recording identity, pairwise identity, correction/applicability, expiry and atomic storage rules remain unchanged. Personal-text and non-Luna-identity paths retain the existing verifier.

The flag is scoped to unidentified recordings with the existing recording identity path. It is not a fallback after a Jev rejection or repeated model voting. A supported Sol verdict never bypasses other gates. New cached stages have versioned request identities; completed chunk results from another verification contract are rejected, not silently reused. No old failed job or completed source is automatically reprocessed.

## Evidence and remaining gate

Offline checks compare the new support request with the previously paid 17-case screen, preserve the original failed deployed replay, and run the actual SQLite writer through supported/contradicted/uncertain outcomes, restart and stale-source rejection. Integration tests inject verifier outcomes deliberately: they prove application behavior, **not** fresh model accuracy. Metadata unit tests reuse saved response fields only as parser/policy inputs; removing the support question changes the provider request and needs fresh validation.

No new provider calls have been made for this fix. The earlier $0.50 approval was scoped to gbrain; its unused balance is not silently repurposed.

Proposed paid gate, requiring approval: up to **$0.25** within the existing $5 global cap. Use exact saved extraction/identity responses only where requests match; run fresh Sol support and Jev metadata on original/correction inputs, exercise their actual writer path, and screen a frozen independent set of positive and negative cases. Retaining the preference changes later identity/relation calls, so those changed requests require real evidence too. Reserve each request, enforce the total, make no automatic retries, stop on a substantive failure, and save responses for offline replay. Do not repeatedly tune to Juniper.

Gate must show: preference retained; existing location correction remains valid; negation, competing subjects, quotation and future-as-current errors do not become active false memories; uncertain identity does not become account ownership; exact citations remain supported. Review ambiguous labels before the paid run. Source revision/deletion race checks stay required, independently of the future recording-retention feature.

Do not merge this candidate as a completed fix or deploy it until the provider-backed composition and applicable budget integration pass. Existing runtime budgets do not yet admit Sol in the hosted learning path. Rollout and deliberate recovery of missed sources require a subsequent reviewed step; no automatic backfill.

The new six-case QA input is frozen before live inference in `Backend/fixtures/source-verification/qa-cases.json`: named-family/student positives, negation, unsupported account ownership, quoted-person attribution and future metadata. `expected_support` and `expected_admission` are deliberately separate: a true future claim with proposed current metadata must fail admission. These are synthetic development gates, not a population benchmark. All speakers in these cases are anonymous; “my sister” does not establish an account-owner relationship.

Local validation: 43 targeted tests passed across source verification, saved Sol screen, original subject-continuity failure, atomic classifier evidence, writer transactions and chunk behavior. The historical restored screen tests emitted SQLite ResourceWarnings; their connection lifetime was corrected and those three tests rerun successfully. `git diff --check` passed. These results do not satisfy the still-pending live composition gate.
