# Proactive foundation checkpoint

September 28, 2026. Implements the first bounded portion of the [plan](proactive-contributions-plan.md): scheduling, local evidence preparation, provider request/output contracts and seven frozen synthetic cases. It is not wired into the hosted service or native app yet. No migration, deployment, live provider call or microphone use occurs here.

- `Backend/proactive_policy.py`: stable-cutoff attempts, one pending lease, cooldown, deadline, attempt cap, duplicate keys and invalidation on revision/Quiet/Stop/background/owner change. This is in-memory policy, not durable reconnect handling; integration must persist delivery identity and session state.
- `Backend/proactive_context.py`: existing owner-scoped local note/transcript/retained discovery with current capture excluded, original evidence and required correction expansion. No paid Jev ranking. Oversized context rejects rather than dropping known corrections.
- `Backend/proactive_models.py` and `prompts/proactive-v1.md`: Luna silence-or-contribution schema and optional batched Jev relevance/novelty judgments. No forced contribution. Thresholds are unvalidated hypotheses, not performance claims. Output ID validation does not prove factual entailment.
- `Backend/fixtures/proactive/cases.json`: relevance, already-addressed, wrong-person, study, unrelated, fictional example and instruction-in-source cases. Expected labels/rubrics never enter model input. These are frozen for forthcoming evaluation, not model-passing results.

## Verification

Run from repository root:

```sh
PYTHONPATH=Backend python3 -m unittest Backend/test_proactive_policy.py Backend/test_proactive_models.py -v
PYTHONPATH=Backend python3 scripts/evaluations/proactive_replay.py
```

Twelve focused tests pass. The executable replay uses actual isolated SQLite storage and local discovery, then a clearly labeled synthetic draft through output validation and scheduling. Observed: one contribution with `prior` provenance; repeated cutoff suppressed; Quiet rejects pending delivery; another owner gets no source. JSON output explicitly says no audio/model calls and no chat persistence integration. Reviewed source and `git diff --check` passed.

Current official contracts were checked before adapter construction: [Responses structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs) and [TypeSafe API](https://docs.typesafe.ai/api). Existing nonretrying transports can execute these request contracts later; this checkpoint calls neither.

## Remaining gates

Durable contribution persistence without a phantom user turn; authenticated service and cancel/revalidation protocol; budgeted live model comparison; native event wiring and ordinary agent-message rendering; physical-iPhone acceptance and separately authorized rollout. The approved $0.25 / 12-call grant remains unused. Do not infer active proactivity or natural-language quality from local replay success.

## Durable service checkpoint — September 28

`proactive_service.py` now runs bounded local discovery, optional Jev judgment, Luna drafting, revalidation and atomic persistence behind an internal interface. It is **not enabled in hosted routing or the app**. Contribution turns have `kind=proactive`, no fabricated user prompt, and retain original evidence for subsequent ordinary questions. Durable attempt/connection keys prevent repeated payment for a replayed cutoff and duplicate messages; interrupted attempts remain terminal for retry purposes. A pending normal Ask prevents contribution persistence. Source deletion preserves delivered text while excluding unavailable evidence from subsequent context.

Verification:

- 77 targeted tests passed: proactive policy/models/service, chat/context/snapshots, memory, retention unit cases and recording notes.
- `PYTHONPATH=Backend python3 scripts/evaluations/proactive_service_replay.py` exercised actual localhost WebSockets, isolated SQLite persistence/reopen, duplicate requests, owner isolation, follow-up evidence assembly and deletion. One explicitly synthetic model response; zero external/paid calls. This harness does not establish hosted authentication or native capture behavior.
- The broader run also exposed `RecordedRetentionAcceptance.test_exact_provider_replay_through_companion_sockets`: its historical saved response expects an older companion instruction string. The current committed prompt has since changed persona and hidden-citation wording; exact replay rejects the unmatched request. This change does not alter that prompt or replace the saved response. Do not describe that historical provider acceptance check as passing.

Schema 19 adds contribution kind and attempt/connection bookkeeping. Existing replies default to `reply`. Rollback must retain schema-19-compatible code and disable contribution execution; an older schema-18 binary cannot open the migrated database. No production database has been migrated by this checkpoint. Provider quality, cadence under continuous speech, hosted lifecycle authorization, native rendering, live model comparison and physical acceptance remain unverified.
