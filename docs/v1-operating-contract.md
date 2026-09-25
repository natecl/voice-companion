# V1 operating contract

Status: implementation requested September 24, 2026; checkpoint 0 underway. The founder accepted the paid Render recommendation after reviewing its free-tier limitations and approximately $7.25/month baseline. Render CLI authentication and workspace access are verified; the founder has now explicitly approved up to $5 total V1 provider-testing spend, allocated as below. The internal relay is deployed and successive physical-iPhone recordings are verified; see [hosted validation](v1-hosted-validation.md). Checkpoint 1 review and targeted verification are complete. Governed by [engineering principles](engineering-principles.md) and the [V1 plan](v1-implementation-plan.md).

## First delivery and deployment proposal

Make the physical iPhone record and save two successive sessions with the Mac relay off. Keep Swift/SwiftUI, Grok STT, and the existing transcript/storage contracts. Extend the Python service boundary; do not expose the development relay unchanged.

Recommend one paid Render Starter web service in a US region, one process/instance, and a 1 GB persistent disk for a SQLite authorization/usage ledger. No server transcript database, vector database, or separate queue. Disable automatic deploys and previews; deploy an explicitly tested commit. A deployment can interrupt recording, so schedule it outside active QA and surface interruptions honestly.

Official documentation reviewed September 24:

- [WebSockets](https://render.com/docs/websocket): supported without a fixed connection-duration limit; instance replacement still disconnects clients.
- [Persistent disks](https://render.com/docs/disks): persist across restarts, but constrain a service to one instance and remove zero-downtime deploys. This is acceptable for the initial founder trial, not a scaling claim. Disk snapshots do not replace a tested SQLite backup procedure.
- [CLI](https://render.com/docs/cli): supports deployment, logs, and noninteractive operation, allowing agents to run and inspect the service.
- [Pricing](https://render.com/pricing): Starter $7/month plus disk $0.25/GB/month, approximately $7.25/month baseline before taxes and usage extras. Reconfirm the checkout before purchase.

Render CLI 2.28.0 was installed and authenticated. The existing workspace is selected; its unrelated service was only inspected and was not modified. The dedicated Voice Companion service is deployed; see hosted validation for its identity and tested commit.

## Request flow and authentication

Proposed first-trial contract, to implement and test:

1. Manually enroll the founder with a random 256-bit app credential, an expiry, and a revocable server record. Store only its hash on the server; install the credential in the app's Keychain through a deliberate internal setup flow. Never embed a shared secret in source or the app binary. Public signup and account recovery are deferred.
2. iPhone connects to the service over public-trust TLS. The service validates authorization, expiry, revocation, concurrency, and durable budget before opening a provider connection.
3. Microphone PCM flows through the service to xAI; transcript events return to the app and local session storage. Stop/disconnect closes upstream with bounded cleanup. No automatic paid reconnect or retry.
4. Reserve the maximum permitted request spend atomically before contacting the provider. Keep unresolved reservations charged after crashes; restarting must not reset quotas. Reconcile only when evidence permits. Fail closed if the ledger is unavailable. Use separate transcription and Ask allocations.
5. Revocation rejects subsequent requests and terminates an active stream within five seconds. Use opaque user/request IDs in logs; never record tokens, audio, transcript text, questions, or answers in routine telemetry.

One active recording per user and initially one globally. Use a single-instance deployment guard. An unavailable server ends the session visibly and preserves received text; it must not imply ongoing capture.

## Proposed paid-trial envelope

Founder approved approximately $7.25/month hosting and **up to $5 total V1 provider testing spend**, not a recurring $5 daily allowance. Working allocation: $2 STT, $2.50 answers, $0.50 Jev. Enforce component limits and a global ceiling through conservative reservations; provider estimates are not verified invoices or an account-wide billing guarantee. Check available provider account limits before enabling traffic.

Keep the app's five-minute capture limit, the relay's 310-second PCM allowance, and 330-second wall timeout initially. Propose six recording attempts per user per UTC day and a global six-attempt daily limit for the founder-only trial. Failed attempts consume an attempt; UTC rollover does not reset the overall evaluation envelope. Limit ordinary Ask to 20 attempts per day; any larger held-out evaluation needs its own explicitly bounded run. Disable unused endpoints until their checkpoint is implemented.

[xAI pricing](https://docs.x.ai/developers/pricing) lists streaming STT at $0.20/hour. Five minutes is approximately $0.0167; the 310-second server allowance is approximately $0.0173. Reserve at least $0.02 per attempt initially, subject to validating billing semantics. Six full attempts are about $0.1033 of audio processing, excluding infrastructure. A later 30-minute test would cost about $0.10 of audio, but increasing the cap requires its own bounded verification.

First checkpoint live QA: at most two 20-second sessions after explicit founder readiness, no automatic retry. Estimated audio cost $0.0023 total; authorization can still reserve full request allowances. A failure is investigated locally before another paid attempt.

## Selected answer model and Jev

Founder decision, September 24: use **GPT-6 Luna (`gpt-6-luna`)** for V1 answers and shape its personality and behavior through the versioned [companion prompt](../Backend/prompts/companion-v1.md). This supersedes the earlier Grok candidate and conversational recommendations of Sonnet/Gemini. No comparative model testing is planned, per founder instruction. Required functional integration QA remains scoped to the selected model; this decision is not a measured quality claim.

The [official model page](https://developers.openai.com/api/docs/models/gpt-6-luna), reviewed September 24, lists $0.10 per million input tokens and $0.50 per million output tokens. A 5,000-input/500-output answer would be approximately $0.00075. Founder explicitly requires reasoning off: send `reasoning: {"effort": "none"}` on every answer request (the provider default is medium). Use Standard processing, streaming via the Responses API, with no web/tools. Verify access and request behavior at integration. An OpenAI API credential must remain server-side; no Luna calls or live integration exist yet.

Founder clarification: prioritize quick responses with Standard processing and reasoning off. This explicitly supersedes the earlier Flex choice. Latency remains unverified until integration QA. Do not silently enable reasoning or upgrade to premium processing. Disable SDK automatic retries. These are planned settings, not an implemented integration.

Propose a 16,000-token total input ceiling and 1,000-token output limit per Ask. At Standard rates the maximum token estimate is $0.0021 before safety margin; retain the conservative $0.003 reservation per request once token counting and limit semantics are verified. Reject oversized context clearly instead of silently truncating. Use stateless requests with `store: false`; that does not by itself remove provider abuse-monitoring retention. See [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data).

Jev remains checkpoint 4: one typed routing judgment per Ask, not a prose generator or constant transcript processor. Its [introduction](https://docs.typesafe.ai/introduction) confirms typed decisions. Recheck endpoint, version, pricing, retention, and credentials before sending any transcript context. No Jev call is needed for independent recording.

## Retention and deletion responsibilities

App: transcripts and later Q&A remain local; deleting a session removes its associated local content. Review device-backup behavior before describing deletion guarantees.

Service: keep audio and conversation payloads in memory only, with bounded buffers; persist only credential hashes, revocation/expiry, request status, reservations, and content-free usage metadata. Retain detailed operational records for 30 days, with aggregate budget counters retained for the evaluation lifetime so cleanup cannot reset spend. Administrative user deletion revokes access and removes the credential record; retain only de-identified accounting needed to preserve the global spend cap. Document disk-backup expiry separately before inviting other users.

[xAI API security documentation](https://docs.x.ai/developers/faq/security) states default API retention is 30 days and API content is not used for training without explicit permission. Team-wide zero-retention options may be available but have not been verified for this account or STT. Do not change shared account settings without checking their impact. Local deletion does not delete provider audit copies. TypeSafe retention remains a checkpoint 4 prerequisite; do not describe cloud processing as on-device or zero-retention by default.

## Pre-measurement targets

These are internal acceptance targets, not measured results or public latency claims:

- Checkpoint 1: two complete successive physical-iPhone sessions, Mac relay off; invalid/revoked/over-budget requests cause zero upstream calls in local socket fixtures. Crash/restart preserves charged reservations. Normal disconnect closes upstream within five seconds in local tests.
- Capture: first displayed transcript within five seconds of speech onset on each short live QA session; log the observation and distinguish network/provider time where observable. Do not wait for speaker labels.
- Direct Ask: 12 fixed synthetic cases covering recall, summary, perspective, missing information, wrong-session context, unknown speakers, and quoted prompt injection. Every reference must resolve and support its associated claim on review; zero fabricated facts in the missing-information cases. First text within three seconds and completion within 15 seconds on at least 10 of 12 cases. This small set is a smoke gate, not a statistical latency claim.
- Jev: develop on 12 labeled questions, then freeze a separate 24-question held-out set before the paid run. At least 22/24 acceptable routes, zero harmful routing mistakes, and direct fallback for timeout/malformed/uncertain output. Maximum routing wait 750 ms. Compare answers against the direct baseline on eight representative cases; require a recorded improvement on at least two without grounding regressions, with median added first-answer latency no more than 500 ms. A failed gate requires investigation and founder scope resolution, not retroactive threshold changes.

## Immediate next action

Checkpoint 1 is verified; merge the reviewed checkpoint, then implement pocket-ready capture in checkpoint 2. Keep the current five-minute cap until the separately bounded longer-capture check. Manual locking/speech/interruption QA still requires explicit founder readiness. Luna and Jev remain later integrations; the $5 total provider-testing ceiling persists across checkpoints.
