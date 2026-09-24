# Five-minute recording checkpoint

Status: implementation in progress; real five-minute microphone/provider acceptance is pending. Do not mark this checkpoint complete or merge it until the live check passes.

## Behavior and bounds

The founder authorized five-minute development recordings on September 24, 2026. The shared app capture deadline is now 300 seconds. The relay allows 310 audio seconds, one upstream connection attempt per process, and a 330-second wall timeout. The client resource timeout is 345 seconds; the existing 10-second readiness and 12-second finalization deadlines still govern visible failures. The relay still gives finalization 10 seconds after audio.done. No automatic retries. Raw microphone audio is not retained.

The recording status and Stop button remain fixed below the scrolling transcript, so transcript growth cannot push Stop offscreen. The first safe-area-inset implementation failed Mac hit-testing; an explicit sibling footer passed on Mac and physical iPhone.

The current [xAI model page](https://docs.x.ai/developers/models/speech-to-text), checked September 24, lists streaming at $0.20/hour. Five minutes is approximately $0.0167; the 310-second relay ceiling is approximately $0.0173. These are estimates, not verified billing. The [streaming guide](https://docs.x.ai/developers/model-capabilities/audio/speech-to-text) describes binary frames and audio.done; documentation alone does not establish long-session reliability.

## Local evidence

- Four real-socket relay checks passed with a fake local upstream: authentication and one-attempt quota, full 310-second PCM byte allowance, rejection of one excess sample before forwarding, and bounded wall-time cleanup. Byte accounting is accelerated, not a five-minute soak. Log: `work/five-minute-relay-tests.log`.
- Four Foundation UI checks passed on Mac and physical iPhone, including 60 simulated turns spanning 300 transcript seconds, a visible/hittable Stop button, Saved, relaunch, and all 60 turns retained. This is accelerated transcript-volume evidence, not real five-minute audio. Logs: `work/five-minute-mac-ui-final.log`, `work/five-minute-phone-ui-final.log`; screenshots exported under `work/five-minute-*-shots`.
- The initial Mac core run passed 21 tests. The expanded transport run passed all 12 checks, including the opt-in 90-second real local WebSocket check across the previous resource-timeout boundary (90.165 seconds, finalized and saved). Evidence: `work/five-minute-transport.log`.
- Final signed Mac and iPhone builds passed. The phone build is installed and its encrypted relay health check passed without a provider call. A three-second Activity Monitor attachment to the idle phone app succeeded, preparing CPU/memory observation for live QA. Generated artifacts and local QA data remain ignored.

To reproduce the 90-second check, set `TEST_RUNNER_VOICE_LONG_SESSION_CHECK=1` and `TEST_RUNNER_VOICE_TEST_PYTHON` when invoking xcodebuild with `-only-testing:CoreTests/TransportFailureTests/testConnectionSurvivesFormerResourceDeadline`. It is skipped in default checks to avoid adding 90 seconds to unrelated changes.

## Required live check

Wait for explicit founder readiness. Use one continuous five-minute playback from the previously supplied YouTube video, starting at 3:09, through computer speakers into the physical iPhone microphone. Keep the app foreground and do not seek or pause playback. Start capture only after the founder is ready. Let the app reach its five-minute automatic stop, then inspect Saved and the limit explanation. Monitor process CPU/memory with a bounded Instruments trace if the profiling preflight succeeds; do not call this a battery-life benchmark.

Retrieve the saved session, inspect timestamp continuity and speaker labels near the beginning/middle/end against the source, and independently verify reopen after relaunch. Confirm no duplicate chunks, no unexpected cutoff, received text retained, completion after automatic stop, and the relay closed within its limits. Record actual duration, finalization delay, resource observations, and limitations. If exact audio boundaries/reference speaker turns are unavailable, do not claim WER or diarization error rates.

One live run is authorized for this checkpoint, with no automatic retry. A failed attempt remains failed and requires diagnosis before another paid run. The current development relay must be restarted explicitly for any additional attempt, with its new token copied to the phone.
