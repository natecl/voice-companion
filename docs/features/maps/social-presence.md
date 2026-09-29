# Invited social presence and interface

Feature ID: `social-presence` · Planned September 29, 2026; baseline main `cdd17dc`.

## Purpose and user outcome

Invite a third intelligent participant that brings relevant personal continuity and perspective into a conversation. [Canonical revision](../../product-source-of-truth.md#invited-social-presence--september-29-2026) governs; [experience and UI brief](../../social-presence-experience.md) translates it into proposals.

## Current implementation

Capture, persistent chat, notes, memory and gated proactive delivery are existing foundations. The new social-presence shell is not implemented or visually approved. The “personal knowledge graph” starts with the existing linked evidence/identity/lifecycle representation.

## Gaps and non-goals

Need an isolated clickable prototype, concrete visual review, native state wiring, contribution/correction/silence acceptance and an integrated demo. No new graph database, simulated emotion, voice replies, always-on capture or public disclosure of private memories in this slice.

## Flow and implementation entry points

Arrival → explicit invitation → listening with Quiet/End → ordinary contribution → reply/correction → finish → reopen/history.

- [Current native shell](../../../App/CompanionRootView.swift)
- [Current styles](../../../App/ExperienceStyle.swift)
- [Detailed UI state proposal](../../social-presence-experience.md#proposed-interface-a-place-to-meet)

## Contracts and dependencies

Uses [capture](capture.md), [chat](chat.md), [proactive](proactive.md), [identity](identity.md), [recall](recall.md) and [note cache](note-cache.md). Consumers include [distribution](distribution.md). Invitation deliberately starts the intended recording/participation state; Quiet suppresses contributions while capture continues; End ends capture and pending unsolicited delivery. Preserve draft and single-main-chat behavior. Messages remain private on the owner's screen.

Shared shell/controller files have one owner. Prototype work must remain isolated from production runtime changes. Appearance never substitutes for accurate permission/capture state.

## Verification and delivery state

Run `python3 scripts/verify_feature.py social-presence` using the [contract](../verification/social-presence.json). No automated suite is implemented for the new shell yet; its mechanical receipt remains a required gap. Prototype inspection cannot satisfy native acceptance. Contribution quality also requires the proactive verifier and approved actual model pipeline evidence. This plan changes no deployed backend or installed app.

## Next bounded work

After baseline/contracts, UI-1 creates a clickable phone-sized flow including keyboard, large text, reduced motion and failure states for review. UI-2 implements the selected design only after that review; LLM-1 handles participation quality independently. Use the [phase plan](../../execution/demo-testflight-phases.md) for ownership/dependency gates.

## Maintenance

Workers submit implementation, gaps and evidence deltas to the orchestrator. Update this map and the linked verifier as each prototype/native/model checkpoint is accepted. Do not call the product verified from mockups or scripts alone.
