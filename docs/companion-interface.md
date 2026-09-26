# Companion and recording-library interface

September 26, 2026. Opt in with `--companion-ui`; normal installed behavior remains unchanged until the matching hosted rollout is approved.

The main Companion view has ongoing server-owned history, a draft, explicit recording attachment and bounded memory preference. The Recordings view preserves transcripts and legacy personal-note access/deletion. Separate selection state means opening a past recording or citation never replaces the active capture. Both surfaces stay mounted to preserve reading position during navigation. Capture/stop controls stay available across both. The mobile keyboard dismisses on Send or opening Recordings.

“Ask about this” requires an owner-matching acknowledged source revision; an unsynced recording is not presented as server-ready. Questions during capture include a frozen received transcript cutoff. Source buttons read the exact authenticated saved evidence, show its original timestamp/excerpt and open the corresponding recording when available locally. A missing local recording is explained without hiding the fetched cited excerpt. The app does not invent a replacement for deleted/unavailable evidence.

Deleting a source clears local companion-derived display immediately and temporarily blocks chat while its tombstone is pending synchronization. After acknowledgment, history reloads from the server with affected answers invalidated. This avoids asking against a source the user has just deleted while offline. Capture remains independent. An in-flight source read is cancelled on deletion/backgrounding; cancelled responses cannot reopen deleted evidence.

This is functional navigation, not a visual redesign. No summaries, note editor, voice identity, voice replies or side chats are added. Separate personal-note creation is absent from this opt-in interface; legacy data remains accessible. General microphone and background behavior is unchanged and still needs the final physical capture-plus-chat check.

## Behavioral evidence

Mac: `MacUITests/CompanionUITests` launches the actual app, a local CompanionService/MemoryService and SQLite store. Synthetic capture keeps adding transcript text while synthetic streamed answers run. The test asks during capture, verifies capture is still active and growing, opens a frozen source, returns to an unchanged draft, stops/synchronizes, attaches the saved recording, sends a follow-up, removes the attachment, relaunches, reopens the source and deletes it. Both dependent answers disappear and show invalidated states. Fourteen adjacent native controller/connection/memory tests also pass, including deletion of a past recording without changing the active capture and rejection of unacknowledged attachments.

Phone simulator: `PhoneUITests/CompanionPhoneUITests` exercises capture, chat, exact citation, return navigation, stop, saved attachment/removal and restored history after relaunch through the same local service. Run the fixture externally (`python3 Backend/companion_fixture.py <private temporary directory> --ui`) and pass its config through `TEST_RUNNER_VOICE_MEMORY_UI_CONFIG`. The fixture contains no real credentials and cannot call paid providers. Mac tests provision their own unique local fixture automatically. Set `TEST_RUNNER_VOICE_TEST_PYTHON` for the Mac runner.

Failed runs are preserved in local Xcode results: automation startup initially timed out before app execution; a Mac static-text assertion read the label instead of value; navigation testing exposed actions below the fold, which were moved above excerpts/transcripts; the Mac segmented picker test needed its native radio-button accessibility role. None were counted as acceptance. Final runs exercise the complete flow; no STT or paid model calls were made.

Physical iPhone, hosted runtime wiring, migration, deployment and final acceptance remain pending. The local synthetic provider verifies transport/state/navigation, not new model quality; prior live service evidence remains applicable to its unchanged model boundary.
