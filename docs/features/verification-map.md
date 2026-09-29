# Product feature verification map

Each row links a product outcome to its own verifier. Run `python3 scripts/verify_feature.py <feature-id>` for full verification, or add `--checks-only` for local mechanical checks. Checks-only never establishes feature acceptance.

Source of truth: [machine-readable catalog](catalog.json). These entries describe repository foundations, not freshly verified production state. External evidence must match the tested commit and the actual scope claimed; missing evidence leaves full verification incomplete. Historical QA links in [feature details](features.md) remain scoped historical evidence.

| Feature / ID | Implementation state | Dedicated verifier | Required real-path evidence |
| --- | --- | --- | --- |
| **Capture and live transcript** / `capture` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/capture.json) | Actual microphone/provider capture, interruption and save/reopen |
| **Recording library and sync** / `library` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/library.json) | Offline save/relaunch, sync recovery and attaching a recording |
| **Meeting note summaries** / `meeting-notes` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/meeting-notes.json) | Final note-generation configuration produces a faithful summary through service/storage; Render the actual summary and supporting passage; inspect failures/retry |
| **On-device note caching** / `note-cache` | planned; persistent cache not implemented | [Acceptance + checks](verification/note-cache.json) | Implement and exercise disk persistence, invalidation, owner separation and refresh coalescing; Cold launch/offline read, refresh success/failure, deletion and sign-out |
| **Companion chat and follow-ups** / `chat` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/chat.json) | Actual answer/follow-up pipeline with final model configuration; Streaming, draft preservation, attachment, failed delivery and reopen |
| **Composer dictation** / `dictation` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/dictation.json) | Actual dictation recognition, discard/send, permission and interruption; backend budget test alone is insufficient |
| **Notes search** / `notes-search` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/notes-search.json) | Search results, empty/error state and opening the correct note |
| **Automatic memory learning** / `memory-learning` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/memory-learning.json) | Real extraction/verification on bounded source, accepted/rejected claims and resulting durable memory |
| **Past-context retrieval** / `recall` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/recall.json) | Actual ranked context → answer pipeline, irrelevant and conflicting evidence cases |
| **Personal context and identity** / `identity` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/identity.json) | Named, unknown and third-party subject cases through the active identity path |
| **Memory corrections and time** / `memory-lifecycle` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/memory-lifecycle.json) | Changed temporal/relationship judgments on real model output; never infer event completion |
| **Note deletion and retained answers** / `deletion` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/deletion.json) | Swipe/long-press deletion, source unavailable, preserved replies and reopen |
| **Proactive contributions** / `proactive` | implemented foundations; fresh feature verification required | [Acceptance + checks](verification/proactive.json) | Active decision → output → storage/delivery; relevant, resolved and same-topic-irrelevant cases; Actual bubbles, Quiet/stop, no stale/duplicate deliveries in intended configuration |
| **Tester access and account controls** / `access` | internal foundation; independent beta readiness unverified | [Acceptance + checks](verification/access.json) | Actual authenticated service paths with two isolated users and revocation; Fresh enrollment, sign-out/data clearing and actionable failure UI |
| **TestFlight install and update** / `distribution` | internal foundation; independent beta readiness unverified | [Acceptance + checks](verification/distribution.json) | Signed release install/update and independent tester access; intended native/backend version pairing |
| **Sign-up and pricing previews** / `subscriptions` | preview/deferred; not delivered as a working integration | [Acceptance + checks](verification/subscriptions.json) | Verify pilot navigation accurately marks or excludes unavailable sign-up/pricing flows |
| **Calendar, email and messages** / `connected-sources` | preview/deferred; not delivered as a working integration | [Acceptance + checks](verification/connected-sources.json) | No implemented verifier: requires scoped connector design, consent, ownership and disconnect contract before implementation |

Each manifest names the expected evidence paths, acceptance and checks. The catalog lists implementation/test files for worker navigation. The orchestrator supplies the final feature packet before work, checks imported receipts and explicitly accepts the result. The generic runner alone cannot determine if a generated note is faithful or a rendered page is correct.

Adding/changing a feature: update its catalog entry, manifest, relevant tests and evidence scope together. Do not grant a feature pass by weakening a requirement or substituting replay for fresh model behavior. Use `--list` to discover feature IDs. No command triggers a paid API, microphone, device interaction or release automatically.

## Initial mechanical check results — September 29, 2026

The first run exercised all 13 configured feature suites at `872388f`. Nine suites passed their mechanical checks: capture, library, meeting-notes, chat, dictation, notes-search, recall, proactive, and access. This is not live-feature acceptance.

Four suites remain incomplete with existing failures (the feature-verifier change does not modify their implementation/tests):

- `memory-learning`: `test_schema7_migration_adds_no_automatic_fact_metadata_or_jobs` expects schema 17; actual schema is 19.
- `identity`: `test_migrate_v4_preserves_legacy_ids_and_does_not_backfill` has the same version mismatch.
- `memory-lifecycle`: `test_migration_v5_preserves_identity_links_and_tombstones` has the same version mismatch.
- `deletion`: `test_exact_provider_replay_through_companion_sockets` receives `answer_unavailable` instead of a saved answer. Diagnose the replay/active contract before claiming retained-answer acceptance.

These are baseline findings, not waived requirements. Fix and rerun the affected feature verifier in its bounded implementation packet. No paid model calls or phone interaction were used. The four features without automated suites remain explicit gaps, not passes.
