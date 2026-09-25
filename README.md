# Voice Companion

> Granola with an AI that listens alongside you and can join the conversation.

An iPhone-first companion for everyday conversations, with Mac support. Working name: Voice Companion. The installed internal V1 build records microphone audio through the hosted service, supports locked-screen capture, saves transcripts locally, and answers typed questions during or after a conversation with fixed source references. Recording remains capped at five minutes; speaker labels are best-effort. See the [V1 runbook](docs/v1-runbook.md) for use, setup, quotas and known limits, and [final acceptance](docs/v1-acceptance.md) for evidence. The [V0 runbook](docs/v0-runbook.md) retains local Mac relay instructions and historical scope. This private repository is not a public release.

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
- [Automatic memory research and proposed harness](docs/automatic-memory-research.md)
- [Automatic memory implementation plan and PR checkpoints](docs/memory-implementation-plan.md)
- [Memory foundation contract and local QA](docs/memory-foundation.md)

Sources and research inform the product; they do not silently change its definition. Implementation proposals remain hypotheses until accepted by the founder.

## Development

See [development commands and foundation QA](docs/development.md). The shared SwiftUI source is in `App/`; `project.yml` generates both native app targets and their UI tests.
