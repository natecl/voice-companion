# Internal rollout preflight

> Historical rollout preparation. Hosted activation and bounded physical acceptance were subsequently recorded; the budget and pending gates below are checkpoint-time evidence, not a new execution allowance. See [current state](current-state.md) for selected behavior and current evidence boundaries.

September 26, 2026. The founder approved the additional $0.50 QA allocation and internal rollout, and explicitly declined the Render plan upgrade. Keep Starter (512 MiB); qualify capacity before enabling semantic retrieval. Hosted activation and physical acceptance are still pending.

## Canonical-copy migration

A read-only connection to each hosted SQLite database produced private backups after confirming no active requests. SQLite `data_version` stayed unchanged across the three backups; SHA-256 hashes verified the transferred files. Only explicitly named database/manifest members were extracted into ignored, private `work/rollout-preflight/`; no transcript content, credential data or database files are committed.

The current hosted memory schema is **3**. Running the new MemoryStore constructor on a separate copy upgraded it to **15**. Integrity and foreign-key checks passed. Every original column/row remained identical in owner (1), credential-owner (1), source (8), claim (5), support (4) and job (9) tables, including source payloads, revisions, tombstones and job states. Usage and memory-budget files remained byte-identical. Zero embedding jobs were backfilled and zero paid calls occurred. A fresh backup is still required immediately before deployment because new activity can happen after this preflight.

## Durable interface activation

`--companion-ui` remains a one-launch preview. `--enable-companion-ui` persists internal activation, so quitting and reopening normally keeps the main chat/library interface. `--disable-companion-ui` reverses that local activation without deleting recordings, chat or memory. The existing installed default remains off until activation is explicitly invoked. UI tests use owner-specific QA preference keys, leaving the user's normal activation untouched. Mac and iPhone simulator tests enable once, remove the activation argument, relaunch and verify restored main-chat history.

## Approval scope

1. **Declined; do not apply.** The earlier proposal was to upgrade this Render service from 512 MB Starter ($7/month) to 2 GB `1c-2g` / Standard ($25/month), approximately **$18/month additional compute**, for model/concurrent-work headroom. Prices were checked against [Render's official pricing](https://render.com/pricing). Linux resource acceptance is still required after the approved change; the 512 MB instance has not been proven to fail, and no model was loaded there during preflight.
2. **Approved:** **$0.50 additional bounded memory QA** within the existing **$5 overall cap**. Proposed category redistribution moves unused recording capacity: STT $2 → $1.50, Ask $2.50 → $2.85, Jev $0.50 → $0.65. Reserve the additional allocation once ($0.35 Ask/$0.15 Jev) and expose it in the canonical profile/rework subledger, raising that allocation from $2.40 to $2.90. Its current reservations are $2.38. This does not refund old attempts or authorize automatic retries. Category-policy/provisioning changes must be implemented and tested under this explicit approval before enablement.
3. **Approved:** the internal deployment and activation of the reviewed memory runtime/main-chat interface. Public release remains out of scope. Prepare the persistent model cache explicitly; do not enable semantic startup until its offline load is ready. Confirm migrations, resource headroom, worker health, source/index coverage and budget admission before manual testing. Do not bulk reprocess existing sources or silently retry failed paid jobs.

The physical gate uses two short fictional captures and bounded questions: ask during continued capture, navigate chat/library, stop and reopen, attach a recording, follow up, verify a correction, relaunch, then delete the test sources and inspect dependent removal. Keep claims about unnamed recording speakers unresolved. The allowance covers up to 52 remaining conservative one-cent memory/model reservations; direct companion answers retain the existing admission accounting, with a planned maximum of six. Stop before a necessary run would exceed a cap and ask for a concrete increase. Do not weaken quality to fit the allowance.

Describe the exact device steps and wait for founder readiness before the physical check. Deployment approval is not readiness for a timed recording or permission to bypass device/security prompts.


## Approved allowance implementation

`provision_rollout_allowance` is an explicit operator action, never a startup grant. It transactionally redistributes the exact approved category caps and reserves Ask $0.35/Jev $0.15 once before exposing the $0.50 sub-allocation. Conflicting receipts or recording usage above the reduced cap roll back the policy change. The $5 total and all historical reservations remain unchanged. Runtime opt-in `VOICE_ENABLE_ROLLOUT_QA=1` validates both global and profile receipts and requires rework. Existing callers retain their prior cap.

Focused QA exercises the real SQLite ledgers, repeated provisioning, cap exhaustion, paid-retry rejection, conflict rollback, refusal to erase recording usage, and reopening through the actual service policy. The hosted-process check starts with the new allowance and proves history access does not spend provider credit.
