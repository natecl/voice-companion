# An invited third person at the table

Founder direction, September 29, 2026. This supersedes note-taking-led positioning; it does not claim these behaviors are all implemented. The product is an invited AI social presence that remembers relevant shared history, follows a conversation and contributes with judgment. Notes remain useful infrastructure and a record. The exact existing one-liner is retained pending a separately chosen replacement; it does not constrain this revised experience.

## What the user comes for

“Bring someone who remembers” is proposed consumer copy, not a finalized name or tagline. The central loop is invite → listen → contribute when useful → follow the response → return with continuity. A familiar, candid friend is the intended feeling; the app remains transparently AI, with fallible memory and no claim of human experience or knowing everything.

The user should stay present with the other people. Starting is deliberate; listening and Quiet/Stop state are legible at a glance. A contribution arrives as ordinary messages in the existing main chat. It can connect a prior priority to a present decision, raise a tradeoff, or ask an overlooked question. A recap of what everyone just heard is not enough to establish this experience. Silence is a successful outcome when there is nothing worth adding.

## First experience slice

Proposed test setting: a student and a trusted friend or study partner making a recurring project decision. Students remain the reachable pilot cohort; this is a test setting, not a permanent restriction on the product or a claim that the wedge is validated.

1. Earlier, the user deliberately shared that keeping evenings free matters and that a small project would help them follow through. Store those statements with subject, time, source and uncertainty.
2. In a later invited discussion, the pair considers a larger project requiring evening meetings. Without a typed request, the companion makes the relevant tradeoff visible: “Would the smaller version fit better with keeping your evenings free?” This is an illustrative target, never a hardcoded demo answer.
3. The user says that this week's schedule is different. The companion accepts the correction, does not repeat the old concern, and can answer a follow-up grounded in the update. A temporary exception must not silently erase a lasting preference.
4. The conversation moves to an unrelated topic containing similar words. It stays quiet. Quiet and Stop prevent delayed contributions while preserving the correct capture/chat state.
5. Later, the user reopens the conversation and sees the same messages and usable notes. The product reward was the contribution, not generating the document.

Use explicit fictional histories and non-sensitive facts in the demo. Do not infer who is in the room from speaker numbers. Contributions stay on the owner's screen; spoken/public output and automatic sharing are outside this slice. A future shared-room output mode requires an explicit audience/visibility contract before it can expose private history.

## “Read the room” as observable behavior

| Situation | Expected participation | Failure to catch |
| --- | --- | --- |
| Earlier preference changes the live choice | Brief, specific connection or useful question | Reciting an unrelated remembered fact |
| Same words, different intent/topic | Silence | The known club-budget/constellation false positive |
| People already resolved the issue | Silence | Reopening a finished decision |
| User corrects or disagrees | Reflect the update; qualify conflicting memory | Arguing from old notes or repeating the reminder |
| Discussion is exploratory | Offer a possibility when useful | Presenting tentative ideas as commitments |
| Topic changes while a response is pending | Drop or revalidate the stale response | Late contribution to an abandoned topic |
| No reliable personal context yet | Use the current discussion only, or stay quiet | Fabricated familiarity or invented biography |
| Quiet or Stop | No unsolicited delivery after cancellation | Late or duplicate bubbles |

Text/transcript context can support topic and turn-level judgments; it does not establish emotion, relationships or room awareness from unseen cues. Evaluate usefulness, timing, novelty, grounding and conversational form separately. No minimum number of interjections is a success metric.

## Personal knowledge graph: capability before infrastructure

Use the existing provenance, identity, relationships, observations, corrections and temporal store as the starting representation. Connect people, preferences, goals, experiences and commitments only when supported by source evidence. A graph here means linked personal knowledge; it does not require a new graph database, graph visualization, embeddings rewrite or a separate omniscient profile service.

First prove these observable paths: a supported preference survives reopen; a third-party preference is not assigned to the owner; a correction or temporary exception reaches retrieval; conflicting or uncertain information stays qualified; ordinary note deletion and explicit erasure remain distinct. Audit existing schema and reads before adding fields. A gap justifies the smallest migration only when a test requires it. Preserve failed migration/retention tests as blockers for affected claims.

## Experience and implementation boundaries

- Invitation reuses deliberate capture and the existing proactive opt-in/control path. Copy such as “Invite into this conversation” is a UI hypothesis to inspect, not permission to change capture semantics or pretend capture is off.
- Founder subsequently requested a non-traditional, personable interface instead of the note-taker/dictation-led shell. Explore a new home/live-conversation layout in the prototype phase below. Preserve input, persistence and control contracts while evaluating the shell; existing message typography and readability are a baseline, not a prohibition on the newly requested redesign. Voice replies remain outside this slice.
- Notes, cache, recording reliability, auth and recovery remain necessary because continuity depends on them. They support the experience rather than define its consumer pitch.
- Keep participation timing/eligibility and message composition independently inspectable. Start from the selected working pipeline; model allocation is an implementation hypothesis, not a decision to enable experimental Jev routes.
- Contributions may span ordinary bite-sized messages with useful content preserved, one durable contribution and one notification/cooldown. Do not simulate separate messages only with paragraph breaks or shrink the type to fit.
- Calendar/email/messages and fresh outside sources remain fuller-vision work. No connector, always-on recording, or additional account access follows from this revision.

## Evidence and learning

A model worker submits the exact prior context, current-turn sequence, expected contribute/silence rationale, actual decision/messages, latency, request/configuration fingerprint, budget receipt and persisted/delivered result. Fictional outputs can be retained; real participant content needs an explicit retention choice. Local replay verifies mechanics; fresh approved provider execution verifies changed judgment and wording. Simulator evidence establishes visual/state behavior; physical audio claims still need the physical path.

For the pilot, ask whether a contribution changed the discussion, felt well timed, was awkward or irrelevant, and whether people choose to invite the companion again. Record missed opportunities as well as interruptions. Repeat invitation is the proposed leading product signal; no retention rate or engagement threshold is established yet. Note count and recording minutes alone do not establish success.

See the [execution phases](execution/demo-testflight-phases.md), [feature contexts](features/context-map.md) and [verification contracts](features/verification-map.md). The founder approved incorporating this vision into the plan; the packets, demo and copy above are implementation proposals to verify, not completed features.

## Proposed interface: a place to meet

Design hypothesis: create a calm shared space with a recognizable abstract presence, rather than a document dashboard or a generic glowing AI orb. Use a small paired-shape mark with a consistent silhouette, warm neutral surfaces, generous space, human-scale typography and one restrained accent. Its character comes from how it waits and responds; a face, mascot, simulated emotion or elaborate 3D scene is not required. Test distinctiveness and legibility in the prototype instead of claiming this direction is validated.

### Arrival — before listening

The center of the screen holds the companion's quiet presence and an honest “Not listening” state. A thumb-reachable primary action says “Invite into a conversation” (proposed copy). A smaller “Talk with me” entry reveals the familiar text/dictation composer for private direct chat. A returning-user continuity line appears only if supported and appropriate; first use explains what inviting does instead of inventing familiarity. No task list, document icons or constantly open dictation toolbar dominates arrival.

History and account/search remain reachable through plainly labeled secondary controls. History opens a sheet or page of past conversations with their notes/transcripts, preserving swipe/hold actions. Avoid hiding essential navigation behind an unlabelled gesture. The person should feel they are bringing someone along, not starting a paperwork workflow.

### At the table — invited and listening

The presence becomes smaller and makes space for contributions. A stable, readable Listening indicator and elapsed time confirm real microphone capture. Quiet and End are always visible within thumb reach, without an overflow menu. Quiet suppresses proactive messages while recording continues; End stops capture and pending unsolicited delivery. Network loss or an interruption changes both the label and available recovery action; animation never implies listening when capture has stopped.

Messages enter this same space, not a separate insights panel. Existing conversation remains accessible; the newest contribution can be read without opening Notes. A “Reply” affordance opens the composer without ending the session. Live transcript is a secondary, clearly labeled view. This design does not add automatic TTS, mirrored public output or assume everyone can see the owner's screen.

### Speaking with the companion

When the user opens direct chat, the familiar one-line expanding composer appears with upright paperclip, dictation mic/arrow behavior and existing attachment semantics. It can tuck away when returning attention to the room, but never discard a draft; preserve a visible draft/resume affordance. New messages must not cover Quiet/End or force-scroll someone reading history. Dictation's existing capture pause/resume explanation stays legible.

### Leaving and returning

Ending returns to a calm resting state with a simple saved/saving/failure result and a route to the conversation. Summary generation can finish in the background; no congratulatory notes checklist or invented relational farewell is necessary. Next visit restores continuity and makes another invitation obvious. The archive remains available, including cached notes offline; the app must not imply active listening merely because prior history is open.

### Motion, touch and feedback

Use a small family of state transitions: presence settles when invited, an understated transition reveals a contribution, controls compress/release on touch, and history rises into view. A restrained acknowledgment haptic can mark a successful deliberate action; do not buzz continuously while listening or for every stream token. Respect reduced motion, Dynamic Type, screen readers and device/user haptic settings. All tappable targets remain comfortably sized; distinguish states with labels as well as color or movement.

Libraries.dev thinking/voice examples are reference material for genuine processing/audio states. The native app is SwiftUI: do not install React effect packages or a WebView to reproduce a decorative effect. Use native state-driven transitions, pause rendering when hidden and measure responsiveness/battery impact. Do not animate a fake audio waveform when no audio level is available.

### Prototype gate before replacing the app shell

Build one isolated clickable prototype covering arrival, listening, contribution, reply/keyboard, Quiet, End, history, empty first use, offline/interruption and large-text/reduced-motion states. Compare against the existing app at a real phone viewport. The founder reviews the concrete visual direction; agents inspect usability/state contracts. Then implement the selected shell in a separate bounded native packet. Do not replace working capture/chat while the visual proposal is still unreviewed.

The UI worker must answer: can a first-time user tell whether it is listening, invite it deliberately, read its contribution, reply, stop it and find a past conversation? Does it create a personable sense of continuity without pretending to have feelings or unsupported knowledge? This is the visual gate, separate from whether the model's contribution is useful.

## Reference research before UI-1

Founder-selected sources: [Refero iOS](https://refero.design/ios-apps) and [Mobbin iOS](https://mobbin.com/discover/apps/ios/latest), with Libraries.dev for applicable motion references. Examine complete journeys, not isolated attractive screenshots. Start with social/chat presence, welcoming home/empty states, live audio-session controls, transitions into history and graceful interruptions. Do not limit research to note-taking apps or copy a competitor's full shell.

For each selected reference, record app, exact screen/flow URL, observed behavior, the specific pattern to borrow, what not to borrow, and how it supports invitation/presence/control. Assemble a small annotated reference set before choosing typography, spatial hierarchy and motion. Compare coherent visual directions rather than averaging unrelated apps into a generic interface. The proposed paired-shape presence and warm palette above remain hypotheses until this research/prototype review.

Access inspection on September 29: Mobbin's supplied discovery URL redirected to a public landing page in the current browser session; no private app flows were inspected. Refero's official MCP page documents Pro-plan access and account authorization. No Refero tool is connected in this session; plugin-directory search returned no match. Do not claim research on authenticated screens or silently purchase access. Official setup is at https://refero.design/mcp, with endpoint https://api.refero.design/mcp. Research access is a UI-1 prerequisite if its packet requires these private references, not a reason to mark unseen screens reviewed. This planning checkpoint adds the research method without claiming a completed reference study.
