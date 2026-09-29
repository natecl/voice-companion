# Minimal verifier tooling and feature evidence map

Status: initial local runner implemented as the Phase 0 orchestrator prerequisite. Workers use it before submitting their first checkpoint. It is an evidence collection/review aid, not a sandbox or proof of semantic correctness.

## Runner

Entry point: `scripts/verify_checkpoint.py --packet <manifest>`. It executes a reviewed allowlist of checks declared for the packet, in dependency order. Default is offline/local. No provider transport, deployment or device interaction is enabled by a generic “all” option. Paid or physical checks remain explicit separately authorized operations whose receipts can be attached.

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


## Orchestrator review receipt

Extend `review` with reviewer identity, reviewed commit, inspected artifacts/checks, semantic/visual judgments where applicable, disposition (`accepted_for_integration`, `changes_required`, `blocked`) and the explicitly released next packet IDs. The runner may collect evidence and flag missing requirements; it cannot self-approve the review. A changed implementation/configuration requires review of its affected evidence before continuation.

Add persistent note-summary caching to the feature map: account/revision cache keys, disk persistence, immediate cached render, foreground/open refresh, request coalescing, offline/error behavior, known-revision invalidation, deletion/sign-out/reset clearing and actual UI evidence. Distinguish a server read from paid regeneration.


## Using the implemented foundation

Commit your packet and changes first. From the checkout:

```sh
python3 scripts/verify_checkpoint.py --packet docs/execution/packets/verifier-foundation.json
```

The command prints a private receipt path under ignored `work/verification/`. Exit 0 means evidence is collected and awaiting review; exit 1 means required checks/evidence are incomplete; exit 2 means the packet/source identity is invalid. Neither exit 0 nor a worker's report is orchestrator acceptance. Raw child output is intentionally discarded to avoid persisting credentials or private transcript contents; exact commands, exit codes and durations remain in the receipt. Rerun a failing command locally with appropriate safe diagnostics to investigate.

Only reviewed commands in the Python `REGISTRY` execute. The initial registry includes verifier self-tests and existing offline proactive/admission checks. The orchestrator adds narrowly scoped commands before assigning a packet. Environment credentials are not forwarded, but this is trusted-code execution, not network isolation. No automatic paid/device/release command exists. Real-path checks run separately under their explicit authorization and attach evidence receipts.

Each manifest declares all three evidence categories with checks or explicit not-applicable reasons. External receipts include `commit`, `kind`, `result`, `procedure`, `observed` and underlying checkout-relative `artifacts`. Live-provider receipts also include `request_sha256`, `model`, `ledger`, `pipeline_layer`, `paid_calls` and `reserved_microusd`. Use one accounting receipt per paid run to avoid counting a shared run twice. Receipt declarations are subject to orchestrator inspection; metadata cannot establish that a call actually happened. Artifacts are hashed and rechecked during review.

After inspecting the exact code and artifacts, the orchestrator records a decision:

```sh
python3 scripts/verify_checkpoint.py --review-receipt work/verification/<receipt>.json --reviewer orchestrator --decision accepted_for_integration --notes 'Describe inspected behavior and evidence' --release <next-packet>
```

This writes a new reviewed receipt. The CLI records the review; it cannot authenticate a reviewer or prevent a worker from falsifying metadata. Workflow enforcement belongs to this orchestrator and repository review protections. It never merges or deploys. Native build/backend IDs and semantic/visual judgments belong in external evidence and review notes; automated comparison of every environment field is not implemented. A cross-packet release dashboard is deferred until actual packets need it.

## Feature-linked entry points

Start with [the product feature verification map](../features/verification-map.md). Its catalog links each feature to implementation paths, reviewed test modules and a dedicated acceptance manifest. Run `python3 scripts/verify_feature.py <feature-id>`; use `--list` to discover features. The full verifier requires feature-specific real-path evidence and inspection, not merely unit tests.

`--checks-only` explicitly collects mechanical evidence only and cannot release dependent packets. Planned features with no automated suite report blocked rather than fake success. Full runs remain incomplete until their declared external evidence exists for the exact commit. The normal orchestrator review command can accept a full-feature receipt after inspection. No feature is marked verified at collection time.

Before assigning any worker, select its feature IDs and update their manifests to the bounded acceptance criteria of the job. Preserve required failure cases and actual pipeline/UI/device checks. The map is a verification contract, not a claim that all listed features work or have been deployed. Deferred connectors and subscription previews retain explicit limitations.
