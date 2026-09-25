# Internal V1 acceptance — September 25, 2026

Accepted for the founder-only installed iPhone trial. This handoff changes documentation only, starting from merged `57db047`; it reuses behavior evidence where implementation is unchanged. Jev routing was explicitly deferred after its failed benefit/grounding gate, not silently passed. Public release and additional consumer features remain outside this acceptance.

| Requirement | Evidence and scope |
| --- | --- |
| iPhone records independently of Mac | Successive real hosted sessions and Keychain provisioning in [hosted validation](v1-hosted-validation.md). |
| Locked/background capture and safe interruption | Actual lock/unlock, incoming call, preservation and bounded five-minute run in [background validation](v1-background-validation.md). No all-day battery claim. |
| Ask about a saved conversation, inspect sources, relaunch | Founder-confirmed correct answer, source and full app-relaunch persistence in [saved Ask validation](v1-ask-validation.md). |
| Ask during listening, continue afterward, persist both | Two actual phone/provider runs, plus independent saved-container inspection, in [live Ask validation](v1-live-ask-validation.md). The final run's later phrase occurs after answer completion and remains outside its fixed source snapshot. |
| Missing information, context boundaries and grounding | Frozen real-Luna synthetic cases and the targeted prompt-correction rerun in [synthetic evidence](v1-ask-synthetic-evidence.md). Missing and wrong-session answers declined to invent facts. Prompt and direct provider implementation are unchanged since corrected baseline `6226944`; no new paid call needed. |
| Representative failures and independent cancellation | Actual local WebSocket fixtures cover provider errors, abrupt disconnect, rejected access, finalization timeout and retained text. Current native live-Ask tests cover failure/cancellation isolation; backend Ask tests cover invalid references, revocation, cancellation and budget denial. These are synthetic failures through real app/server contracts, not simulated proof of microphone quality. |
| Shared Mac compatibility | Final Mac target build and core regression results below. Physical Mac microphone behavior is supported by prior V0 evidence; no new live Mac Ask claim. |

Practical usefulness: the founder said the first live question went well and the answer was good without supplying a recap in the typed question. The second saved answer correctly recalled the supplied appointment fact. This demonstrates the bounded context-aware interaction, not product-market fit, long-term utility, or a daily-use habit.

## Final regression pass

On macOS 26.6.2 / Xcode 27.0, the Mac target built and 26 non-transport core tests passed (Ask, live Ask, recording lifecycle, configuration and transcript handling). The initial direct xcodebuild invocation omitted the documented fixture Python override, causing fourteen transport fixture startup failures due to missing `websockets`; preserve that failed log. Reran only the affected transport class with `TEST_RUNNER_VOICE_TEST_PYTHON=/Library/Frameworks/Python.framework/Versions/3.13/bin/python3`: fourteen passed. The existing opt-in ninety-second socket test remained skipped; no duration-related implementation changed. No product code fix or broad repeat was needed.

Eight targeted backend Ask/startup tests also passed. Existing final-checkpoint evidence remains applicable: sixteen admission/admin/relay tests, two simulator UI tests with visual inspection, signed iPhone build, and actual phone/provider runs. Final review covered immutable snapshots, independent state/cancellation, persistence, source resolution and usage preservation. No runtime source changes in this handoff.

Ignored logs: `work/v1-final-mac-core.log` (initial environment failure preserved), `work/v1-final-transport.log`, `work/v1-final-backend.log`. Successful transport result: `Test-Mac-2026.09.25_14-41-41--0400.xcresult` in the Mac DerivedData test logs.

Read-only hosted check: HTTP health 200, zero active requests, founder credential not revoked, expiry October 2 at 02:17:38 UTC. Ledger reservations total $0.305, including deferred Jev spending. No provider calls, new recording grants, device reinstall, or user-dependent manual QA were performed in this final pass.

## Known limits and delivery

The installed native build and tested hosted backend are identified in the [V1 runbook](v1-runbook.md), along with setup, recovery, quotas, credential renewal, storage and retained operational responsibilities. Sources may be semantically wrong despite valid IDs; anonymous speaker labels are unverified. First-answer-text latency varied from 2.626 to 6.207 seconds in the live-Ask runs. Exact screen-paint times are not logged. Recording remains five minutes, Ask is foreground/typed/current-conversation only, and public privacy/deletion/distribution operations remain unfinished. No additional microphone or paid run is needed to close this unchanged-code handoff.
