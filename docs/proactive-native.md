# Proactive contributions: local native checkpoint

September 28, 2026. This is a verified local development slice, **not deployed or App Store ready**. The installed app and hosted startup do not enable it. The exact positioning remains **AI notes that proactively contribute to discussions**.

## Implemented path

Finalized capture passages → authenticated foreground socket → local prior-note discovery → bounded Luna decision/draft → source/lifecycle validation → durable assistant-only turn → ordinary main-chat bubble. Existing typed questions and composer drafts keep their own lifetime. There is no fabricated question, new conversation, author heading or suggestion card.

The native coordinator ignores interim-only changes, coalesces pending updates and requires fresh finalized content after backgrounding. Quiet stops further contributions without stopping capture. The backend preserves Quiet on reconnect, rejects revision rewinds, rechecks credentials before saving and cancels pending work on disconnect. Source deletion preserves already delivered text; original evidence remains the grounding for follow-ups while available. The new-message pill lets the user navigate to the contribution rather than forcing a scroll while reading.

Native execution currently requires a **Debug** build with `--proactive-qa` and a loopback relay. `Backend/hosted.py` does not construct the new service; `/proactive` remains unavailable unless explicitly injected. This prevents a merge from authorizing runtime spending or changing the installed experience. Runtime budget provisioning and a matching hosted/native rollout are still required.

## Verification

- 38 focused backend tests passed: policy, model contracts, durable service, authenticated socket, exact live-model replay, relay and existing companion service.
- Nine native XCTest cases passed using the compiled CoreTests bundle: coordinator, companion controller and actual companion socket. The new cases cover finalized-only input, late-message rejection after Quiet, fresh context after backgrounding, revision advancement and capture reset.
- iPhone 17 Pro simulator UI test exercised actual local service/storage with explicitly synthetic capture and model output: one ordinary agent message, preserved unsent draft, Quiet without stopping capture, and the new-message navigation control. Screenshot: [local native evidence](qa/proactive/ordinary-message.png).
- Mac and iPhone Simulator targets compiled. Shared iPhone context-menu preview shapes now have platform guards because those APIs are unavailable on Mac. The existing companion socket test's stale error-copy expectation was updated to match the already shipped friendly wording.
- Mac UI automation initialization timed out. A subsequent Xcode native-unit launch stalled in debugger setup; the same compiled targeted tests passed directly under `xctest`. Do not claim Mac UI acceptance from those results. Simulator test teardown takes roughly two minutes in this environment after the interaction assertions.

The original native QA used no new inference or transcription calls. The subsequent retrieved-evidence semantic screen brings cumulative feature QA to seven calls and $0.11 conservatively reserved. See [provider evidence and limitations](proactive-model-screen.md). Existing historical retained-memory exact replay still has the separate prompt/fixture mismatch recorded in [backend evidence](proactive-foundation.md).

Reproduce backend checks with `PYTHONPATH=Backend python3 -m unittest Backend.test_proactive_policy Backend.test_proactive_models Backend.test_proactive_service Backend.test_proactive_socket Backend.test_proactive_live_screen Backend.test_relay Backend.test_companion_service -q`. Run `Backend/companion_fixture.py <new-temp-directory> --ui --proactive`, pass its isolated config as `TEST_RUNNER_VOICE_MEMORY_UI_CONFIG` to the Phone scheme, and select `PhoneUITests/ProactiveUITests`. Never substitute production recordings or credentials for this synthetic fixture.

## Remaining before rollout

Continuous-speech timing and relevance need stronger evidence; a new finalized revision deliberately cancels old analysis and may reduce opportunities during uninterrupted speech. A subsequent three-case screen verified silence for retrieved wrong-person, fictional-example and instruction-bearing notes; it is not broad accuracy evidence. Study connections and corrected/obsolete claims still need live-model evidence. Repeated-connection suppression is deliberately conservative and can miss a second useful fact from the same passage.

A real iPhone conversation, foreground/background transitions, stop/reopen and perceived usefulness still require a separately scheduled consented check. Before that check, prepare the runtime allowance and matching deployment, verify available transcription capacity, explain the short steps and wait for founder readiness. The $0.25 model QA grant does not authorize ongoing runtime usage, new paid transcription or deployment. Calendar/email/messages, outside knowledge and locked-screen proactive delivery remain outside this slice.
