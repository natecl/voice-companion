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
