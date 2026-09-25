# Automatic personal profile learning

Checkpoint 2: actual Luna extraction → independent Jev source/identity verification → persisted profile claims, with automatic corrections. Enabled only by an explicit store/runtime setting; hosted rollout and full iPhone recall remain pending.

## Contract

Personal sources use a separate versioned prompt/schema; existing recorded-source extraction remains unchanged. The personal schema distinguishes the user, an explicitly related person/pet, other named subjects, and unknown identity. Application provenance establishes authorship separately from passage text; quotations and other people's preferences remain attributed to their subjects. Jev independently checks source support before judging scope, relation, modality and lifecycle. Probability/confidence thresholds remain 0.90/0.60; no Luna-verifies-Luna fallback.

Related people begin source-scoped to avoid name-based identity merges. Only a Jev-verified explicit correction of a prior fact about the same related person can adopt the prior subject identity. Matching names or relationship labels alone cannot deduplicate across sources. This may retain redundant related-person facts; general entity resolution remains deliberately limited. Ambiguous identities are not forced into the profile.

User preferences, background, goals and relationships share the existing store/lifecycle. A reported medical recommendation remains reported information; tentative plans retain their modality. Profile statements are source-backed reports, not independently verified truths about the world.

`VOICE_ENABLE_PERSONAL_LEARNING=1` requires memory learning and the separately provisioned profile QA allocation. It selects the new bounded allocation for memory operations during the internal QA window. Do not enable it for unbounded general use. New personal sources can enqueue learning only when enabled; previously held sources are not automatically backfilled. Cross-session personal recall remains held until checkpoint 3.

## Provider evidence — September 25, 2026

All 11 designated scenarios passed their live gates:
- Four development: biology/drawing interests; daughter and own preference; preference correction; quoted hypothetical exclusion.
- Four held-out: sport/pet appointment; teaching/family/tentative hobby; ambiguous same-name exclusion; unidentified recorded speaker kept unidentified.
- Three focused extensions using a copy of saved development state: daughter's corrected interest supersedes old fact; different friend with the same name stays separate; reported appointment advice preserves lack of commitment.

Separately, one real Jev batch rejected two deliberately incorrect user attributions (daughter's hobby and quoted friend's profession) and accepted the two supported alternatives. Actual stored claims and qualifications were inspected. Bounded corpus evidence is not a general accuracy guarantee. Ambiguous same-name input yielded no retained facts, favoring abstention; richer ambiguous-entity recall remains a limitation.

Evidence: ignored `work/profile-live-development-v1.log`, `profile-live-heldout-v1.log`, `profile-live-extension-v1.log`, `profile-support-probe.log`, and `work/profile-qa-evidence/`. Synthetic response fixture `Fixtures/personal-support-provider-response.json` preserves the four support decisions. No real personal content was submitted by these tests. Final review added local lexical prioritization of older correction targets within the bounded profile pool; its focused regression passes. Provider prompts and the targets used in the live correction cases remain unchanged.

Local checks: 44 existing memory tests, six profile contract/writer/budget checks, and six hosted startup/transport checks passed. These include actual local store writes and corrections, identity refusal, legacy guards and an aggregate-budget exhaustion test. The native checkpoint 1 evidence remains applicable: this checkpoint changes backend learning, not capture or UI.

## Accounting

Founder-approved ceiling: additional $1, ID `personal-profile-qa-2026-09-25-100`. Provisioned once in the hosted global ledger as a reserved QA allocation; the sub-ledger is in the existing canonical `/var/data/voice-companion/memory-budget.sqlite`. Prior memory allocation and spending remain intact. No local copy of this ledger may be used to authorize calls.

30 live calls so far: 11 Luna, 19 Jev. Conservative reservation $0.01/call, total $0.30; $0.70 remains. These are conservative accounting amounts, not verified invoices. Provider usage payloads are retained. The allocation covers checkpoint 3 retrieval and answers too; no automatic retries or increases. The evaluator refuses existing run directories and stops on failed acceptance. Actual hosted service code/configuration has not been changed.

Current official contracts checked: [Luna model](https://developers.openai.com/api/docs/models/gpt-6-luna) and [TypeSafe API](https://docs.typesafe.ai/api). Preserve Standard/default Luna, reasoning none, structured output and no SDK retries. Jev remains `jev-1.13.0`; vendor retry advice does not override the project's deliberate paid-retry rule.
