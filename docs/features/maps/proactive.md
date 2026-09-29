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

## PROACTIVE-1 bounded controls checkpoint — September 29, 2026

Base `47eadb4c8be3a46593bb6f17250f4c24335ea02c`; branch `codex/proactive-controls`.
An expired service result was correctly discarded, but its pending policy lease
could block all subsequent additive speech. `observe` now invalidates an expired
lease before scheduling. The original cutoff remains consumed: this does not retry
a failed provider call. New context still obeys interval, cooldown and attempt caps.
Quiet and End remain suppressive after expiry.

Reproduce the original failure by running
`PYTHONPATH=Backend python3 -m unittest Backend.test_proactive_policy.ProactivePolicyTests.test_expired_pending_lease_releases_new_additive_context`
with the five-line expiry guard removed: `next_lease` is unexpectedly `None`.

Verification command (local Python 3.13, macOS 26.6.2 arm64):

```sh
PYTHONPATH=Backend python3 -m unittest Backend.test_proactive_policy Backend.test_proactive_service Backend.test_proactive_socket Backend.test_proactive_stream Backend.test_proactive_phone_qa Backend.test_proactive_conversation
python3 scripts/verify_feature.py proactive
```

The targeted suite passes 44 tests. Actual authenticated loopback WebSockets run
through `ProactiveSocketService` and `ProactiveService`, using deterministic fake
provider responses and isolated SQLite files. Inspected outcomes: expired result
writes no turn; additive speech later delivers exactly one reopened turn; Quiet
and End reject a response even when the provider ignores task cancellation; Quiet
continues accepting live transcript updates without further model calls. This
establishes transcript/control mechanics, not microphone capture. Existing replay
and service checks cover duplicate retries, source-connection deduplication and
cached historical responses. Multi-paragraph text persists as one turn and incurs
one cooldown. Budget denial makes zero provider calls and consumes the cutoff;
local phone-QA ledger tests preserve caps and no-refund/no-retry behavior.

Runtime selection is unchanged: hosted source wires the `llm` default only when
explicit PhoneQA configuration exists; `proactive_models.PROMPT` selects v4 and
`grouped_messages=False`. The selected text schema accepts paragraph-separated
text; the experimental grouped schema/prompt is not enabled. No hosted config or
installed build was inspected or changed by this packet.

The feature verifier's mechanical checks pass; full-feature status remains
**incomplete** for live-provider, simulator and inspection receipts. These tests
are fresh service/control execution with synthetic or historical cached outputs,
not fresh LLM judgment. Paid calls: zero. No UI/device/capture-quality, distribution
activation, deployment or broad relevance claims. The wider targeted run emits
SQLite ResourceWarnings from fixture helpers; checks still pass. Their baseline
frequency was not separately measured; shared storage code is unchanged.
Primary review/merge is pending; this packet does not advance dependent phases.
