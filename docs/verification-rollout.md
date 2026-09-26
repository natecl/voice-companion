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
