# Bounded physical proactive test

September 28, 2026. Setup checkpoint; real-microphone usefulness is **pending**.

The founder approved $0.09 additional funding: two recordings and two generated notes. Five Luna calls remain in the original separate proactive grant ($0.25/12 calls; seven already used). Failed/cancelled calls remain charged; no automatic paid retries. Existing runtime charges remain intact. The operator script provisions the explicit extension; startup cannot create funding.

The server reads an operator-only `proactive-phone-qa.json`, requiring the existing account, a window no longer than 24 hours, and an existing capture registry. Only two distinct captures can register. Proactive retrieval is restricted to these captures, excluding the live capture; existing private notes cannot contaminate this video experiment. Test recordings remain available as transcripts/notes but do not enqueue personal-memory learning. The existing grant ledger enforces the shared 12-call and $0.25 ceilings across the earlier model screen and this phone test.

The native Debug launch argument `--proactive-phone-qa` enables the real hosted connection. It is deliberately different from `--proactive-qa`, which selects synthetic local audio. Release builds remain unchanged. Expiry rejects new proactive work; the ordinary recording budget and five-minute capture limit remain authoritative. Quiet, disconnect, revision changes and backgrounding still invalidate pending contributions.

## Founder-run check, after setup and explicit readiness

1. Keep the app foregrounded. Start capture and play 7:14–11:42 of the Mark Pincus/Garry Tan video `oHwUD9b9_pg` (4m28s). Stop and wait for the note to finish.
2. Start a second capture and play 35:40–39:44 (4m04s). Watch for an ordinary agent message connecting the cost discussion to the first recording, without sending a question.
3. Inspect relevance, attribution, novelty, timing and silence. A contribution is not guaranteed; forced commentary would be a failed test. Do not replay or extend paid runs without checking the remaining allowance.

Do not preload the video's full transcript. The two captured excerpts are third-party source material, not personal facts or instructions. The app must not claim the speakers' statements are the founder's experiences.

## Setup verification

48 focused backend checks passed before delivery, including a real local authenticated WebSocket round trip with a synthetic model. The phone test gate is checked for wrong-owner rejection, two-capture limit, expiry, duplicate calls, the five remaining calls and no-refund accounting. Source persistence without a learning job and unchanged normal learning are checked. Explicit $0.09 provisioning preserves historical request rows and is idempotent at the accounting layer.

Continuous speech remains an unresolved acceptance question: new finalized revisions cancel old analysis, so uninterrupted audio can yield no contribution. Do not report this setup checkpoint as physical proactive acceptance. Deployment and signed-device build evidence will be recorded after completion.

Signed generic-iPhone Debug build succeeded (`Phone`, iOS SDK 26.5, team configured locally). An actual local WebSocket check through the new phone gate registered prior/live captures, produced one synthetic contribution as an ordinary stored turn, and consumed exactly one fixture-ledger reservation. No paid provider calls were used for this setup QA.

## Internal setup deployed

Merged PR [115](https://github.com/natecl/voice-companion/pull/115), commit `ca8b1f103f71b678ca1c320f0bd5770f4b9d0811`, is internally deployed. Render reported live; general, notes and learning health checks succeeded. The signed Debug app is installed and launched on the physical iPhone 16 Pro with the real-audio test argument. The gate expires September 29 around 13:25 America/New_York.

Twenty databases were backed up before explicit provisioning. A copied-ledger dry run validated startup and the notes allowance first. Post-deployment checks covered 104 historical tables and preserved prior charges. One note deletion synced after app launch; its acknowledged device-outbox deletion was inspected, and its expected source/notes lifecycle changes were excluded explicitly from the preservation comparison. Other historical rows were preserved. Seven prior proactive calls/$0.11 reserved remain unchanged; no new provider calls or test captures ran during setup. The additional $0.09 allowance is provisioned.

Physical capture, usefulness and continuous-speech timing remain unverified. Awaiting the founder's explicit readiness before the first excerpt; do not label the setup as a completed proactive test.
