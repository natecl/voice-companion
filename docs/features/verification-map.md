# Product feature verification map

> Current September 29 release status and remaining phases: [TestFlight handoff](../execution/testflight-release-handoff.md). UI/integration PR154–155 are merged and the internal phone build is installed; backend rollout, independent accounts and paid plans remain pending. Earlier dated evidence below is historical, not a fresh release attestation.

Start with the [dedicated context map for your feature](context-map.md): current behavior, gaps, dependencies, evidence and next bounded work.

Each row links a product outcome to its own verifier. Run `python3 scripts/verify_feature.py <feature-id>` for full verification, or add `--checks-only` for local mechanical checks. Checks-only never establishes feature acceptance.

Source of truth: [machine-readable catalog](catalog.json). These entries describe repository foundations, not freshly verified production state. External evidence must match the tested commit and the actual scope claimed; missing evidence leaves full verification incomplete. Historical QA links in [feature details](features.md) remain scoped historical evidence.

| Feature / ID | Implementation state | Dedicated verifier | Required real-path evidence |
| --- | --- | --- | --- |
| [Capture and live transcript](maps/capture.md) / `capture` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/capture.json) | Actual microphone/provider capture, interruption and save/reopen |
| [Recording library and sync](maps/library.md) / `library` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/library.json) | Offline save/relaunch, sync recovery and attaching a recording |
| [Meeting note summaries](maps/meeting-notes.md) / `meeting-notes` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/meeting-notes.json) | Final note-generation configuration produces a faithful summary through service/storage; Render the actual summary and supporting passage; inspect failures/retry |
| [On-device note caching](maps/note-cache.md) / `note-cache` | cache/shared iPhone locally verified; account lifecycle pending | [Acceptance + checks](verification/note-cache.json) | Implement and exercise disk persistence, invalidation, owner separation and refresh coalescing; Cold launch/offline read, refresh success/failure, deletion and sign-out |
| [Companion chat and follow-ups](maps/chat.md) / `chat` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/chat.json) | Actual answer/follow-up pipeline with final model configuration; Streaming, draft preservation, attachment, failed delivery and reopen |
| [Composer dictation](maps/dictation.md) / `dictation` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/dictation.json) | Actual dictation recognition, discard/send, permission and interruption; backend budget test alone is insufficient |
| [Notes search](maps/notes-search.md) / `notes-search` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/notes-search.json) | Search results, empty/error state and opening the correct note |
| [Automatic memory learning](maps/memory-learning.md) / `memory-learning` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/memory-learning.json) | Real extraction/verification on bounded source, accepted/rejected claims and resulting durable memory |
| [Past-context retrieval](maps/recall.md) / `recall` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/recall.json) | Actual ranked context → answer pipeline, irrelevant and conflicting evidence cases |
| [Personal context and identity](maps/identity.md) / `identity` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/identity.json) | Named, unknown and third-party subject cases through the active identity path |
| [Memory corrections and time](maps/memory-lifecycle.md) / `memory-lifecycle` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/memory-lifecycle.json) | Changed temporal/relationship judgments on real model output; never infer event completion |
| [Note deletion and retained answers](maps/deletion.md) / `deletion` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/deletion.json) | Swipe/long-press deletion, source unavailable, preserved replies and reopen |
| [Proactive contributions](maps/proactive.md) / `proactive` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/proactive.json) | Active decision → output → storage/delivery; relevant, resolved and same-topic-irrelevant cases; Actual bubbles, Quiet/stop, no stale/duplicate deliveries in intended configuration |
| [Tester access and account controls](maps/access.md) / `access` | internal foundation; independent beta readiness unverified | [Acceptance + checks](verification/access.json) | Actual authenticated service paths with two isolated users and revocation; Fresh enrollment, sign-out/data clearing and actionable failure UI |
| [TestFlight install and update](maps/distribution.md) / `distribution` | internal foundation; independent beta readiness unverified | [Acceptance + checks](verification/distribution.json) | Signed release install/update and independent tester access; intended native/backend version pairing |
| [Subscriptions and paywall](maps/subscriptions.md) / `subscriptions` | planned billing; previews only | [Acceptance + checks](verification/subscriptions.json) | Sandbox purchases, restore/lifecycle, account-bound entitlements and truthful paywall states |
| [Calendar, email and messages](maps/connected-sources.md) / `connected-sources` | preview/deferred; not delivered as a working integration | [Acceptance + checks](verification/connected-sources.json) | No implemented verifier: requires scoped connector design, consent, ownership and disconnect contract before implementation |
| [Invited social presence](maps/social-presence.md) / `social-presence` | planned; foundations only | [Acceptance + checks](verification/social-presence.json) | Prototype review, native states/accessibility/persistence; proactive judgment separately |

Each manifest names the expected evidence paths, acceptance and checks. The catalog lists implementation/test files for worker navigation. The orchestrator supplies the final feature packet before work, checks imported receipts and explicitly accepts the result. The generic runner alone cannot determine if a generated note is faithful or a rendered page is correct.

Adding/changing a feature: update its catalog entry, manifest, relevant tests and evidence scope together. Do not grant a feature pass by weakening a requirement or substituting replay for fresh model behavior. Use `--list` to discover feature IDs. No command triggers a paid API, microphone, device interaction or release automatically.

## Initial mechanical check results — September 29, 2026

The first run exercised all 13 configured feature suites at `872388f`. Nine suites passed their mechanical checks: capture, library, meeting-notes, chat, dictation, notes-search, recall, proactive, and access. This is not live-feature acceptance.

The initial run found four incomplete suites (the feature-verifier change did not modify their implementation/tests):

- `memory-learning`: `test_schema7_migration_adds_no_automatic_fact_metadata_or_jobs` expects schema 17; actual schema is 19.
- `identity`: `test_migrate_v4_preserves_legacy_ids_and_does_not_backfill` has the same version mismatch.
- `memory-lifecycle`: `test_migration_v5_preserves_identity_links_and_tombstones` has the same version mismatch.
- `deletion`: `test_exact_provider_replay_through_companion_sockets` receives `answer_unavailable` instead of a saved answer. Diagnose the replay/active contract before claiming retained-answer acceptance.

These are baseline findings, not waived requirements. Fix and rerun the affected feature verifier in its bounded implementation packet. No paid model calls or phone interaction were used. The four features without automated suites remain explicit gaps, not passes.

## Bounded baseline repair — September 29, 2026

The [P0 checkpoint](../qa/background-baseline/p0-b.md) explains and repairs the four mechanical failures against base `47eadb4`. Migrations now assert intentional schema 19, preserve no-backfill/integrity/identity checks, inspect empty additive tables and verify a second reopen. Retention replay is labeled historical: only its recorded instructions are pinned, while every other request field remains exact. A negative check rejects a current-prompt request without consuming cached responses.

All four affected mechanical feature suites pass after independent coordinator reproduction. This restores regression checks, not full memory/deletion feature acceptance. No current provider, native app, physical device, deployment or install was exercised; full feature manifests retain their required evidence gates. See the checkpoint report for exact tested commits and receipts.

## Plans and billing release gates

[Plans and usage limits](maps/pricing.md) now has its own [verifier](verification/pricing.json): `python3 scripts/verify_feature.py pricing`. Accounts, subscriptions and distribution manifests now require real release/sandbox/lifecycle evidence, not merely preview navigation. Prices and auth-provider choices remain open. No new pass receipts were generated by this documentation update.
