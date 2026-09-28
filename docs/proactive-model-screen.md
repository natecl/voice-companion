# Proactive model screen — September 28, 2026

The first small screen favors the one-call Luna route. It is a provisional implementation choice, not proof of broad conversation quality. Preserve the frozen Jev thresholds; do not tune them on the missed positive.

| Frozen case | Luna decision/draft | Jev then draft | Interpretation |
| --- | --- | --- | --- |
| Alex's prior sleep concern relevant now | Contributed a qualified, supported reminder; 2.96 s | Silence; 0.30 s | Jev novelty probability .85 fell below the predeclared .90 threshold, despite `new` being the top label. No draft call. |
| Concern already discussed | Silence; 2.03 s | Silence; 0.19 s | Both avoided repeating the concern. |
| Maya's sleep, only Alex's old note | Local retrieval empty, no model call | Same | Correct pipeline silence; this does **not** measure either model's wrong-person judgment. |

Actual positive output: “Earlier, Alex said they had been waking up at three every morning that week; that may be worth mentioning to the doctor.” It preserves Alex as the subject, uses qualified timing, adds no diagnosis and does not turn the statement into an account-owner fact. The source and current conversation are synthetic; no user recording was transmitted.

Four live calls total: two Luna, two Jev. Conservative reservations: **$0.05 of $0.25**, leaving $0.20 and eight calls in the authorization, but unused calls are not a reason to spend. Luna usage 1,128 input / 74 output; Jev 1,570 input / 162 output. Stored provider time excludes SSH overhead, retrieval and native rendering. No transcription calls or runtime quota changes.

The separate operator ledger is `/var/data/voice-companion/proactive-20260928-025/usage.sqlite`; reservations remain charged after failure. Requests are at most 16 KB and Luna output at most 600 tokens, with conservative $0.02/Luna and $0.005/Jev reservations. Reference prices checked September 28: [Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [TypeSafe API](https://docs.typesafe.ai/api). Exact request/response evidence is under `Backend/fixtures/proactive/live-screen-20260928`.

The runner initially stopped before the third case because it assumed local retrieval would return evidence. Inspection showed legitimate empty retrieval. It was corrected to record local silence, and resumed with the four exact cached responses—no provider retry or additional call. Cases, prompts and thresholds did not change.

`PYTHONPATH=Backend python3 -m unittest Backend.test_proactive_live_screen -v` replays all six route/case results through the durable service with exact request equality, original evidence storage and message persistence. No network fallback exists. This verifies that the real provider responses integrate with the service, independently of native or physical acceptance.

Remaining evidence: richer prior-note retrieval, model-level wrong-person/quoted-example/injection negatives when candidates are supplied, corrections, sustained speech timing, native lifecycle/control, and physical usefulness. Runtime remains disabled. Native integration should use Luna provisionally behind the rollout gate; Jev has not demonstrated enough value for an added runtime call in this screen.
