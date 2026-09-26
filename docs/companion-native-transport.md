# Shared native companion connection

September 26, 2026. This checkpoint adds the shared Swift transport; it does not enable the hosted route or replace the current app interface.

`CompanionSocketConnection` uses the existing relay credential and TLS configuration at `/companion`. Requests preserve a stable question ID and immutable context. Missing attachments/live captures encode as explicit nulls. History is server-owned; the client sends no assistant history. There are no automatic retries or new paid requests on reconnection.

Accepted/context/delta/done ordering is checked before presentation receives events. A completed stream requires the correct question ID, valid source references and an explicit saved acknowledgment. A duplicate returns its existing durable state. Cancellation closes the socket; a 25-second bound covers stalled service connections. A connection remains busy until its previous operation unwinds, including after cancellation.

The live cutoff copies interim and finalized transcript segments with their original passage IDs. It remains distinct from durable memory synchronization, which still includes only finalized segments. Speaker labels remain anonymous. A later transcription revision can conservatively invalidate a cited snapshot; no identity inference is added here.

## Verification

Run the Mac scheme with `-only-testing:CoreTests/CompanionConnectionTests -only-testing:CoreTests/MemoryTests`, setting `TEST_RUNNER_VOICE_TEST_PYTHON` to a Python with backend dependencies installed. `Backend/companion_fixture.py` launches the actual authenticated CompanionService and SQLite store with a synthetic streaming provider. The native URLSession client sends a question, receives text and save acknowledgment, repeats the same request, reopens history from a new client, sends a live interim snapshot, and reads its durable citation. A stalled answer is cancelled without completion. The adjacent memory tests exercise the unchanged sync lifecycle over a real socket, including save/restart/delete.

Expected receipt: `Companion socket QA: stream/save, duplicate recovery, reopened history, frozen live citation, cancellation verified`. Additional checks reject out-of-order deltas, false save completion, nonexistent citations and overlong Unicode input. The Phone simulator target builds from the same source. No provider API calls or microphone capture are needed for this changed boundary.

This is transport evidence, not UI, physical-iPhone or hosted rollout acceptance. Main chat/library presentation, source navigation and deployment remain subsequent checkpoints.
