# Companion chat and follow-ups

> September 30 delivery context: [release handoff](../../execution/testflight-release-handoff.md). This map distinguishes source implementation from recorded deployment, installation and bounded verification; historical receipts do not attest current runtime state.

Feature ID: `chat` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Persistent chat, attachments, streaming and durable recovery. Product direction is an invited AI social presence with personal continuity; the retained agreed one-liner is **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

One persistent main chat supports questions during and between captures. Agent is the main screen; Notes is secondary. Normal chat, drafts, attachments and durable turn recovery exist.

The local PR171 candidate reauthorizes companion content on already-open sockets after session revocation. Four regressions reproduced stale-session disclosure; 38 targeted account/companion checks passed independent review using real loopback sockets and fictional data. [Evidence](../../qa/account-isolation-review/README.md). This backend fix is not deployed in recorded `208ca34`.

## Gaps and non-goals

No side chats, autonomous work actions, or spoken replies. Semantic quality cannot be established by socket fixtures. Installed/native and deployed/backend versions must be checked separately.

## Flow and implementation entry points

Composer + optional attached/live snapshot + history → qualified past context → answer generation → durable turn → streamed/reopened bubbles.

- [Backend/companion_service.py](../../../Backend/companion_service.py)
- [App/Sessions/CompanionController.swift](../../../App/Sessions/CompanionController.swift)
- [UITests/CompanionUITests.swift](../../../UITests/CompanionUITests.swift)

## Contracts and dependencies

Ordinary note deletion preserves sent replies. Keep existing bubble UI, upright paperclip, single-row expanding composer and mic-to-arrow switch. Capture and answer lifecycles are independent; uncertain delivery must not cause blind paid retries.

**Uses:** [Past-context retrieval](recall.md), [Recording library and sync](library.md), [Tester access and account controls](access.md)

**Consumers / coordinated work:** [Composer dictation](dictation.md), [Proactive contributions](proactive.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: implemented foundations; fresh feature verification required.
- [Feature verifier contract](../verification/chat.json): `python3 scripts/verify_feature.py chat`.
- [Mechanical baseline and unresolved checks](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Actual answer/follow-up pipeline with final model configuration; Streaming, draft preservation, attachment, failed delivery and reopen.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

The approved shared companion-room UI is merged through PR154–155. Preserve its design and interactions while completing Phase 1 account lifecycle; do not restart shell prototyping. See [shared room](shared-room.md).

Verify follow-up, failed delivery/draft preservation, streaming and reopen through the active socket path; inspect actual model output only when model/context behavior changes.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [companion-chat-store.md](../../companion-chat-store.md)
- [companion-internal-rollout.md](../../companion-internal-rollout.md)
- [native-experience-ui.md](../../native-experience-ui.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.

## Historical native presentation candidate — September 29

Founder approved replacing the native shell with the reviewed lavender/plum prototype. See [bounded implementation and QA](../../qa/companion-room/README.md). Two-line Notes entry and Invite replace root tabs/search; the existing chat/controllers remain. Temporary reference art is debug-only presentation (still bundled; remove before distribution). Invitation delivery is not implemented. This historical candidate predates the merged shared-room baseline; use [shared room](shared-room.md) for current presentation wiring.
