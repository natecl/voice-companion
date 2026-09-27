# Product source of truth

Status: Agreed with the founder on September 24, 2026.

Current interpretation: later dated refinements below supersede conflicting earlier delivery descriptions. See [current implementation and decision brief](current-state.md) for deployed versus candidate status. In particular, notes are implemented; release chat hides visible sources; TTS/voice identity remain deferred; the experimental retrieval gate is disabled.

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


### Main chat and recording-library refinement

Founder decision: default to one persistent main companion chat; optional side conversations come later, with separate discussion histories and shared relevant personal memory. Starting a capture or returning to the app does not start a new chat. Keep a recording library with one item per capture. “Ask about this” opens the main chat with that recording visibly attached; citations return to the original recording passage. Capture stays available across chat and library, and navigation preserves recording, drafts and reading position.

Eventually each recording will offer notes/summary and its transcript. For the current rework, deliver existing transcript access, deletion and chat connections; defer summary generation, note editing and side-conversation UI. Generated summaries are derived views, not independent factual evidence. The Manus Companion/Workspace pill toggle is a layout reference, not a required visual design. The one-liner and PBN remain unchanged.

## Recording deletion and retained memory — September 26, 2026

Founder decision: deleting a recording removes the recording/transcript from the library but may retain already learned memories, which remain usable in companion answers. Recording deletion is not a request to forget learned knowledge. Remove links to unavailable passages; never present retained memory as a still-viewable original source. Preserve corrections, identity uncertainty and temporal qualifications. Communicate this distinction in deletion copy. This supersedes earlier source-deletion cascade requirements for ordinary recording deletion. Explicit memory erasure is a distinct future behavior; do not infer that it is already implemented.

The [retention implementation](retained-recording-memory.md) separates committed learned claims and their bounded supporting excerpts from the deleted transcript. Live-provider acceptance is verified and the [internal rollout](retained-memory-rollout.md) is deployed; the bounded physical-iPhone deletion, recall and reopen check has passed. Legacy unsupported claims are not backfilled, and previously deleted content is not restored.

## Lean notes slice — September 26, 2026

Founder-approved direction: consolidate around a lean Proven/Better/New experience, with transcript-derived notes next and spoken companion participation afterward. Notes and summary are one feature. Generate after capture from the recording transcript only, save beside it, preserve supporting passage references, and adapt structure to the content. Proactive participation remains deferred. The [notes plan](recording-notes-plan.md) separates storage, generation, native integration and physical acceptance. Permission to simplify the memory system is not a completed replacement or a change to recording-deletion semantics; evaluate notes-based retrieval separately before retiring existing machinery.

## Notes-first consolidation — September 27, 2026

Founder authorizes implementing notes-first past-context retrieval with Jev ranking, direct transcript fallback and a thin personal layer. Preserve current conversation context, original passage citations, uncertainty, attribution, corrections and learned knowledge retained after recording deletion. Thin means a simpler implementation, not work-only or shallow personal understanding. Nonpersonal retained knowledge stays distinct from personal profile facts. Replace existing complexity only after matched behavioral evidence; the approved direction is not a claim that Jev retrieval or the replacement has passed QA. See [delivery plan](notes-first-memory-plan.md).


## First-release input and companion feel — September 26, 2026

Founder clarification after memory consolidation: spoken replies/TTS are outside the first release. Add explicit voice dictation into the chat composer: stop to retain editable text, or Send to finish transcription and submit the combined draft. No automatic sending merely because speech stops. Voice recognition/enrollment and manual voice-note labeling remain outside this slice; unknown recording speakers remain unknown. Refine the companion toward the agreed attentive-friend experience. See [input contract and personality direction](companion-feel-and-dictation.md); that document separates candidate implementation and proposed tone examples from verified behavior.

## Plain-message companion replies — September 26, 2026

Founder decision: the first release companion should respond as ordinary messages, without visible source markers, source buttons or a source list. Keep the evidence and provenance internally for factual grounding, corrections, invalidation and debugging. This supersedes the earlier visible chat-citation requirement; recording-library access and notes-to-transcript navigation remain. Update the personality toward the attentive, candid, naturally personal direction in [the companion brief](companion-feel-and-dictation.md). This is authorization to implement the candidate, not proof of new prompt quality or deployment.


Founder clarification: Talk to companion supports ordinary ongoing conversation, general questions, brainstorming and reflection without needing a recording. Captured context makes relevant answers more personal; it does not limit the companion to retrieval questions or require every reply to mention memories. This grants no additional tools or autonomous actions.

## Retrieval-gate decision

After the bounded Jev classifier screen, the founder chose to keep the pre-retrieval gate disabled. Existing past retrieval and Jev evidence ranking remain unchanged. Chat style is interpreted by Luna from the message and context; no separate normal-chat/brainstorming/retrieval mode classifier is enabled. See [evidence](memory-gate-screen.md).


## Private composer dictation — September 27, 2026

Founder decision: speech addressed to the companion through composer dictation is separate from meeting capture. Pause meeting audio while dictation captures speech, visibly explain the pause, and resume automatically when dictation stops. Other people speaking during that interval are also omitted; no voice identification or simultaneous-speaker separation is claimed. Typed chat and waiting for the companion answer do not pause capture. Dictated questions must not enter the meeting transcript or derived notes through the recording path. They remain ordinary chat when explicitly sent.
