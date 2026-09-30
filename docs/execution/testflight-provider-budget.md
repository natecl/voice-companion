# TestFlight provider-testing allowance

Founder approval: September 29, 2026, $5 total for provider/API testing toward TestFlight readiness. No automatic paid retries. Excludes hosting upgrades, subscriptions and other purchases. This is a separate grant; preserve all earlier grants and charges.

Approval ID: `testflight-readiness-2026-09-29`.

| Limit | Reserved | Actual recorded | Remaining unreserved |
| --- | --- | --- | --- |
| $5.00 | $0.00 | $0.00 | $5.00 |

Before each paid run, record its purpose, provider/model, bounded call count, maximum cost, and reservation. Afterwards record observed usage/cost and sanitized evidence. Keep failed attempts charged until billing evidence supports reconciliation. Stop before a call whose maximum could exceed the remaining allowance. This ledger alone does not alter runtime quotas; any provisioning must preserve historical reservations and charges.

No paid calls have been made against this grant.

September 30 non-billable OAuth checks: two requests to Google’s token-revocation endpoint using wholly fabricated invalid tokens—one Python response-contract investigation, one explicitly opted-in Swift simulator adapter check. Both returned `invalid_token`; no real grant or account changed. No model calls or paid requests, $0 expected cost; the paid allowance remains untouched. Evidence: [Google revocation QA](../qa/google-account-revocation/README.md).
