# Conversation-level proactive validation

## Outcome

Move beyond one useful reminder: check whether the companion remains helpful after acknowledgment, resolution and topic changes, without changing the phone UI or adding inference on every transcript event. No new tuning is justified until this sequence supplies evidence.

## Implemented free checkpoint

Run `PYTHONPATH=Backend python3 scripts/evaluations/proactive_conversation_replay.py /tmp/conversation-replay.json`.

The replay uses actual ProactivePolicy, source retrieval, current v4 request construction, ProactiveService, SQLite turn persistence and reopen. It advances virtual time past the real 60-second cooldown. Sources and speech are fictional, model responses are explicitly scripted, and there is no audio or network. Exported requests preserve the exact current context and prior contributions for a separately funded model screen.

| Time | Event | Expected application result |
| --- | --- | --- |
| 0s | Cedar calendar proposal misses the five-person prerequisite | Save first contribution |
| 30s | Speaker acknowledges the plan | No scheduling during cooldown |
| 65s | Speaker explicitly settles the plan | Evaluate with acknowledgment and previous message available |
| 90s | New topic already includes the relevant venue facts | Evaluate; correct model behavior is silence |
| 115s | New participant proposes a venue that violates the known constraint | Allow a distinct useful contribution |
| 180s | Cedar reminder is already addressed; scripted model repeats anyway | Durable same-evidence duplicate defense rejects it |
| 205s | Quiet, with recording still active | No scheduling; capture remains active |

Observed replay: two saved messages, five synthetic model requests, no paid calls. Assertions inspect current text, previous contribution context, cooldown boundary, duplicate defense, Quiet and reopened history. Forty-three proactive tests pass. No App/, native test, UI component or project changes. Existing SQLite ResourceWarnings remain; no new storage lifecycle change is claimed.

This does **not** prove model acknowledgment detection or useful timing. Scripted silence is a contract fixture, not semantic evidence. Duplicate protection identifies source spans, not every paraphrase or equivalent detail spread across notes; that limitation remains. The exported sequence supplies earlier synthetic agent messages, so the next model screen is teacher-forced context, not a claim of an autonomous natural conversation.

## Next bounded semantic screen

Request up to $0.10 and five Luna calls, no retries, separate from exhausted prior ledgers. Feed the five exported request states once each. Predeclare decisions: contribute, silence, silence, contribute, silence. Review complete prerequisites/qualifiers, natural short wording and helpful timing, not just JSON or word count. Preserve raw sanitized results and replay them through the same service before selecting any behavioral changes. A failure stops promotion; diagnose and propose a bounded targeted iteration rather than changing expected results.

## Later physical check

Only after model validation and a separately funded capture setup, ask for founder readiness. Use one conversation lasting past the cooldown (about three minutes), with fictional seeded Cedar/Harbor context. Say the corresponding lines from `STEPS` in the replay, acknowledge the first reminder, wait through the cooldown, then raise the venue decision. Check visible ordinary messages, preserved draft, no repeated resolved reminder, and Quiet without stopping capture. Do not start recording or treat implementation approval as readiness. This document does not provision funds, seed the real account, extend the gate or authorize recording.

## Approved live-model screen result

Founder approved the separate $0.10/five-call allowance. All five calls completed with no retries or extra spending authorization. Isolated ledger `proactive-conversation-20260928-100/usage.sqlite` records five completed attempts, $0.10 conservative reservations (not invoice cost), 6,623 input tokens and 187 output tokens. Runtime quotas, prior ledgers and personal account data were not modified.

| Case | Real Luna decision | Review |
| --- | --- | --- |
| Missing Cedar prerequisite | Contribute, 197 characters | Preserves team agreement, basic flow, five people, before adding features, historical pending status and calendar waiting |
| Acknowledgment after cooldown | Silence | Does not repeat the settled plan |
| Venue facts already covered | Silence | Does not restate information already in the conversation |
| Newly joined participant proposes inaccessible room | Contribute, 133 characters | Flags stairs versus Mina’s step-free need before booking; no invented medical reason |
| Resolved Cedar topic revisited | Silence | Does not repeat the previous reminder |

All five decisions meet the predeclared expectations. Useful output examples:

> The Cedar team had agreed to test the basic recording flow with five people before adding features, and those tests hadn’t happened as of the note. Calendar integration was to wait until afterward.

> The upstairs room isn’t suitable for Mina: it has only stairs, and she needs step-free access. Please flag that before Joel books it.

The venue reminder does not restate the alternative first-floor room; it answers the immediate suitability question correctly. This screen is not proof of preserving every potentially useful detail in all scenarios. Provider duration was 1.12–1.99 seconds, not phone end-to-end latency. Message lengths meet the soft guide without truncation.

Replay each real response through the exact exported request using the predeclared synthetic conversation prefix, then verify validation, delivery/silence and reopened chat. Stop each replay at its real response so later synthetic history is not mislabeled as a closed-loop live conversation. Forty-four proactive tests pass using `PYTHONPATH=Backend python3 -m unittest discover -s Backend -p 'test_proactive*.py'`; no network in replay. Existing SQLite ResourceWarnings remain. The separate adversarial synthetic duplicate test still deliberately forces a duplicate to verify storage defense.

No production code or prompt change was needed: deployed v4 already passes this bounded screen. Phone UI and installed app remain unchanged. The allowance is exhausted. Real audio, natural timing, long-session usefulness, semantically equivalent evidence from other notes, and a fully model-generated multi-turn sequence remain unverified by this result. Next product check is the separately funded, readiness-gated physical conversation described above.
