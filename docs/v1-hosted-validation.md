# V1 hosted recording evidence

> Historical first hosted rollout. Commit, health, enrollment and ledger figures below are observations from that run, not current deployment or authorization to provision/spend again. See [current state](current-state.md) for selected behavior and current evidence boundaries.

September 24, 2026; implementation commit `381d243`. Internal trial only.

Render service `srv-daqtfs7lot8c73dleuug`, Virginia Starter, one instance, 1 GB disk, automatic deploys/previews disabled. Deployment `dep-daqtfsnlot8c73dlf0tg` is live at that commit. HTTPS `/health` returned 200. The founder approved approximately $7.25/month hosting and $5 total provider testing. The current ledger enables only STT with a $2 allocation and $0.02 permanent reservation per attempt.

The signed iPhone build installed on the physical iPhone 16 Pro. Paired-device provisioning transferred the app credential; the founder confirmed the encrypted connection-check banner. A subsequent normal launch used Keychain. Device Documents listing after recording contains only the old development configuration, not the hosted transfer file: successful secure storage removes that transfer file. Hosted requests below independently confirm the hosted configuration was used, without relying on the Mac relay.

## Actual microphone sessions

The founder reported speaking into the phone, explicitly tapping Stop, leaving/reopening the app, and seeing the saved transcript. They repeated the recording successfully. Server logs and copied local session metadata independently establish:

| Started (UTC September 25) | Server audio seconds | Saved state | Transcript segments |
| --- | --- | --- | --- |
| 02:26:51 | 24.3871 | completed, microphone, no end error | 1 |
| 02:29:16 | 23.1964 | completed, microphone, no end error | 4 |

Server request IDs: `9652d3ae-399c-4ecf-8002-7eed649a363f` and `bc2172c8-f0de-4310-8b47-5b2cb66c9227`. Both ended completed. This verifies successive actual recording and local saving through the hosted path; it does not verify background recording, transcript accuracy, or measured first-text latency.

An additional earlier completed server request, `900601e4-bb23-42f3-b35f-5466ac5dc2ae`, carried 47.9918 seconds. It was not among the two newest saved sessions inspected; do not claim its local persistence. All three logged calls total about 95.5753 audio seconds and $0.00531 estimated STT cost, not verified billing. The remote ledger was inspected after a hosted invalid-credential probe: exactly three STT reservations totaling $0.06, with no additional reservation from the rejected probe.

## Local evidence and remaining review

16 backend tests passed, including real local WebSockets with synthetic upstream, SQLite concurrency/restart budgets, revocation during streaming/finalization, credential export permissions, and real service-process locking. Two targeted native configuration tests passed; signed iPhone build passed. Logs and copied private session data remain ignored under `work/`; private transcript text is not committed.

The server logs also contain rejected HEAD handshake diagnostics. No recording failure is associated with them; do not hide them or count them as transcription failures. Final review added explicit access, daily-limit, budget-limit, busy, and authorization-unavailable messages. Real local URLSession WebSockets exercised all five pre-capture rejections and HTTP 401, through the production controller and store. The selected native suite ran 17 tests: 16 passed and the existing opt-in 90-second test was skipped. Hosted invalid credentials returned HTTP 401 without an added reservation. Signed iPhone rebuild passed. The final change affects native error presentation and a local fixture only; prior real hosted success evidence remains applicable, so no additional paid recording was performed. Ask/Luna/Jev and background capture are not implemented by this checkpoint.
