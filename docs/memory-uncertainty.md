# Memory rework checkpoint 1A — unresolved lifecycle proposals

This is the first bounded part of checkpoint 1, not completion of structured identity or the full memory rework.

Previously, an uncertain Jev replacement judgment fell through to `relation=new`. A supported correction could therefore become a second current profile fact under a different subject. The writer now emits `unresolved` unless a new-fact judgment or compatible lifecycle transition is accepted. Support and attribution do not independently establish a safe transition.

Schema 4 adds `claim_relation_proposal` for candidate target links. The claim keeps its original source support, unresolved state and source-scoped subject. No identity is copied from a target when a transition fails compatibility checks. Current and historical searches exclude unresolved claims; internal `search(..., unresolved_only=True)` returns them explicitly with candidate IDs and sources. The existing recall snapshot still annotates source evidence with claim state. Dedicated qualified conflict retrieval is a later checkpoint.

Within the commit transaction, proposed targets must be live claims belonging to the same owner. A stale/deleted or foreign target rejects the whole job. Source deletion/revision invalidates unsupported content and removes dependent proposal links. Losing the target never promotes the remaining unresolved claim to current. Maintenance does not silently expire/promote an unresolved proposal. Existing accepted new facts, duplicates and supported supersession retain their contracts.

The migration is additive and performs no paid backfill or repair of historical claims. Schema-3 binaries reject schema 4; do not deploy an older binary onto an upgraded database. Hosted deployment is unchanged and requires its own reviewed rollout. Account identity, tombstones and original evidence are preserved. No prompt, provider, threshold, app or UI changes are included.

## Behavioral evidence

On the development Mac with Python 3.13:

```sh
python3 -m unittest discover -s Backend -p 'test_memory_uncertainty.py' -v
python3 -m unittest discover -s Backend -q
```

- Seven focused tests execute actual writer/store transitions in temporary SQLite databases. The recorded Maya response passes through extraction parsing, independent support replay, judgment parsing, lifecycle selection and transactional commit. After restart, swimming remains the prior active fact and tennis is unresolved with the possible target and source intact. This establishes safe storage of uncertainty, not successful semantic resolution of Maya's correction.
- Synthetic conflict/incompatible transitions remain unresolved; compatible high-confidence corrections still supersede. These are fixture judgments, not new model-quality evidence.
- Cross-owner/stale writes roll back; source revision rejects late results; deletion removes proposal links and unsupported content; migrated schema-3 data preserves owner, claims and tombstones. SQLite integrity/foreign-key checks pass.
- Full backend suite: **87 tests passed**. Broader execution was justified by a shared schema and read-contract change. Test relay/audio logs are local fixture events, not paid transcription runs.
- Zero paid calls; no hosted migration, production data edits, phone installation or device QA.

Remaining checkpoint 1 work: structured entities and mentions, evidence-backed identity links, legacy identity handling and reversible identity-dependent transitions. Reconsideration and qualified conflict retrieval remain later work; this checkpoint does not automatically resolve or reprocess existing failures.
