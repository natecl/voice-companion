# Plans and usage limits

Feature ID: `pricing`. See [release handoff](../../execution/testflight-release-handoff.md).

## Current implementation

Backend admission, reservations and historical spending ledgers exist. They are internal QA/runtime controls, not a selected Free/Pro product or subscription entitlement system.

## Gaps and non-goals

Prices, allowances, billing periods and reset policy are undecided. No promised unlimited capture or silent quota increase. Pricing research cannot substitute for measured costs or founder decisions.

## Contracts and dependencies

Stable authenticated owner from access; verified subscription entitlement from subscriptions. Reserve atomically for concurrent capture/chat/notes/memory/proactive work; reconcile failures without duplicate charging. Existing notes stay readable at limits. Preserve historical charges. Coordinate shared admission/admin files with account and billing owners.

## Verification and delivery state

Planned, not implemented or accepted. Run `python3 scripts/verify_feature.py pricing`; [manifest](../verification/pricing.json). Required evidence: approved plan matrix and cost assumptions; actual authenticated concurrent enforcement/reset/upgrade/downgrade; clear UI at limits and retained access to saved notes. No dedicated plan automated suite exists yet; missing evidence must remain incomplete.

## Next bounded work

After Phase 1 account/data-lifecycle acceptance, start Phase 2: prepare a measured cost and allowance proposal, mark assumptions, get concrete founder selection, then implement server enforcement with local fixtures before paid integration checks. See [accounts](access.md) and [subscriptions](subscriptions.md).
