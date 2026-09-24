# Development relay

This is a local Mac development relay, not a deployed service. Python 3.11+ and websockets 15.0.1 are required (`python3 -m pip install -r Backend/requirements.txt` in your chosen virtual environment).

Run `python3 Backend/relay.py` from the repository. It reads the ignored `.env`, binds only 127.0.0.1:8766, and writes a short-lived random client credential to `work/relay-client.json` with owner-only permissions. Quit with Ctrl-C; the client configuration is removed. The provider key never enters the native app. Do not expose this process publicly.

Build with `DEVELOPMENT_TEAM=<team> scripts/check.sh mac build`, then launch the built app with `--relay-config <absolute-path-to-work/relay-client.json>`. Use a stable development signing identity for microphone permission. The app asks for microphone access and only starts capture when recording is requested.

Limits: one active session, three upstream connection attempts per relay process, 60 audio seconds per session, 180 audio seconds per process, and a 70-second server timeout. The app auto-stops at 55 seconds and allows bounded finalization. No automatic retries. Logs contain duration/status/estimated cost, not transcript text or raw audio. No raw audio is retained. Estimates are not verified invoices.

Run `python3 -m unittest discover -s Backend -p 'test_*.py'` for a real-socket local test with a fake upstream. It verifies unauthorized clients never reach the provider, authorized frames/finalization are forwarded, connections clean up, and the session cap rejects new calls. It makes no external API calls.

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
