# Internal V1 runbook

Status: founder-only internal V1 accepted September 25, 2026. This is an installed development build, not a public release. The product remains: “Granola with an AI that listens alongside you and can join the conversation.”

## Use on iPhone

Open VoiceCompanion. The current phone already has its hosted-service credential in Keychain; no laptop relay or cable is needed for use. Internet access is required for transcription and answers.

1. Start recording and speak. Transcript text appears as the provider returns it; speaker labels are best-effort.
2. Recording can continue while the phone is locked. Calls or audio interruptions end capture explicitly; received text remains saved. Unlock to interact with Ask.
3. Type a question under Ask about this conversation. Recording continues during the answer. Ask uses only the transcript received at submission, with a visible cutoff; recently spoken words may not be included yet.
4. Open a source to inspect the fixed passage used by that answer. Each question stands alone: previous answers and other sessions are not supplied to the model.
5. Stop recording, return to sessions, and reopen the transcript and answer history. Delete session removes both from local app storage.

Stop recording and Cancel answer are independent. Backgrounding cancels an active answer but can leave recording running. There is no automatic paid retry or resume after interruptions.

## Installed build and service

- Native implementation: `fc7bc1c`, installed on the founder's iPhone 16 Pro, iOS 26.5.2. Subsequent checkpoint commits changed backend QA admission/docs, not native source. Merged checkpoint baseline: `57db047`.
- Hosted backend: tested commit `f5e022e`, Render deployment `dep-darbtrojo6nc73fc2l40`, service `srv-daqtfs7lot8c73dleuug`, https://voice-companion-sdbr.onrender.com. Auto-deploy is off; deploy only a tested commit outside active sessions.
- Provider: Grok streaming transcription; direct GPT-6 Luna answers with reasoning none, Standard processing, no tools, no automatic retries. Jev is deferred.
- Founder credential expiry checked September 25: October 2, 2026 at 02:17:38 UTC. Renew deliberately using [internal provisioning](../Backend/README.md#internal-provisioning) when needed. Do not put provider keys in the app or commit client exports.
- The Mac target builds and shared core behavior passes. V0 Mac microphone evidence remains valid; full new iPhone interface parity or new live Mac Ask QA is not claimed.

For a new internal device, use the DEBUG hosted credential import documented in the backend runbook. The existing phone needs no re-enrollment for this checkpoint. Build with `DEVELOPMENT_TEAM=<team> DEVICE_ID=<device-id> scripts/check.sh device build`, then install the resulting signed app with `xcrun devicectl device install app`. Development signing/provisioning may expire independently of the service credential; public installation and renewal UX are deferred.

## Limits and recovery

| Situation | Meaning and next action |
| --- | --- |
| Recording stops after five minutes | Current verified cap; start a new session deliberately if allowance remains. No long-session endurance promise. |
| Daily recording/Ask limit | Base allowance is six recording attempts and twenty Ask admission rows per UTC day for this single-founder service. Failed attempts count. Wait for midnight UTC or obtain explicit approval for a bounded QA grant. |
| Total budget reached | Stop provider testing and obtain a revised budget. Never reset the ledger or disguise prior attempts. |
| Access expired or revoked | Re-enroll through the administrator; no automatic key fallback. |
| Network, provider or capture interruption | Read the explicit incomplete/error state; existing received text is retained. Diagnose before a deliberate retry. |
| Answer is slow or cancelled | Capture is independent. Partial answers remain visibly incomplete. Server deadline is twenty seconds; client deadline twenty-five. |
| Context too large | Current JSON context limit is 12,000 UTF-8 bytes and at most 200 passages. Nothing is silently truncated. Shorten the recording/use a smaller session; no retrieval is implemented. |
| Answer contradicts the conversation | Inspect the cited snapshot. Source IDs prove passage existence, not truth or faithful reasoning. Do not treat uncertain speaker labels as identity. |

The $5 lifetime provider-testing ceiling comprises $2 STT, $2.50 Ask and $0.50 retired Jev allocation. Reservations remain charged even on failure: $0.02 per ordinary recording and $0.003 per ordinary Ask. September 25 final read-only snapshot: STT $0.180, Ask $0.102, retired Jev $0.023; total $0.305 reserved, $4.695 remaining overall, subject to category/day limits. These are conservative admission reservations, not invoices. Evaluation batch rows do not equal individual model-call counts. The three explicitly authorized extra recordings that day are already consumed; no unused extra attempt remains. UTC rollover resets daily counts, not lifetime spend.

Hosting's approved baseline is approximately $7.25/month before taxes/extras, separate from provider testing. New spending or longer recordings need their own bounded authorization.

## Storage and operational boundaries

Sessions and Q&A are local JSON files in the app's Application Support/VoiceCompanion/sessions directory. No cross-device sync or server transcript database exists. Audio streams to xAI; the selected transcript snapshot and question go to OpenAI. Routine service telemetry contains IDs, durations/status and token counts, not conversation content. No raw audio is retained by the app/relay.

Deleting a local session does not erase provider retention, device backups, or deliberately exported QA copies. `store:false` does not establish zero provider retention. The operating contract's thirty-day ledger cleanup, de-identified accounting migration, and administrative account erasure are proposed responsibilities, not implemented jobs. The ledger currently retains accounting and credential-hash records. Resolve retention/backup/deletion policy and user-facing disclosure before inviting others; do not present this founder build as production-ready.

Use `python Backend/admin.py usage` on the exact Render instance for reserved totals. `/health` is read-only liveness, not proof of microphone, credentials, provider health or remaining quota. Before deployment, verify zero active requests and make a SQLite backup using the backup API; preserve policy and all charged requests. Never replace the persistent ledger to make an old binary start. Do not operate on unrelated Render services.

## Evidence and handoff

[Final acceptance](v1-acceptance.md) maps the required behavior to existing physical-device, provider, UI and regression evidence. No additional microphone/provider run was necessary for this documentation and final regression pass.

Future scope remains separate: longer capture, latency improvements, consumer UI polish, spoken questions/replies, proactive participation, cross-session memory/retrieval, computer audio, sync, signup/billing, TestFlight/public distribution and privacy/retention operations. This internal V1 establishes current-conversation context plus explicit typed Ask; it does not yet establish a daily consumer habit or an always-on companion.
