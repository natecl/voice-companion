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
