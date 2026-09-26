# Internal companion rollout

September 26, 2026. Founder explicitly approved internal rollout and an additional $0.50 QA allocation, and declined the Render upgrade. The service remains **Starter, 512 MiB / 0.5 CPU, $7/month**; no hosting tier increase was applied. Public release remains out of scope.

## Reviewed deployment

Backend commit `107ae6e4f7400a5a2b309494eb8aeece0688202f` includes the memory rework, persistent chat, source navigation and bounded embeddings. [PR 66](https://github.com/natecl/voice-companion/pull/66) implements the approved budget; [PR 67](https://github.com/natecl/voice-companion/pull/67) qualifies Starter capacity. All 300 backend tests pass, alongside the prior native Mac/iPhone simulator behavior evidence. See [capacity measurements](companion-capacity.md).

The existing Render service now tracks `main` with automatic deployment still off. Its build installs `Backend/requirements-semantic.txt`. The approved start command explicitly enables `VOICE_ENABLE_MEMORY_REWORK`, `VOICE_ENABLE_COMPANION`, `VOICE_ENABLE_SEMANTIC_INDEX`, and `VOICE_ENABLE_ROLLOUT_QA`; the pinned cache is `/var/data/voice-companion/embedding-models`, loaded offline. Other existing provider credentials and feature settings remain in their configured environment. No secrets belong in this document.

A fresh consistent SQLite backup was made before deployment, stored privately on the persistent disk and transferred to ignored local work storage with SHA-256 verification. Migration 3→15 preserved original owner, credential ownership, source, claim, support and job values. The actual staged service's data matched the backup. No historical sources were reprocessed or indexed; existing source recall uses the supported fallback until new sources are indexed.

The first cache transfer was interrupted by the staged deployment and was not treated as successful. A subsequent complete transfer passed checksums for every cached file. The actual Render instance loaded the pinned model offline and returned a 384-dimensional query vector. With the old service and separate probe both resident, total cgroup usage was 464,191,488 bytes; no memory-limit or OOM events occurred. This is pre-activation evidence, not the final workload claim.

## QA allowance

The one-time operator action provisioned `companion-rollout-qa-2026-09-26-050`. Profile/rework cap is now $2.90, with $2.38 historically reserved and **$0.52 remaining** before physical QA. Global $5 cap is unchanged. Category caps are STT $1.50, Ask $2.85, Jev $0.65; Ask $0.35/Jev $0.15 are reserved for this additional sub-allocation. No earlier attempts were refunded, and no paid provider calls occurred during capacity/preparation.

Provisioning ran only after the compatible staged backend was healthy and no requests or learning jobs were active. Policy redistribution and global reservation use a single `BEGIN IMMEDIATE` transaction, the same serialization boundary as request admission. This operator action neither migrates source schema nor recovers in-flight requests; those startup operations still require the exclusive service lock. Restart does not grant credit. Existing old-cap workers do not gain spending access until explicit rollout activation.

## Activated service evidence

Deployment `dep-darv6n0jo6nc739ir7g0` is live. Learning and indexing health both report idle with no failures. The public TLS WebSocket companion endpoint rejected unauthenticated access and returned main-chat history for an authorized short-lived QA credential linked to the existing owner. That credential was revoked immediately afterward; no token or content was logged. Usage reservations stayed unchanged. Service cgroup memory during the check was 362,926,080 bytes (346 MiB); all memory-limit/OOM event counters were zero. Existing sources remain unindexed as intended, with no automatic backfill.

## Physical iPhone evidence

The signed build was installed on the founder's iPhone 16 Pro and launched with persistent companion activation after explicit readiness. The founder exercised the real microphone/provider path. Their reports, screenshot and read-only server inspection establish:

- A sourced answer about Project Juniper's morning meetings appeared during capture. The later spoken library-location sentence reached the final saved transcript; recording continued after the answer.
- After reopening, the companion answered the location from saved source evidence without an attached recording.
- A new recording changed the location to the community center. The answer used that correction and its source opened the new recording.
- Deleting the correction invalidated its dependent answer. The removal notice persisted after app relaunch. Server verification found the source tombstoned with null payload, no supporting rows, embeddings, live snapshots or chat dependencies for it, and null answer text/empty citations on the invalidated turn.
- The founder's final screenshot shows the original recording attached through Ask about this. The first response reports morning meetings and the library with sources; the follow-up “and where?” returns the library with its source. Both turns are saved complete on the server.

This passes the exercised physical capture/chat, saved-source recall, source navigation, attachment, follow-up and deletion/relaunch behaviors. Navigation between both surfaces while actively recording has simulator evidence, but was not separately confirmed in this physical run. No public release or general memory-quality claim follows from this small fixture.

### Preserved quality limitations

The attached-recording answer added an unsolicited “I can’t say they’re yours” disclaimer. The user had not asked to attribute preferences to themselves. Keep identity safeguards, but make uncertainty relevant to the actual question; this is a response-quality follow-up, not a failed attachment transport check.

Both extracted location claims were `unresolved` with `relation_unresolved` before correction-source deletion. The correct updated answer demonstrates retrieval and answering over original evidence, **not** verified claim supersession. This remains a memory-relation quality issue to investigate using saved evidence before any additional provider run. Do not mark automatic relation/lifecycle correction proven by this fixture.

### Final bounded accounting

Profile/rework reservations reached **$2.58 of $2.90**, leaving **$0.32**. Physical QA added 20 conservative one-cent memory/model reservations ($0.20) over the $2.38 baseline. Direct answer reservations added $0.018 (six attempts), and STT reservations added $0.10 (five attempts, including the user's actual attempts beyond the guided successful captures). Subledger spending is already globally reserved and must not be counted twice. These are reservations, not measured invoices.

Final global reservations: Ask $2.779, Jev $0.553, STT $0.340, total $3.672 of the unchanged $5 cap. No paid retries or refunds were performed by the agent. Read-only final inspection found no failed learning jobs and zero memory-limit/OOM events. No further paid test was run to close this evidence checkpoint.

Rollback must not restore old source databases or resurrect deleted material. Do not run a schema-3 binary against schema 15. Disable new feature flags on a compatible reviewed binary if containment is necessary; disabling semantic retrieval is a reported degraded state, not equivalent acceptance.
