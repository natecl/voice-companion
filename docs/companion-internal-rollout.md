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

## Remaining physical acceptance

The signed iPhone build succeeded. Installation/activation and manual QA wait for founder readiness. Do not equate backend health or simulator evidence with physical acceptance. Planned checks: capture while chatting, navigate without stopping capture, save/reopen, attach a recording, follow up, verify a correction, relaunch, and delete the test source with dependent answer invalidation. Keep anonymous speaker identity unresolved. No microphone test starts without a ready response.

Rollback must not restore old source databases or resurrect deleted material. Do not run a schema-3 binary against schema 15. Disable new feature flags on a compatible reviewed binary if containment is necessary; disabling semantic retrieval is a reported degraded state, not equivalent acceptance.
