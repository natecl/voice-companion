# Independent-verifier internal rollout

Founder approval: an additional $0.25 for rollout testing and internal learning within the unchanged $5 global cap. This is distinct from the isolated verifier QA balance. No hosting upgrade, automatic backfill, public release or recording-retention change is included.

## Preparation contract

The one-time operator grant `independent-verification-rollout-2026-09-26-025` reserves $0.25 globally before exposing it to the profile ledger. Existing attempts remain charged. The enabled profile cap becomes $3.45; the previous $3.20 cap stays unchanged for old callers. Sol reserves $0.04 per bounded call; Luna/Jev reserve $0.01 each. Restart, retries and flag activation cannot mint credit.

Funding uses available recording-category headroom while retaining all existing policies and the $5 aggregate cap. The global category identifies funding, not provider usage. `allocation_request` distinguishes this one allocation from actual recording attempts without excluding its dollars from money limits. Existing request records remain intact. Failed provisioning cannot expose local credit; an interrupted operator call can be resumed idempotently.

The hosted verifier flag requires the existing rollout and preference allocations plus the new globally reserved grant. With the flag off, the earlier behavior and allowance remain. No user transcript migration is required.

## Predeployment verification

36 focused checks passed across budget provisioning/exhaustion, no automatic retry, request admission, source verification and actual local hosted startup/history recovery. The first startup fixture still expected the old policy; it was corrected to use the provisioned preference policy. A proposed distinct allocation state was rejected by the existing SQLite constraint during tests; the final compatible implementation uses an explicit allocation marker instead. No failed candidate was deployed.

Existing provider-backed verification is recorded in `independent-source-verification.md`. New provider calls are reserved for a single short synthetic recording through the actual hosted sync/worker/companion path. Earlier source/correction and negative-case evidence remains applicable.

## Deployment and acceptance procedure

1. Check active requests/jobs and save consistent SQLite backups plus the existing Render configuration.
2. Provision the reviewed grant while the old worker still has its old exhausted cap.
3. Add `VOICE_ENABLE_INDEPENDENT_VERIFICATION=1` to the existing start command; retain Starter, offline embeddings, auto-deploy off and the other flags. Deploy the reviewed commit.
4. Verify health, exact running commit, unchanged original records and budget grant, and no automatic reprocessing.
5. Use a short-lived isolated QA identity to sync one synthetic preference. Inspect the actual worker's saved active memory and verifier rubric. Ask once through authenticated companion WebSocket, check source navigation, and revoke the credential. Do not repeat a failed paid check automatically.
6. Record observed cost, remaining allowance and limitations. This does not claim new physical-microphone or iPhone UI evidence.

Rollback: retain the compatible deployed binary and disable the verifier flag to contain new processing. Do not restore old source databases or resurrect deleted information. Preserve budget reservations and failed attempts. No old memory backfill is part of rollback or rollout.


## Completed internal rollout — September 26, 2026

[PR 79](https://github.com/natecl/voice-companion/pull/79) merged preparation at `3eba445781a03a77f737ea84205894c22569151f`. Render deployment `dep-das36h8jo6nc73a0vcug` is live at that exact commit with the independent verifier flag enabled. Starter, the existing disk, offline embedding cache and auto-deploy-off settings were retained. No phone rebuild was needed.

A consistent schema-15 SQLite backup is retained privately at `/var/data/voice-companion/companion-approved-czb56995`. Original source, claim, support, job and companion records matched the backup before QA; no historical sources were reprocessed. The grant was provisioned before deployment while the old worker remained on its exhausted cap.

Hosted behavioral evidence: a short-lived isolated QA identity synchronized the synthetic transcript “Project Spruce.” / “Prefers evening meetings.” through the authenticated `/memory` endpoint. The actual worker stored one active preference. Its persisted stages include `independent-source-v2:support` and `independent-source-v2:metadata`. The companion, without an attached recording, answered “Project Spruce prefers evening meetings. [[p1]]”; the citation reopened the original second passage and the saved answer was found in subsequent chat history. QA credentials were revoked. This is hosted backend evidence, not new physical microphone/iPhone UI evidence. See `Backend/fixtures/source-verification/rollout-evidence.json`.

The harness initially expected JSON from the plain-text `/health` route; this preflight error caused no provider call. Two answer submissions were then blocked by `daily_limit` before answer-provider access. Inspection found 39 counted Ask entries against a base limit of 20: 27 were prior gbrain calls and five were funding reservations. The first one-attempt grant alone was insufficient. A transaction preserved all history and added the exact offset needed to expose one available approved QA attempt (effective cap 40 against 39 prior entries). That attempt succeeded. No paid extraction/verification was repeated, no money cap was bypassed, and normal daily limits were not permanently increased. The current day's Ask allowance is exhausted again after the successful check.

### Final accounting and health

- New learning/recall calls: two Luna, one Sol, two Jev; $0.08 conservative reservations. The separate successful answer reserved $0.003 under the existing Ask budget. These are ceilings, not billed inference cost.
- Shared profile ledger: $3.28 of $3.45 reserved, leaving **$0.17** for internal learning/recall. The isolated verifier QA remainder stays separate.
- Global reservations: **$4.513868 of $5**. The $0.25 grant is counted once globally, not again per subledger call.
- Learning and indexing are idle, each with one completed synthetic job and no failure. No active requests, pending provider reservations or memory-limit/OOM events remain.
- The app retains its five-minute recording cap, best-effort speaker labels and existing daily limits. The accepted retained-memory-on-recording-deletion behavior remains a separate, unimplemented change.
