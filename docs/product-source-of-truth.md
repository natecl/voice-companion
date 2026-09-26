# Product source of truth

Status: Agreed with the founder on September 24, 2026.

## One-liner

> Granola with an AI that listens alongside you and can join the conversation.

## Proven, Better, New

Use the breakdown discussed by Mark Pincus and Garry Tan in the first source video, as agreed in this product conversation. The framework starts from our accepted paraphrase, not a verbatim quotation. The iPhone-first formulation of New is the founder’s subsequent refinement, not a claim about what the video speakers explicitly prescribed.

- **Proven:** Granola.
- **Better:** Faster responses, lower latency, lower price—the improvements existing users would clearly recognize.
- **New:** An iPhone-first AI companion that listens alongside you in everyday conversations and can join in when you turn to it.

This is the product source of truth. Everyday capture scenarios are applications of this vision, and Jev is a potential way to implement it.

## iPhone-first consumer direction

Explicit founder decision, September 24, 2026: make this a true mobile consumer product, with iPhone use cases leading feature priorities, interaction design, and engineering effort. The Mac app and desktop meeting capabilities remain supported; simultaneous feature parity is not required at every checkpoint.

The intended differentiation is the everyday companion experience and its usefulness with captured personal context, not merely having an iPhone app. Conversations with friends, lectures, and appointments such as a vet visit are central use cases alongside meetings. The phone makes the companion accessible throughout the day. Whether this experience creates a durable consumer habit remains a hypothesis to validate.

“Always-on” remains the long-term listening-companion vision. The practical starting experience is deliberate capture: start listening, put the phone away, stay present, then revisit or ask about the conversation. This decision does not authorize silent continuous recording, presume the AI knows everything about the user, or claim that locked-screen/background recording already exists in V0. Proactive participation remains a later hypothesis beyond responding when explicitly addressed.

Roadmap implications: prioritize independent iPhone use without a Mac relay, practical capture while the phone is put away, and useful recall/questions about captured conversations. Define and verify each as a separate slice. Stronger attribution is needed before memories or responses depend on who said something. Preserve the shared native foundation and the Proven → Better → New delivery discipline; this direction does not add all companion features to V0.

## Clarification: Granola is the Proven

The authoritative Proven entry is **Granola**, the reference product itself. The earlier proposed breakdown—start a recording session, capture a transcript, write your own notes, get organized AI notes, and revisit the conversation—is superseded and must not be used as the Proven definition.

Those interactions may describe use cases, but they do not replace the agreed framework above.

## Source grounding

[Mark Pincus and Garry Tan video](https://www.youtube.com/watch?v=oHwUD9b9_pg&t=591s)

- 7:14–9:43: AI listening in a conversation; asking its perspective; using ongoing context and transcripts.
- 9:46–11:42: Apply Proven, Better, New; Granola as the proven reference; price and speed as better; continuous listening as a hypothesis.
- 15:06–16:34: Response latency, listening/responding, and the possibility that a novel feature attracts trial without retaining users.

The discussion includes uncertainty about what will work. Preserve that distinction: the vision is agreed; product-market fit and individual features are not proven.

## Delivery guidance

Build Proven, then Better, then New. The [V0 scope](v0-scope.md) defines the first narrow implementation slice; it does not redefine Granola as the Proven. [Engineering principles](engineering-principles.md) govern implementation choices and agent verification workflows.

## V0 acceptance clarification

Founder decision, September 24, 2026: speaker diarization is best-effort for the internal voice-in/transcript-out slice and is not a strict completion gate. Text must display without waiting for speaker identity. This does not change Granola as the Proven or the one-liner. Attribution-dependent memories and proactive companion participation require separate validation later; V0 does not establish who the user is from anonymous speaker labels.

## V1 implementation refinement — September 25, 2026

Founder decision: use direct Luna for V1 questions and proceed to Ask while listening. Defer Jev intent routing after its quality evaluation; it is an optional future implementation tool, not a product requirement or V1 gate. The one-liner and PBN remain unchanged. See [decision](v1-jev-decision.md).

## Automatic memory refinement — September 25, 2026

Founder decisions for the next slice: learn automatically from captured conversations and allow relevant past context to inform Ask in a new conversation. No memory suggestion inbox, approval-per-memory flow, Forget button or memory-management screen. Memory maintenance is internal: supersede corrected claims, expire temporary context, invalidate unsupported claims and consolidate duplicates. Retirement from current context does not erase useful history or imply an event was completed. Existing session deletion remains supported.

Use Jev for bounded memory judgments and relevance assessment of retrieved candidates, with application code enforcing ownership and lifecycle rules. Supermemory is research inspiration only, not an integration. Unknown speakers must not become user facts. These are agreed product directions; the [memory implementation plan](memory-implementation-plan.md) defines proposed checkpoints and verification, not delivered capabilities. The one-liner and PBN remain unchanged.


## Personal companion profile — September 25, 2026

Founder decision: personal memory should understand the person across their whole life, including relationships, family, pets, background, interests, routines, preferences, values, goals and changing circumstances. These are flexible kinds of knowledge, not required fields or a work-oriented persona. Journaling, appointments, lectures and everyday conversations are central alongside meetings. The intended feeling is personal intelligence on tap: being remembered well and receiving relevant understanding when needed, without claiming to know everything.

Build the profile memory slice before voice enrollment. Start with explicit personal text as a source of known user authorship; authorship alone does not make every mentioned fact about the user. Unknown recorded speakers remain unknown. Reuse automatic learning, source links, corrections and internal forgetting; no per-memory approval inbox or management screen. Voice recognition is a separate later identity feature. See the [personal-profile plan](personal-profile-plan.md). The agreed one-liner and PBN are unchanged.

## Companion-first interaction refinement — September 26, 2026

Founder-approved ICP: a curious, ambitious, AI-comfortable person who thinks out loud and wants an attentive personal companion that understands their life without repeated explanation. The founder, Mark Pincus and Garry Tan are reference personas; the initial audience is a shared mindset rather than a job title. Whole-life understanding includes family, relationships, interests, goals, studies, work and appointments.

The companion is the primary experience; transcripts and notes supply evidence. Two actions: **Capture meeting note** and **Talk to companion**. Voice notes and meeting recordings are one capture type, not separate memory silos. Chat is ongoing across recordings, works without opening a recording, and stays available while capture continues using the transcript received so far. The desired feeling is talking with an attentive friend, with sources available when useful.

The separate personal-note creation path is an interim QA mechanism, not the normal product workflow. Existing sources retain their provenance. Unknown speakers remain unknown until supported identity evidence exists; voice recognition is a later slice. No memory approval inbox or user-facing forgetting flow. Muse is the founder's interaction reference, not a claim of feature parity or a changed one-liner. Granola remains the Proven. See the [memory rework plan](memory-rework-plan.md) for proposed delivery and acceptance boundaries.
