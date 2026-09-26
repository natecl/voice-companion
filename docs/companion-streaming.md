# Persistent companion streaming service

September 26, 2026. Checkpoint 6A4; opt-in handler only, no hosted route or native UI enabled. Additive schema 15 stores request-context fingerprints alongside existing turns.

## Contract and lifecycle

`CompanionService` authenticates the credential and resolves its owner server-side. History requests are owner-scoped and paginated without model admission. Ask requests contain a question ID, question, explicit memory flag, optional exact-revision attachment and optional validated live snapshot. Arbitrary assistant history, past memories and extra request fields are rejected.

Duplicate IDs are bound to the question plus memory setting, attachment and live input. An identical repeat returns the saved/pending/failed turn without another reservation or model call. Reusing the ID with different context fails. Only one pending turn per owner is admitted. Accepted requests reserve the existing Ask allowance; failed requests do not automatically refund reservations or trigger another inference.

The handler builds context, performs optional bounded indexed recall, streams Luna's answer, verifies source references and current evidence, then commits the answer and all history/source dependencies before emitting `saved=True`. Disconnect, revocation, deleted/changed evidence, invalid citations, incomplete generation and timeouts terminate the attempt. A failed attempt releases unreferenced live snapshots. Protected completion waits for its storage transaction even if the socket closes, allowing a later identical request to recover a committed answer rather than spend again.

Startup recovery is explicit and must run under the existing exclusive service lock: mark interrupted pending turns failed and remove unused prepared snapshots. It never retries inference. The handler has a five-second initial-message timeout, three-second recall deadline and twenty-second generation lifecycle bound. Content-free telemetry records request ID, completion, first-text/elapsed seconds and available token counts; no question, source text, answer text or credentials are logged by the service.

## Conversation behavior

The new versioned prompt applies only to `companion-context-v1`. Existing `/ask` instructions remain unchanged. Preserve GPT-6 Luna, reasoning none, default service tier, `store=False`, no tools and no automatic SDK retries. Prior conversation and original evidence are explicitly supplied by our source-aware harness; no provider-hosted persistent conversation is created.

History supports natural follow-ups but is not independent factual evidence. Canonical corrections outrank older capture snapshots; sources retain uncertainty and unknown-speaker attribution. Empty-library general questions work. Explicit memory opt-out occurs before recall/history use. The final provider input check includes prompt overhead; an oversized assembled context fails rather than being silently truncated.

## QA and failures

Full backend suite: **292 tests passed** on the development Mac/Python 3.13 after the final changes. Real socket replay covers durable save/history, identical replay without spend, changed-context conflicts, concurrent duplicates/busy requests, cross-owner isolation, malformed requests, memory opt-out, disconnect cleanup, source deletion and revocation during streaming, invalid citations and interrupted-request recovery. Captured model responses are checked against the current prompt and reference contract.

Live scratch execution on the existing Render host exercised the real handler → storage/context → provider stream path with synthetic data. No production code, canonical memory source, native build or STT path was changed. Evidence is in `Backend/fixtures/companion-service/`.

The initial gate correctly answered during capture, followed up about whether swimming needs a pool, selected a source-linked tennis correction over older swimming history and answered 2+2 without memory. Its anonymous-speaker answer failed manual review: it expressed temporal uncertainty without explaining uncertain identity. The old keyword check accepted “can’t confirm” too broadly. Preserve this failed output in `provider-calls.json`; the whole first gate is not considered passing.

The revision explicitly labels snapshot speaker identity unknown and distinguishes a current live cutoff from earlier snapshots. Targeted live outputs now say the runner speaker “hasn’t been identified as you”; the held-out daughter/Iris answer likewise refuses to establish the relationship from an unidentified speaker. The tennis correction regression still passes. That check replays the exact unchanged Jev ranking request/response, verified by request equality, to avoid paying again for an unaffected boundary. A final quoted-instruction case answered “Maya enjoys tennis” with its citation instead of following the embedded instruction to answer BANANA. These are small synthetic gates, not a general accuracy guarantee.

## Allowance and remaining work

Ten calls reserved $0.10: the initial five Luna/one Jev sequence, three targeted Luna calls, and one Luna quoted-instruction check. Canonical total is **$2.38/$2.40**: 97 Luna and 141 Jev calls, leaving **$0.02**. Reservations are conservative estimates, not verified invoice totals. No identical paid retry or new transcription.

Hosted runtime selection/resource validation, relay routing, native main-chat/library integration, source navigation, rollout approval and physical acceptance remain. The handler is exercised in isolation and is not deployed. This checkpoint does not claim the new UI or microphone/chat coexistence is verified on the phone. See the [frozen gates](companion-streaming-gate.md) and [OpenAI conversation-state guidance](https://developers.openai.com/api/docs/guides/conversation-state) informing manual context management.
