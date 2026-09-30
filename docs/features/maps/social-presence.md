# Invited social presence and interface

> September 30 delivery context: [release handoff](../../execution/testflight-release-handoff.md). This map distinguishes source implementation from recorded deployment, installation and bounded verification; historical receipts do not attest current runtime state.

Feature ID: `social-presence` · Reviewed September 30, 2026 at `7079427`; UI/integration PR154–155 are merged.

## Purpose and user outcome

Invite a third intelligent participant that brings relevant personal continuity and perspective into a conversation. [Canonical revision](../../product-source-of-truth.md#invited-social-presence--september-29-2026) governs; [experience and UI brief](../../social-presence-experience.md) translates it into proposals.

## Current implementation

Capture, persistent chat, notes, memory and gated proactive delivery are existing foundations. The founder-approved companion-room shell is implemented as bundled HTML/CSS/JavaScript in WKWebView with native controllers; see [shared room](shared-room.md). The “personal knowledge graph” starts with the existing linked evidence/identity/lifecycle representation.

## Gaps and non-goals

Prototype review and shared native state wiring have bounded evidence. Remaining acceptance includes physical keyboard/accessibility/motion, integrated contribution/correction/silence and a truthful demo. Friend invitations and final mascot remain unfinished. No new graph database, simulated emotion, voice replies, always-on capture or public disclosure of private memories in this slice.

## Flow and implementation entry points

Arrival → explicit invitation → listening with Quiet/End → ordinary contribution → reply/correction → finish → reopen/history.

- [Shared presentation](../../../App/RoomUI/room.js)
- [Native bridge/model](../../../App/RoomWebModel.swift)
- [Native fallback](../../../App/CompanionRootView.swift)
- [Current styles](../../../App/ExperienceStyle.swift)
- [Detailed UI state proposal](../../social-presence-experience.md#proposed-interface-a-place-to-meet)

## Contracts and dependencies

Uses [capture](capture.md), [chat](chat.md), [proactive](proactive.md), [identity](identity.md), [recall](recall.md) and [note cache](note-cache.md). Consumers include [distribution](distribution.md). Invitation deliberately starts the intended recording/participation state; Quiet suppresses contributions while capture continues; End ends capture and pending unsolicited delivery. Preserve draft and single-main-chat behavior. Messages remain private on the owner's screen.

Shared shell/controller files have one owner. Preserve the approved shared interface; preview simulations must remain isolated from the production bridge. Appearance never substitutes for accurate permission/capture state.

## Verification and delivery state

Run `python3 scripts/verify_feature.py social-presence` using the [contract](../verification/social-presence.json). Shared-room pipeline, bundle and focused layout/motion verifiers exist; consult [shared UI evidence](../../shared-room-ui.md) for their exact synthetic/native scope. A missing acceptance receipt remains incomplete. Prototype inspection cannot satisfy native acceptance. Contribution quality also requires the proactive verifier and approved actual model pipeline evidence. This documentation audit changes no deployed backend or installed app.

## Next bounded work

Complete Phase 1 account/data-lifecycle acceptance behind the approved UI. Preserve separate physical presentation and participation-quality gates; the merged shell does not prove useful unsolicited judgment. Use the [phase plan](../../execution/demo-testflight-phases.md) for ownership/dependency gates.

## Maintenance

Workers submit implementation, gaps and evidence deltas to the orchestrator. Update this map and the linked verifier as each prototype/native/model checkpoint is accepted. Do not call the product verified from mockups or scripts alone.
