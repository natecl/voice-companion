# TestFlight provider-testing allowance

Founder approval: September 29, 2026, $5 total for provider/API testing toward TestFlight readiness. No automatic paid retries. Excludes hosting upgrades, subscriptions and other purchases. This is a separate grant; preserve all earlier grants and charges.

Approval ID: `testflight-readiness-2026-09-29`.

| Limit | Reserved | Actual recorded | Remaining unreserved |
| --- | --- | --- | --- |
| $5.00 | $0.02 | Invoice cost unavailable | $4.98 |

Before each paid run, record its purpose, provider/model, bounded call count, maximum cost, and reservation. Afterwards record observed usage/cost and sanitized evidence. Keep failed attempts charged until billing evidence supports reconciliation. Stop before a call whose maximum could exceed the remaining allowance. This ledger alone does not alter runtime quotas; any provisioning must preserve historical reservations and charges.

One physical transcription attempt has now used the $0.02 reservation below; actual billed cost is not yet available.

September 30 non-billable OAuth checks: two requests to Google’s token-revocation endpoint using wholly fabricated invalid tokens—one Python response-contract investigation, one explicitly opted-in Swift simulator adapter check. Both returned `invalid_token`; no real grant or account changed. No model calls or paid requests, $0 expected cost; the paid allowance remains untouched. Evidence: [Google revocation QA](../qa/google-account-revocation/README.md).

## Physical capture/sign-out QA allocation — September 30

One transcription attempt reserved under `testflight-account-signout-20260930-020`:
$0.02 ceiling from this grant, not billed usage. The hosted STT envelope was
exhausted; deployed compatibility patch `482394e` recognizes an explicit,
idempotent global/STT-cap extension. The operator applied it once after a
24-database/123-table preservation check and hash-verified off-host backup.
No request, prior charge, daily policy or other category cap was reset.
No automatic retries or extra daily attempts. The physical capture ran once for 11.8 seconds. Sign-out interrupted normal
finalization, leaving the request terminal state `failed`; received text was
preserved. Keep its full $0.02 reservation charged pending invoice reconciliation.
No retry occurred and no second transcription attempt was provisioned.

Rollback must retain the new policy recognizer once funded. The original
`208ca34` policy reader cannot reopen the funded ledger; never restore old
spending data to make an older binary start. Deployment:
`dep-daukpurtqb8s73boufmg`. Native test build preserves deletion-enabled production
configuration and all 24 pre-install app files. The subsequent [physical receipt](../qa/account-capture-signout/physical-receipt.json)
records actual capture/sign-out and founder-reported switching/relaunch results.
This is not full account or TestFlight acceptance.
