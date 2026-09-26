# Bounded companion context assembly

September 26, 2026. Checkpoint 6A2 is an internal context constructor; it does not change the hosted Ask route, native interface or model prompt. It requires no inference. Live snapshot persistence and conversational model integration remain necessary before serving this contract.

`companion_context.assemble` combines the question, server-loaded recent main-chat history, an explicitly attached finalized recording, a fixed live-capture snapshot and a validated past-evidence packet. Each source group is labelled separately. An empty library produces a valid empty-source context. The service must resolve the authenticated owner and retrieve past evidence before supplying that packet; clients cannot supply trusted past memories or assistant history.

## Boundaries and provenance

Attachments are owner-scoped canonical sources, with an exact revision. Missing/deleted sources, a changed revision or an unfinished attachment fail explicitly. Stored personal text retains its original provenance. Live input is validated as an unfinished recording and deep-copied at the question cutoff; later client speech cannot mutate the context. Attaching the same recording as both finalized and live is rejected.

Small attachments remain complete. Large ones use query-matching original text windows, including neighboring characters for context, with overlapping selected spans merged. This is bounded lexical selection inside the explicitly requested source, not semantic ranking or a whole-recording summary. Coverage is `partial` or `partial_no_match`, never silently labelled complete. No-match long attachments supply no invented excerpt. Long live captures can fall back to their latest window, explicitly partial. Canonical originals remain intact.

History is loaded from `CompanionChat`, never accepted from a client. Its canonical source dependencies are rehydrated alongside the prior dialogue, so assistant prose is not the only evidence for a follow-up. Old citation IDs are remapped to the new context's source IDs without rewriting stored messages. Exact duplicate source spans are supplied once across attached, past and history groups. Live evidence stays separate. Source packets are validated again before returning the context.

The constructor caps the serialized payload at 12,000 bytes and twelve sources. Recent history starts at a 3,000-byte whole-turn bound. If necessary, older whole turns and their dependent evidence are removed together, with `history_limited=True`. If the required source groups still exceed the limit, construction fails rather than silently dropping source qualification or a linked correction. The eventual provider adapter must additionally enforce its prompt-plus-payload budget.

Explicit `use_memory=False` and supported direct requests such as “Only use this transcript” suppress past context before reading chat history. A supplied past packet under that restriction is rejected. The eventual service must apply the same opt-out before initiating retrieval/inference; this constructor cannot undo a call made earlier by a caller.

## Live persistence is deliberately not implied

A live snapshot is not written as a finalized memory source. Doing so would make subsequent transcript revisions invalidate earlier chat answers during ordinary capture. The return value includes the immutable snapshot and `requires_live_persistence=True`; an integrating service must persist and validate its provenance before committing the answer. Passing only the returned finalized-source packets to chat storage would be incomplete and is not an accepted integration. No serving route calls this constructor yet.

## QA

On the development Mac/Python 3.13, the full backend suite passed **280 tests**. Six new real-SQLite context checks cover empty-library chat, canonical follow-up evidence, deletion, owner/revision isolation, attached/past deduplication, a late fact in a long recording, partial no-match, immutable live input, independent live/attached groups, history bounds, early opt-out and citation remapping. The explicit boolean opt-out was added afterward and all six targeted checks passed again.

A separate assembly run selected “The access code is cobalt” near the end of an approximately 12 KB synthetic lecture while retaining a separate fixed live question snapshot. The assembled payload was 2,909 bytes, attached coverage was partial, and later mutation of the caller's speech did not change the prepared input. The live recording was absent from canonical memory. Receipt: `Backend/fixtures/companion-context-qa.json`. No provider calls, no new transcription, no hosted mutation or physical-device claim.

Next: durable live-snapshot provenance, the actual persistent-chat streaming service and a bounded live conversational response gate; then native main-chat/library wiring and approved rollout/physical acceptance.
