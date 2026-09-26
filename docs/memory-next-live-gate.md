# Next live QA gate: independent multi-source questions

Prepared September 26, 2026, after indexed recall PR 54. This is a spending/acceptance plan, not a claim that the next behavior is implemented or approved for deployment.

The current ranker selects one strongest source plus its linked corrections/conflicts. The next change must support a question needing two independent recordings without filling the answer with topical distractors. Keep the existing one-source and no-match evidence as regressions; preserve all original sources and deterministic lifecycle/identity validation.

Freeze these cases before changing ranking semantics:

1. A question about Lena's allergy and Biscuit's medicine must select the two answer-bearing sources, not a general allergy handout or veterinary talk.
2. A question comparing two named people's interests must include both people without merging their identities.
3. A current-versus-earlier preference question must include the linked correction/history with the proper qualification.
4. An unknown first-person recording must not become account-owner biography.
5. A same-name unresolved change must remain unresolved.
6. An unrelated general question must receive no forced personal memory.

Required provider evidence: one bounded Jev role batch covering positive and negative selection, followed by three actual recall-to-Luna cases exercising two independent sources, comparison, and no-match behavior. Maximum initial gate: **7 calls**, reserved at $0.01 each = **$0.07**, no automatic retry. Run recorded/SQLite/socket QA first. If the role gate fails, preserve it and stop that live sequence; do not weaken expectations to continue. Later persistent-chat and physical acceptance have separate frozen gates.

Canonical remote ledger currently reserves **$2.18 of the approved $2.20**, leaving **$0.02**. The full next gate therefore requires a new allowance before paid execution. Request an additional **$0.20** (new total $2.40) to cover this gate and leave room for subsequent explicitly bounded chat checks; no unbounded model loops or bulk historical learning. This document does not provision that allowance or authorize spending beyond the current cap.
