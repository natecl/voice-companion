# Voice Companion

> Granola with an AI that listens alongside you and can join the conversation.

An iPhone-first companion for everyday conversations, with Mac support. Working name: Voice Companion. This private repository contains the native apps and canonical product knowledge. Mac and iPhone apps can replay a sample transcript, show speaker labels, and save/reopen sessions. Mac and iPhone microphone transcription is available through the bounded local development relay, with encrypted LAN transport for iPhone. This is an internal development build with best-effort speaker labels, foreground recording, a five-minute session cap, and local transcript storage. See the [V0 runbook](docs/v0-runbook.md) for setup, current acceptance, and known limitations.

## Product source of truth

[Proven, Better, New](docs/product-source-of-truth.md) is the authoritative product definition agreed with the founder. It takes the framework applied by Mark Pincus and Garry Tan to the voice companion idea as its starting point. Granola is the **Proven**.

## Engineering source of truth

[Engineering principles and agent feedback loop](docs/engineering-principles.md) is the canonical authority for how we select tools, design, implement, debug, test, review, and deliver this product. Product direction and engineering principles are complementary sources of truth. Provisional technology choices still require evidence.

## Knowledge documents

- [Product source of truth and one-liner](docs/product-source-of-truth.md)
- [Founder context and examples](docs/founder-context.md)
- [V0 scope and delivery sequence](docs/v0-scope.md)
- [V0 implementation plan](docs/v0-implementation-plan.md)
- [V1 companion-on-tap plan](docs/v1-implementation-plan.md)
- [Engineering principles and agent feedback loop](docs/engineering-principles.md)
- [Transcription direction and unresolved selection](docs/transcription-direction.md)
- [Synthetic quality screen and remaining acceptance](docs/quality-evaluation.md)
- [Permission, empty-transcript, and microphone-disconnect QA](docs/reliability-edge-cases.md)
- [Initial streaming validation evidence](docs/transcription-validation.md)
- [Source index: videos and X posts](docs/sources/README.md)
- [Video 1 transcript](docs/sources/transcripts/01-pincus-tan.txt)
- [Video 2 transcript](docs/sources/transcripts/02-state-of-startups.txt)
- [Garry Tan X posts supplied by the founder](docs/sources/garry-tan-x-posts.md)
- [Jev research and possible implementation role](docs/jev-research.md)

Sources and research inform the product; they do not silently change its definition. Implementation proposals remain hypotheses until accepted by the founder.

## Development

See [development commands and foundation QA](docs/development.md). The shared SwiftUI source is in `App/`; `project.yml` generates both native app targets and their UI tests.
