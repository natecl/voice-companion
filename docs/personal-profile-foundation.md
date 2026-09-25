# Personal profile foundation

Checkpoint 1: personal source capture and storage, with learning/recall deliberately held. No voice enrollment or public release.

The enrolled app can save a personal text note through the existing local session store and durable outbox. Protocol v2 carries `origin: personal_text`; old recording operations remain v1 and retain their original wire representation. The authenticated credential determines ownership. A personal declaration establishes authorship, not the subjects of every statement. Source origin is immutable across revisions. The new source is held in `profile_pending`, and excluded from cross-session recall until the learning and recall checkpoints pass. The UI explicitly states that personal learning is not enabled.

Schema v3 adds a default-false `profile_link` to claims. The derived profile accepts active, supported user facts and explicitly user-linked subjects across existing kinds, including qualified tentative plans. It filters before limiting results. The writer boundary rejects user/profile claims from ordinary recording sources; models cannot bypass that guard. Relationship claims retain their own subject. Semantic validation remains PR 2 work; fixture claims here do not demonstrate model attribution quality.

Local saving precedes upload, failed upload preserves the note and outbox, and saved notes reopen/delete through existing session handling. Sync acknowledgments update the visible state. No provider key or external inference is needed for this checkpoint. New notes require a memory-enabled enrollment; no old recordings are silently imported.

## Verification — September 25, 2026

- `work/profile-foundation-backend-final.log`: 44 backend memory tests passed, including legacy-v2 migration, personal provenance/protocol guards, owner isolation, broad profile/relationship selection, correction, expiry, stale commits, deletion and existing learning/recall regressions. Synthetic and cached provider responses only.
- `work/profile-foundation-native-fixed.log`: six native memory tests and two Mac UI tests passed. The actual app typed a synthetic personal note, saved/synchronized over URLSession WebSocket to the local Python service/SQLite, showed the correct sync state, relaunched, reopened, and deleted it from both sides. Existing recording synchronization remains passing. Offline notes persist, invalid input is rejected, and no unbounded retry occurs.
- `work/profile-foundation-phone-final.log`: shared iPhone simulator build. This is not physical-device acceptance.
- `work/profile-foundation-screens`: inspected reopened personal-note screenshot; kept local because it includes desktop surroundings.

The initial build exposed Observation's effect on a monitored property's deinitialization; the non-observed network monitor retains its original cleanup. Initial UI execution also stalled reading the runner's private-container configuration. The Debug-only loopback fixture now passes synthetic configuration through the UI launch environment, validating scheme/host/path and owner. Production provisioning and OS permissions are unchanged. Failed output remains in `work/profile-foundation-native.log`; corrected real UI execution passed.

Final changes after native execution only tighten backend malformed-input guards and add backend tests; those are covered by the final backend run. No changes to microphone capture or provider integrations and no paid calls. $1 profile QA approval remains unspent and unprovisioned.

## Deployment and rollback boundary

Not deployed. Schema migration is additive but the old memory binary rejects version 3: do not simply roll back the binary against the migrated database. Before deployment, take a SQLite backup and define an operator-reviewed rollback preserving subsequent source/deletion changes and the independent spend ledger. Prefer disabling memory/profile operation and forward-fixing over restoring an old content snapshot that could resurrect deleted sources. PR 2 and PR 3 must separately prove live learning and physical-iPhone recall. No hosted or physical-device profile claim is made here.
