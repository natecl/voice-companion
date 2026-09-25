# Voice Companion backend

The repository contains a local development relay and a deployed internal hosted service. The first section describes the local relay; see the V1 hosted section below for the current phone service. Python 3.11+ and websockets 15.0.1 are required (`python3 -m pip install -r Backend/requirements.txt` in your chosen virtual environment).

Run `python3 Backend/relay.py` from the repository. It reads the ignored `.env`, binds only 127.0.0.1:8766, and writes a short-lived random client credential to `work/relay-client.json` with owner-only permissions. Quit with Ctrl-C; the client configuration is removed. The provider key never enters the native app. Do not expose this process publicly.

Build with `DEVELOPMENT_TEAM=<team> scripts/check.sh mac build`, then launch the built app with `--relay-config <absolute-path-to-work/relay-client.json>`. Use a stable development signing identity for microphone permission. The app asks for microphone access and only starts capture when recording is requested.

Limits: one active session and one upstream connection attempt per relay process, 310 audio seconds per session/process, and a 330-second server timeout. The app auto-stops at 300 seconds (five minutes); the extra relay allowance covers capture scheduling and queued frames, followed by bounded finalization. Restarting the relay is an explicit new testing budget, not an automatic retry. No automatic retries. Logs contain duration/status/estimated cost, not transcript text or raw audio. No raw audio is retained. Estimates are not verified invoices.

Run `python3 -m unittest discover -s Backend -p 'test_*.py'` for a real-socket local test with a fake upstream. It verifies unauthorized clients never reach the provider, authorized frames/finalization are forwarded, connections clean up, the session cap rejects new calls, the full 310-second PCM byte budget can finalize, an extra sample is rejected before forwarding, and the wall timeout closes the connection. Full-budget bytes are sent quickly to a local fake provider; this is accounting evidence, not a five-minute provider soak test. It makes no external API calls.

Client authentication appropriate for distribution, provider retention review, and production usage accounting remain separate requirements. xAI currently documents short-lived tokens for its speech-to-speech API, not this STT endpoint; do not assume those tokens work for transcription.

## Physical iPhone development

Run `python3 Backend/prepare_lan.py` to generate a seven-day development certificate for the Mac's current en0 address. Then run `python3 Backend/relay.py --lan`. This retains loopback access and adds TLS on the specific local address at port 8767. Both listeners share the same token and usage limits. The phone and Mac must have network connectivity to that address.

Build/install the signed Phone target. Copy the generated client configuration using the paired device connection:

```sh
xcrun devicectl device copy to --device <device-id> --source work/relay-phone.json --destination Documents/relay-client.json --domain-type appDataContainer --domain-identifier ai.voicecompanion.phone
```

The configuration contains a random relay token and the public certificate, never the provider key. The app uses this certificate only as an anchor for its development URLSession, with hostname, chain, and expiry checks intact. It does not change system trust. Configuration loading is disabled outside DEBUG builds. The private key and all client configuration files remain ignored under work; token files and private key are owner-readable only. Restarting the relay rotates the token, so copy the new configuration again. Regenerate the certificate when the address changes or it expires, with the relay stopped first.

Launch with `--relay-check` to verify TLS reachability using `/health`, without audio capture or a provider call. Allow iOS Local Network access if prompted. The diagnostic banner describes only that check; relaunch normally before using the app for recording. `/health` exposes only a static readiness response and consumes no transcription quota.

This is a bounded internal development transport, not public hosting or production authentication. Do not expose the relay publicly.

## Local transport fault checks

`Backend/transport_fixture.py` is a test-only loopback server. It does not read `.env` or connect to xAI. Native `TransportFailureTests` launch it on an ephemeral port and exercise the production URLSession WebSocket adapter/controller/store using synthetic PCM and shortened timeout values. Scenarios cover abrupt socket loss, error events, rejected authorization, missing readiness/finalization, unexpected completion, capture-stream failure, cancellation, and normal explicit/automatic Stop. Server reports verify closure and whether any audio or audio.done arrived.

The Mac check script selects the current `python3` for these tests; it must have Backend/requirements.txt installed. Override with `VOICE_TEST_PYTHON=/absolute/path/to/python`. For direct xcodebuild calls, use `TEST_RUNNER_VOICE_TEST_PYTHON=/absolute/path/to/python`. Default microphone and paid-provider checks remain excluded. These transport tests require neither credentials nor microphone permission.

## V1 hosted service — internal founder trial

`hosted.py` adds persistent admission to the same relay. It requires `XAI_API_KEY`,
`VOICE_DATA_DIR` on a persistent disk, with the approved $5 total ledger and $2 STT allocation in `service_policy.py`.
STT and direct Luna Ask are enabled in the current service. Ask requires `VOICE_ENABLE_ASK=1` and `OPENAI_API_KEY`; policy migration preserves previous accounting. `PORT` defaults
to 10000. Run behind the hosting platform's TLS termination; never expose its
plain HTTP listener directly. No enrolled credentials exist on initial startup.

Each admitted attempt reserves $0.02 permanently, including failed attempts.
This is deliberately conservative authorization accounting, not billed usage.
Six attempts per UTC day and one active STT request globally are enforced in
SQLite. The stored policy cannot be increased by changing an environment
variable; that needs a reviewed migration. An exclusive process lock prevents
another hosted process using the same data directory from resetting active
reservations. Only the lock owner marks prior active requests interrupted on
startup. Keep one instance and one shared persistent directory.

Credentials generated by `Admission.enroll` expire within 30 days, default one
day; only hashes persist. No public enrollment endpoint exists. Keychain setup, administrative provisioning, and deployment configuration are implemented.
The dedicated internal service is deployed and physical-iPhone repeated-session QA passed; see `docs/v1-hosted-validation.md`.
Hosted connection setup times out after two seconds and rechecks authorization
before forwarding audio. Revocation is polled each second during streaming and
finalization. Successive physical-iPhone hosted sessions are verified; provider latency is not benchmarked. Database
errors deny new admission rather than bypassing it.

The local test suite now also exercises repeat sessions over real WebSockets,
revocation/disconnect cleanup, durable reservations after reopening SQLite,
concurrent admission, expiry, category/global quotas, and daily rollover. Its
provider is a local synthetic fixture; it makes no external inference calls.

### Internal provisioning

Use `render.yaml` for the single-instance Starter service with a 1 GB persistent disk.
The mounted data directory must exist; startup never creates a missing disk directory.
Auto-deploys are off. Deploy a tested commit outside active capture.

On the service instance, run `python Backend/admin.py enroll --url wss://<host>/stt --output /var/data/voice-companion/client.json --days 7`.
The command prints only the credential ID, used by `python Backend/admin.py revoke <id>`.
Transfer the 0600 export over authenticated SSH to an ignored local file, then delete the remote export.
For the DEBUG internal iPhone build, copy it through the paired-device connection to
`Documents/hosted-relay.json` and launch with `--relay-check`. The app validates and
saves the configuration in a device-only, non-synchronizing Keychain item, then deletes
the transfer file. Failed storage leaves the file for a deliberate retry. Delete the
local export after successful provisioning. Provider keys never enter this file.

Subsequent launches read Keychain; no Mac service is needed. Explicit `--relay-config`
continues to select local development transport. Hosted transport uses normal OS TLS
validation, with no certificate override. Release builds can read existing Keychain
configuration but have no enrollment/import flow yet; this is internal distribution only.
Use `python Backend/admin.py usage` for content-free reserved totals. Health checks are
unauthenticated liveness only: they do not prove enrollment or transcription.

## Saved-conversation Ask

`VOICE_ENABLE_ASK=1` and server-only `OPENAI_API_KEY` enable authenticated `/ask` WebSockets.
The exclusive-lock startup migration adds the approved $2.50 Ask policy, $0.003 permanent
reservation per request, and 20 attempts per UTC day; it preserves existing STT requests,
credentials and the $5 global cap. It refuses unexpected policies. Back up the ledger before
this deployment. Rolling back to a STT-only binary after migration requires an explicit
policy-compatible rollback; do not delete the ledger to make an old binary start.

Each socket receives one `{question, passages}` JSON snapshot, validates it before admission,
and streams `accepted`, `delta`, then `done` with validated source IDs, or a safe error code.
Only the selected conversation is supplied; prior Q&A is saved locally but is not model input.
The service persists no question, transcript or response payload. Logs contain request IDs,
timing and token counts. Client disconnect, revoked access or a 20-second deadline cancels
the provider stream. No automatic retries. Cancellation cannot guarantee provider-side
billing ceases instantly; the full allowance remains charged.

Luna uses Responses, `reasoning.effort=none`, `service_tier=default` (Standard), `store=false`,
no tools, and at most 1,000 output tokens. Input JSON is capped at 12,000 UTF-8 bytes and
combined prompt/input plus a 1,024-byte framing allowance at 16,000 bytes, conservatively
bounding text-token spend. Oversized input is rejected; no silent truncation. Model usage
must be inspected during integration QA. ID validation establishes source existence, not
semantic faithfulness; reviewed synthetic cases cover that separately.

The native app permits Ask during recording once text arrives, or after recording stops; it remains disabled during replay/connection/finalization. Recording and answer controls are independent. Each answer records the immutable transcript cutoff and any provisional-text caveat. It saves question, answer,
status and immutable source passages in the same session file. Backgrounding cancels Ask;
partial results remain visibly incomplete. No background generation or cross-session memory.

## Explicit QA allowances

Base daily quotas and monetary caps remain enforced. For a separately founder-approved extra recording, run `python Backend/admin.py grant-recording-attempt --date YYYY-MM-DD --approval-id <unique-approval-id>` on the service. Use the current UTC date and reuse the same ID if the command response is uncertain; retries do not add another attempt. Grants expire at midnight UTC and never refund or remove old usage. This is an administrative command, not a public endpoint or permission to grant additional usage without approval. Earlier September 25 one-day/replacement allowance rows remain in the ledger for accounting compatibility. See [V1 runbook](../docs/v1-runbook.md) for the current operational boundaries.


## Memory foundation (disabled by default)

The optional `/memory` source-synchronization endpoint and separate `memory.sqlite` are implemented for local checkpoint QA. They require `VOICE_ENABLE_MEMORY=1` on the service and an explicitly provisioned `memoryOwnerID` on the client. Current hosted configuration remains disabled and persists no transcript payloads. See the [operating contract, retention limits and evidence](../docs/memory-foundation.md) before enabling. Checkpoint 2 adds an optional background extraction/judgment worker, still disabled on the hosted service. Past-context Ask remains checkpoint 3. See [learning limits, enablement gates and paid QA accounting](../docs/memory-learning.md).

Internal credential provisioning for this path uses `enroll --memory`; renewal must include `--memory-owner <existing owner>` to preserve ownership. These flags extend the existing command, including its required URL/output path. Do not enable or provision hosted memory until the documented deployment/retention gates are resolved. Memory QA reserves a separately approved $0.25 inside the existing $5 ledger; do not provision a second copy of its spending subledger.
