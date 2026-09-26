# Indexed recall and answer integration

Checkpoint 5G adds `IndexedMemoryRecall`, compatible with the existing Ask streaming boundary. It executes owner-scoped hybrid retrieval, bounded Jev ranking, deterministic correction/conflict expansion and selected-evidence validation. Legacy recall remains the hosted default until the separate reviewed rollout flag is wired and approved.

Explicit `memory:false` is now accepted by the request validator and skips recall. The indexed adapter additionally recognizes a narrow anchored set of direct English opt-outs such as “Don't use my past notes” and “Only use this transcript” before even looking up an owner. Quoted/reported instructions do not match that anchored rule. This is not a claim of recognizing every natural-language paraphrase.

Memory source IDs remain m-prefixed and retain session/revision/time fields compatible with the current app. At most eight source passages are sent, matching the native decoder's existing limit. Related evidence is kept together; exceeding a source or joint prompt budget produces an explicit unavailable-memory fallback rather than dropping the correction. The current transcript stays intact. A partial semantic index is labeled as partial, not presented as complete recall.

The added indexed-memory instructions distinguish usefulness from truth, unknown identity from the account owner, unresolved changes from accepted corrections, whole-passage claim metadata from exact source windows, and old records from current applicability. Code-managed prompt/input boundaries follow the [official OpenAI prompting guidance](https://developers.openai.com/api/docs/guides/prompt-engineering). The requested answer model remains gpt-6-luna with reasoning none, default service tier, no tools, no storage and no automatic retry.

## Verification

- Full backend suite: **258 tests passed**. Actual local WebSocket Ask checks verify citations, source deletion during generation and memory-outage fallback; storage checks cover corrections, unrelated new sources, owner isolation, empty-library no-spend, opt-out and combined prompt limits.
- Frozen live recall → Jev → qualified source packet → actual Luna streaming: all three cases passed. Correction: tennis with the newer supporting citation. Unknown speaker: declined to identify the recorded runner as the user. Unresolved change: explicitly retained uncertainty between swimming and tennis and cited both sources.
- Observed live recall: 0.261/0.210/0.190 seconds, within the existing three-second recall deadline. The live gate used lexical candidates in the remote scratch environment; the real local semantic/queue path was separately verified in 5B/5C/5F. This is not hosted embedding resource acceptance.
- Evidence: `Backend/fixtures/indexed_answers/{answers.json,ranking-calls.json}`. Six paid calls (three Jev, three Luna), no retries. Canonical ledger: **$2.18 reserved of $2.20**, with **$0.02 remaining** (85 Luna calls, 133 Jev calls). These are conservative reservations, not invoiced cost.

No production database migration, hosted deployment or physical/native claim. Persistent chat, attachment/history assembly, semantic runtime wiring/resource acceptance and final device QA remain pending. This adapter currently selects one strongest relevance seed plus its change-related evidence; broader independent multi-source questions remain a context-assembly requirement.
