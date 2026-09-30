# Product knowledge reconciliation — September 30, 2026

Implementation/documentation checkpoint: `dd5e498`, based on candidate `7079427`.
The founder requested a product-wide refresh of knowledge, feature maps and
verification tooling. This is documentation/tooling acceptance, not new product,
provider, physical or TestFlight acceptance.

## Reconciled scope

- Current-state brief and TestFlight handoff distinguish main `d4d07f1`, unmerged
  account PR159–177, recorded schema21 deployment `208ca34`, physical founder
  migration and later local-only fixes. GitHub main/open PR state was read during
  the audit; production itself was not freshly inspected.
- Entry points and canonical refinements preserve the one-liner, invited social
  presence, separate persistent Google/Apple accounts, existing UI and sequential
  release phases. Historical evidence retains its failures and original scope.
- All 19 catalog entries and their markdown verification table are synchronized.
  Account/provider/migration/backup/restore regression routes and external native
  test sources are mapped. Shared UI and cache are implemented, not previews.
- Real OAuth evidence uses `live_identity_provider`, with matching provider,
  configuration, pipeline and actual call accounting. Synthetic identity fixtures
  cannot meet that category. Physical, independent-person, failure/recovery and
  operational backup evidence remain required.
- Catalog loading rejects missing/outside paths, mismatched runners and full
  feature manifests that omit live behavior or inspection. Mechanical-only
  evidence still cannot release dependent work. Receipt metadata remains subject
  to human/orchestrator inspection; it does not authenticate itself.

## Independent verification

Primary and worker each executed:

```sh
python3 -m unittest discover -s scripts/verification -p 'test_*.py' -q
python3 scripts/verify_feature.py --list
git diff --check
```

Twenty self-tests pass. Discovery lists 19 feature IDs. The primary also checked
910 relative file links across 70 changed Markdown files: all resolve. This file
was added after that count. No app/backend/native-test/UI-asset source changed.
Independent review caught one stale AGENTS routing link to the historical gap
sequence; it was corrected to current-state and the TestFlight handoff.

On clean commit `dd5e498`, actual CLI behavior was inspected:

- `python3 scripts/verify_feature.py pricing` exited 1, returned `incomplete`,
  `feature_verified: false`, and all four missing behavior/inspection gates.
- `python3 scripts/verify_feature.py subscriptions --checks-only` exited 2 with
  “No automated verifier implemented for this feature yet.”

Those expected refusals verify that missing implementation/evidence cannot become
a green release result. Neither command executed a provider or purchase. No paid
calls, deployment, phone installation, UI redesign or new release acceptance.
The separate product Phase 1 gates remain open.
