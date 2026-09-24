# Development relay

This is a local Mac development relay, not a deployed service. Python 3.11+ and websockets 15.0.1 are required (`python3 -m pip install -r Backend/requirements.txt` in your chosen virtual environment).

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
