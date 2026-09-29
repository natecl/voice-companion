# Proactive contributions

Feature ID: `proactive` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Useful unsolicited context with Quiet, budgets and stale-result rejection. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

Gated proactive scheduling, Quiet/stop, budget controls and durable delivery exist. Bounded model screens and phone experiments are recorded; useful timing was reported in the Cedar test. Multiple texts represent one contribution with one cooldown.

## Gaps and non-goals

Broader relevance is unresolved: same-topic but irrelevant reminders remain a known risk. Experimental Jev decision/writer and wording branches are not automatically selected. No claim of public-release activation or always-on listening.

## Flow and implementation entry points

Finalized live text → bounded scheduling/context retrieval → contribute-or-silence decision → validated ordered messages → durable main-chat delivery.

- [Backend/proactive_service.py](../../../Backend/proactive_service.py)
- [Backend/proactive_policy.py](../../../Backend/proactive_policy.py)
- [UITests/ProactiveUITests.swift](../../../UITests/ProactiveUITests.swift)

## Contracts and dependencies

Keep ordinary message styling; preserve useful details in conversational messages. Quiet/stop, stale results and duplicate delivery must be enforced independently of model prose. Relevant memory retrieval does not itself justify interruption.

**Uses:** [Capture and live transcript](capture.md), [Past-context retrieval](recall.md), [Companion chat and follow-ups](chat.md), [Tester access and account controls](access.md)

**Consumers / coordinated work:** [TestFlight install and update](distribution.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: implemented foundations; fresh feature verification required.
- [Feature verifier contract](../verification/proactive.json): `python3 scripts/verify_feature.py proactive`.
- [Mechanical baseline and unresolved checks](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Active decision → output → storage/delivery; relevant, resolved and same-topic-irrelevant cases; Actual bubbles, Quiet/stop, no stale/duplicate deliveries in intended configuration.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

The [social-presence revision](../../social-presence-experience.md) changes acceptance from a correct reminder alone to useful participation, silence, corrections and conversational follow-through. Follow LLM-1/PROACTIVE-1 in the revised phases; model experiments remain unselected until verified.

Prioritize bounded controls and one truthful demo over endless wording loops. Inspect selected prompt/runtime flags and test relevant, resolved and irrelevant cases with explicit paid allowance.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [proactive-contributions-plan.md](../../proactive-contributions-plan.md)
- [proactive-conversation-validation.md](../../proactive-conversation-validation.md)
- [execution/demo-testflight-phases.md](../../execution/demo-testflight-phases.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
