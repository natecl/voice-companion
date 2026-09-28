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

## Physical run findings — September 28

Both founder-played video recordings completed and both generated notes are ready. Read-only hosted inspection found two registered captures. First capture had 12 silence outcomes and no paid proactive evaluations. Second capture had three silence, two cancelled and one unavailable outcome; no contribution was stored. Five additional Luna reservations were consumed: three completed responses and two uncertain/cancelled requests. The shared grant is now at 12 calls and $0.21 reserved, so its call ceiling is exhausted despite remaining monetary headroom. No retry is authorized by this result.

Saved source review confirms the first excerpt discusses an AI participant and Proven/Better/New; the second discusses inference costs, continuous listening and free consumer products. This establishes topical connection, not that an unsolicited message would have been useful at a particular moment. Exact live request packets and model outputs were not retained; the three silence decisions cannot be fully audited from the final transcript.

Code inspection and a local policy reproduction found:

- Any changed source digest invalidates the pending lease, even an append-only additional sentence. The socket cancels that job. Thus ordinary ongoing speech can discard a paid in-flight analysis. The two recorded cancellations are consistent with this mechanism, but the ledger does not retain their precise lifecycle cause.
- Context is selected by the last eight passages, then rejected if its serialized size exceeds 5,000 bytes. The second saved transcript's eight passages serialize to 5,331 bytes, with individual passages of 1,882 and 1,739 characters. The final saved form therefore deterministically exceeds the limit. We cannot prove this caused the historical unavailable result: budget exhaustion is another possible cause, and the terminal reason is not stored.
- A generic unavailable event sets the native coordinator's unavailable flag for the remainder of the capture. A transient oversized window can therefore disable subsequent evaluation. This is code evidence, not a separate observed phone event.

Recommended next bounded fix: retain reason-coded, content-minimal diagnostics; build a size-bounded recent context window with valid original offsets; distinguish appended speech from revisions to evidence used by a pending analysis while retaining stop/background/correction invalidation and freshness checks. Verify with synthetic continuous-speech replay before requesting another paid physical test. Do not increase limits or weaken evidence validation as a shortcut.

No new model/transcription calls, device access, hosted changes or recording retries were used in this investigation. Physical capture/notes succeeded; proactive usefulness remains unverified and no message was delivered. UI formatting/speaker repairs are separate merged checkpoints.
