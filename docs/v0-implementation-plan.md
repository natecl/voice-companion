# V0 implementation plan

Status: Implementation authorized September 24, 2026. Foundation build, launch, and navigation verified on Mac, iPhone Simulator, and a physical iPhone. See development.md for evidence; transcription work remains pending.

Authority: [product source of truth](product-source-of-truth.md), [V0 scope](v0-scope.md), and [canonical engineering principles](engineering-principles.md). This plan implements those decisions without replacing them. Proven remains Granola.

## Outcome

On Mac and iPhone: start microphone capture, see a live speaker-labeled transcript, stop, and reopen the saved transcript.

Exclude computer audio, AI notes, Q&A, Jev, memory, and AI participation. Proposed additional limits for this first development slice: local transcript storage without sync, foreground recording only, and an internal test build rather than public subscription launch. Freemium plus subscription remains the business direction; billing and public distribution are separate work. Validate foreground behavior with the founder before treating it as a lasting product restriction.

## Execution discipline

Apply [fast iteration on verified foundations](engineering-principles.md#fast-iteration-on-verified-foundations) throughout. Phases may be split into smaller PR checkpoints with explicit acceptance criteria and complete behavior within their bounded scope. Keep feedback cycles short; do not skip QA for speed or build dependent work on unexplained failures. Each merged checkpoint should leave a known working baseline and enough evidence to reproduce and debug its behavior.

## 1. Prove the engineering workflow

Inspect the installed development tools and signing/device access. Validate Swift/SwiftUI with a minimal app that builds for Mac and iPhone Simulator, launches, exposes accessible UI controls, and produces inspectable logs. Check physical-iPhone installation early so signing cannot become a late surprise.

Research current official documentation for the tools needed to build, launch, inspect the UI, collect logs, and run tests. Choose minimum OS versions and project organization based on supported APIs and device availability. Record evidence and limitations; do not assume simulator success proves microphone behavior on hardware.

Deliver repeatable commands for setup, build, test, and fixture replay, with documented prerequisites. Use Xcode's tooling as the initial baseline; add dependencies only when they materially improve the agent feedback loop.

Exit: an agent can change a visible element, build, launch, inspect the result, and run a check without the founder relaying commands or errors. Record any unavoidable device or signing step requiring the founder.

## 2. Validate the transcription provider

Recheck the [candidate documentation](transcription-direction.md), including actual availability, streaming speaker labels, finalization, supported audio formats, authentication, retention, pricing, and quotas. Grok Voice Transcribe 2.0 is provisional; compare Muse if accessible. Do not block indefinitely on access to a comparison provider.

Use a small, versioned set of consented or synthetic audio with reference text and speaker turns: single speaker, two speakers taking turns, noisy speech, specialist vocabulary, and some overlap. Keep a held-out sample for the final check. Document fixture provenance.

Measure word error rate, speaker attribution errors, time to first useful text and final text, revision behavior, connection failures, and actual billed usage. Document measurement definitions, test conditions, and sample limitations. Establish numerical acceptance targets before the final evaluation rather than inventing guarantees now or moving targets after seeing results.

Choose one provider and one integration path. Prefer short-lived client authorization if supported; otherwise use a backend relay. Keep provider secrets server-side. Determine the smallest backend runtime from this requirement and the same agent-tooling criteria; do not choose it prematurely.

Exit: a replayed audio sample produces timestamped speaker-labeled results through the selected integration, with a recorded decision and explicit quality limitations. If live diarization is unavailable, resolve that requirement before building around the provider.

## 3. Build the shared transcript flow with simulated input

Create a shared session model and a small number of explicit boundaries:

- Audio source: audio frames and capture lifecycle; platform-specific implementations.
- Transcription adapter: converts provider messages into app-owned events.
- Session controller: recording, connecting, streaming, stopping, completed, and failed states.
- Transcript model: session/segment identity, timestamps, text, optional speaker, finality, and revisions.
- Session store: save and reopen transcript state.
- SwiftUI presentation: record/stop controls, status, live transcript, and saved sessions.

Use a simulated stream to exercise partial text, replacements, late speaker assignments, completion, and failure. Display unknown speakers honestly until labels arrive. Do not mistake a changed speaker label for a new transcript segment.

Exit: the UI can record a simulated session, apply revisions without duplicates, stop, save, and reopen it. Tests verify meaningful behavior such as replacement semantics and persistence, rather than mirroring internal functions. Modules can initially be folders and protocols within the same project; separate packages are optional.

## 4. Complete the live Mac path

Implement microphone permission, capture, and conversion to the provider's required format. Connect it to the shared flow and selected provider. Add only the backend session authorization and usage controls required for a bounded internal trial; do not expose an unrestricted paid API proxy.

Stop must end capture immediately, then request/await final results within a bounded timeout. Clearly distinguish a completed transcript from an incomplete saved session. Save updates incrementally so an unexpected termination does not discard the entire session.

Proposed storage policy: persist transcripts on device and avoid retaining raw audio by default. Decide temporary audio buffering and provider retention explicitly during integration; do not promise zero retention without evidence. Provide a basic way to delete saved sessions.

Exit: a real Mac microphone conversation appears live with speaker labels, finalizes, and reopens after relaunch. Check that recording and billable sessions actually stop.

## 5. Bring the same flow to iPhone

Reuse the transcript model, provider adapter, storage boundary, and appropriate SwiftUI views. Adapt microphone permission, audio routing, interruptions, and lifecycle behavior for iPhone.

For the proposed foreground-only slice, backgrounding or an interruption should safely stop capture and preserve available text with clear status. Do not imply continued recording when capture has ended. Validate the eventual background-recording requirement separately.

Exit: the complete flow works on a physical iPhone, including permission denial, an audio interruption, and leaving the app. Simulator tests support this but do not replace device evidence.

## 6. Verify and package the internal V0

Run automated regression checks and repeat the held-out audio evaluation. Test the interface on Mac and iPhone; perform a longer recording to observe resource usage and transcript growth. Record actual latency, speaker quality, and any remaining limitations.

| Scenario | Expected behavior |
| --- | --- |
| Partial text or speaker reassignment | Existing text is revised without duplication |
| Permission denied | No recording; actionable status and retry path |
| Network loss or provider error | Recording/connection state is explicit; received text preserved; any missing audio is disclosed |
| Stop during connection or finalization | Capture ends; bounded cleanup; no orphaned paid session |
| Silence or empty session | No fabricated transcript or stuck recording state |
| App interruption or termination | Saved text remains recoverable; incomplete session is identified |
| Reopen and delete | Saved transcript survives relaunch and can be removed |
| Provider credentials | No long-lived provider key in app source, build artifacts, or logs |

Do not promise seamless reconnection in this slice. A safe explicit stop and retry is acceptable if documented; automatic recovery must not silently omit or duplicate speech.

Deliver runnable Mac and iPhone development builds, repeatable commands, a short setup/runbook, evaluation results, and a list of known limitations. Public release, subscription billing, and cross-device sync require subsequent planning.

## Founder-dependent blockers

Follow the canonical [stop-and-wait rule](engineering-principles.md#stop-for-founder-dependent-blockers). When founder action is required, stop execution, explain precisely what is needed, and wait. Do not move to another phase or replace the blocked behavior with a workaround. Resume once the founder responds and the prerequisite is satisfied.

## Human involvement and decision records

Agents own routine setup, implementation, command execution, debugging, inspection, and regression checks. Involve the founder when needed for unavailable credentials/signing access, a material product tradeoff, or targeted real-device experience feedback. Record technical decisions and evidence in the repository so future work does not reopen settled questions without reason.

Milestones are verification gates, not repeated permission gates. This document is a plan, not a claim that implementation or deployment has been authorized or completed.

## Phase and checkpoint PRs

Open a focused PR at the end of each phase or meaningful checkpoint, following the [canonical checkpoint workflow](engineering-principles.md#pull-request-checkpoints). Include the tested commit, checks performed, outcome, known limitations, and any dependency on an earlier unmerged PR. Keep documentation aligned with implementation evidence. The founder authorizes merging each verified checkpoint after checks, behavioral QA, and review. Start the next phase from verified main; involve the founder for material unresolved issues rather than routine merge permission.

Every checkpoint must follow [behavioral QA requirements](engineering-principles.md#behavioral-qa-at-every-checkpoint). Demonstrate actual input-to-output behavior and record the tested commit, environment, steps, expected/observed results, and evidence. Mocked tests supplement but do not prove real transcription, microphone capture, or device behavior. A missing prerequisite leaves the relevant checkpoint unverified.

## Definition of done

Both platforms perform microphone -> live transcript with diarization -> stop/finalize -> local reopen. The selected provider meets the documented evaluation targets or any shortfall is explicitly resolved. Failure paths preserve received text and expose incomplete sessions. Agents can reproduce the core checks, and a physical iPhone has been tested. No Better or New features are required to finish this slice.
