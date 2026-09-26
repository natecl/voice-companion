# Persistent main-chat storage foundation

September 26, 2026. Checkpoint 6A1 is a backend storage foundation, not a shipped chat interface or a new model integration. Schema 13 is additive; hosted code and native apps are unchanged.

`CompanionChat` stores one stable main conversation per authenticated owner and ordered question/answer pairs. The server must resolve the owner from the authorized credential; this module is not an authentication API. Two credentials explicitly bound to the same owner share the main conversation. Different owners cannot read, finish or inherit each other's turns.

## Durability and inference control

A question ID is durable and idempotent: replaying the same ID/text returns its existing state and `created=False`; changing the text conflicts. A unique partial SQLite index permits only one pending question per owner. A failed or interrupted request never automatically retries inference. A pending turn survives restart; the future service must reconcile interrupted work explicitly and mark failure before starting a new question. No startup recovery or provider invocation is introduced here.

Questions are limited to 1,000 characters; completed answers to 16,000 bytes; storage to 2,000 turns per owner for this internal slice. Pagination returns at most fifty turns, ordered with a stable sequence cursor. Model-history preparation returns a bounded suffix of at most eight whole completed turns and 6,000 serialized bytes, with `history_limited` when constrained. It stops at failed/invalidated history rather than skipping that gap and reviving older context. It never treats assistant text as a new source of facts.

## Source-derived history

Completion records references and fingerprints of all canonical evidence supplied to the answer, not just cited passages. A follow-up inherits every dependency of the previous turns included in its context, even when its answer omits citations. The integrating service must pass those history IDs and every attached/retrieved/live-source evidence packet used to generate the answer; arbitrary client-provided history is not accepted as a trusted input contract.

Stored citations contain canonical source locations, not duplicated transcript text. Citation IDs must match the answer and supplied source dependencies. A source deletion/revision atomically scrubs affected answer text, citations and dependency rows. Follow-ups are scrubbed too because they inherited the same dependencies. Original user questions remain their own authored messages. IDs and invalidated states remain so the future UI can show an unavailable-answer placeholder.

Other evidence changes, such as corrections, identity or validity transitions, are detected by canonical rehydration on page/history reads and before completing a pending answer. Outdated answers cannot silently enter new context. An in-flight answer with changed evidence fails completion; no stale answer is saved. A bounded fifty-dependency ceiling fails explicitly instead of dropping provenance.

## QA

On the development Mac, Python 3.13: `python3 -m unittest discover -s Backend` passed **274 tests**. Eight new real-SQLite cases cover concurrent duplicate submission, stable reopen and owner isolation, terminal failure/restart, source deletion plus uncited follow-up invalidation, revision during answer generation, correction without source revision, invalid citations, whole-turn history bounds/pagination and schema-12 migration preserving sources/tombstones. Existing migration assertions advance to schema 13 without loosening prior content checks.

Separately exercised a two-process storage path: first process wrote a source-cited answer and an uncited follow-up; second process reopened the identical conversation, replayed the same question without creating a duplicate, deleted the original source, and inspected both answers and dependency rows. Both answers were scrubbed, history became empty and zero dependencies remained. Sanitized receipt: `Backend/fixtures/chat-storage-qa.json`. No provider or STT calls, no hosted mutation.

## Integration still required

Server-authoritative chat/attachment request validation, bounded current/attached/past context assembly, model instructions for conversational history, streaming persistence/reconnect behavior, API routes and native UI are later checkpoints. Source-backed active capture needs a versioned snapshot contract; this module does not assume anonymous live speech is the user or accept unsynchronized text as durable evidence. Physical acceptance remains gated on founder readiness.

Back up and verify schema migration on a canonical database copy before any separately approved rollout. Disabling a feature is safer than running a schema-12 binary against schema 13; do not restore a backup in a way that resurrects source deletions.
