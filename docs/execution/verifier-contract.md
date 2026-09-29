# Minimal verifier tooling and feature evidence map

Status: specification to implement in Phase 1, not an existing tool. Reuse current test scripts and fixtures; do not build an orchestration platform.

## Runner

Proposed entry point: `scripts/verify_checkpoint.py --packet <manifest>`. It executes a reviewed allowlist of checks declared for the packet, in dependency order. Default is offline/local. No provider transport, deployment or device interaction is enabled by a generic “all” option. Paid or physical checks remain explicit separately authorized operations whose receipts can be attached.

Use normal JSON and the Python standard library where sufficient. Store outputs under an ignored per-run directory. Record actual return codes, duration and evidence paths; fail on a failed command, missing required artifact, unresolved required check or mismatched source commit. Do not let a schema validator claim that an image looks right or a message is useful. Those require an explicit inspection result with the underlying output attached.

Required verifier self-checks: failing child command returns failure; missing required evidence blocks ready; replay is never labeled live; absent spend permission prevents any paid execution; stale commit evidence is flagged; logs redact credentials and do not copy private transcript text by default. The runner should not possess production credentials simply to run local tests.

## Receipt

```json
{
  "packet": "P1-A",
  "commit": "<verified SHA>",
  "base": "<base SHA>",
  "environment": "<OS/build/destination>",
  "checks": [
    {"name": "<behavior>", "command": "<reproducible command>", "result": "pass|fail|not_run", "evidence_kind": "fixture|live_provider|simulator|physical_device|review", "artifacts": ["<path>"], "limitations": []}
  ],
  "paid_calls": 0,
  "reserved_microusd": 0,
  "unresolved": [],
  "review": {"status": "pending", "reviewed_commit": null}
}
```

Attach backend commit and native build identity when testing their integration. Budget receipts record reservation capacity separately from actual billed/estimated cost. Never count test success as model quality success when replay intentionally reproduces a failure.

## Feature map

Extend `docs/features/` rather than create a competing source of truth. Each release-critical behavior gets:

- User outcome and implementation entry points.
- Owner and dependent contracts.
- Implemented, verified, merged, deployed and installed state separately, with version/date.
- Reproduction command and evidence receipt.
- Failure modes and recovery behavior.
- Known limitations and the next unresolved question.

First mapped behaviors: capture/stop/save/reopen; notes generation failure/recovery; main-chat follow-up; proactive trigger/cancel/Quiet/limits; fresh tester enrollment/isolation/revocation; install/update.

Orchestrator applies map updates at each verified checkpoint. Workers submit deltas in their reports. Do not let historical footnotes or accumulating summaries masquerade as current deployment status.

## Release readiness report

A small report joins required packet receipts at exact commits. Show ready, failed, missing and expired/stale evidence explicitly. It does not merge, deploy, purchase inference, upload TestFlight builds or invite testers. The orchestrator reviews the report, addresses failures and performs authorized release steps separately.

## Real-path acceptance requirements

Each packet manifest must distinguish `mechanical_checks`, `live_behavior_checks`, and `inspection`. Its completion gate requires every applicable category; explicit not-applicable decisions need a reason. A successful command cannot override an unmet semantic or visual criterion.

For model changes, attach the exact prompt/schema/model/configuration fingerprint, isolated scenario identity, fresh provider receipt, inspected response and resulting application turn/delivery evidence. Track the tested request separately from the code commit so a later prompt change makes the semantic evidence stale. Never include secrets. Note whether entry was provider-only, service-level or the active app pipeline; only claim the layer actually exercised. Capture latency and budget usage without silently retaining real-user content.

The report must flag these as incomplete: fresh model verification missing after a prompt change; only synthetic output for an LLM claim; UI claim without actual rendered inspection; device claim without that device path; required live check skipped for lack of budget. Reviewers compare observed results against criteria fixed before the run. The original implementer performs verification; orchestrator review checks evidence and targeted integration rather than automatically duplicating every paid call.
