# Personal profile recall — checkpoint 3

Status: implemented and locally/provider verified; hosted rollout complete; physical iPhone acceptance pending. This checkpoint must remain unmerged until device acceptance. Checkpoints 1–2 are merged in PRs 29–30. No public release is implied.

## Behavior

Ask can select supported personal claims about the user and related people alongside current conversation context. Luna receives individual verified claims; Jev independently selects relevance using the existing batch. Original personal-note text is retained only for opening the source in the app. This prevents a superseded fact in a mixed note from leaking back into the answer through the original passage. Source buttons identify personal notes and saved answers preserve their original note, date and qualification.

Candidate limits: at most eight personal claims (5,000 model bytes), plus four ordinary passages; without personal candidates, the existing eight-passage fallback remains. The relevance request is capped at 16,000 bytes, combined answer data at 12,000 bytes, and selected source snapshots at 32,000 bytes. Relevance uses the existing three-second limit and confidence thresholds. Ownership, revisions and deletion are revalidated. Retired information is available only as explicitly historical evidence. No extra extraction or transcription call is needed for Ask.

Personal recall defaults off. Enable `VOICE_ENABLE_PERSONAL_RECALL=1` only with personal learning and existing memory recall enabled. The approved profile QA ledger covers answers as well as memory judgments while personal learning is enabled; ordinary admission caps still apply. Allocation exhaustion cannot create a new allowance.

## Observed QA

Synthetic sources cover family, student, friend and appointment contexts, learned by the real Luna/Jev pipeline in checkpoint 2. Live Ask checks used a copy of that evidence plus twenty unrelated newer meeting passages. They exercised the actual WebSocket Ask service and both providers, without microphone transcription.

| Case | Observed behavior |
| --- | --- |
| Paraphrased creative-weekend question | Suggested bird sketching and cited the older student note |
| Current daughter's sport | Answered tennis and cited the correction |
| Historical daughter's sport | Answered swimming with the earlier source and historical qualification |
| Unrelated arithmetic | Answered “Two plus two is four.” with no personal context selected |

The historical answer added unnecessary uncertainty about the current state, but correctly identified the requested past activity. These examples demonstrate a bounded internal profile, not general recall quality at scale: beyond eight competing personal candidates, lexical ranking and recency can still miss an older paraphrased fact. Voice identity and same-name entity resolution are not solved by this slice.

### Failures preserved and diagnosed

The first arithmetic request was rejected as `busy` before either provider ran. The preceding answer advertised completion before asynchronous QA accounting released admission. Completion now follows upstream cleanup and accounting. A local real-WebSocket test delays accounting and submits consecutive requests immediately on `done`; both succeed and admission is released before completion reaches the client. Final authorization/source validation remains in place.

Only the blocked live case was repeated. It answered correctly, but the evaluator required the numeral `4` instead of accepting the word `four`. The saved response was rechecked locally after correcting that assertion; no further provider call was made. Original events and failed assertions remain in local evidence. Source deletion was then verified against a local copy of the resulting database; physical deletion is still pending.

### Local and native verification

- 84 backend checks passed, covering admission, hosted service, learning, recall, profile ownership/lifecycle and answer contracts. These are local synthetic/fixture checks, not 84 paid calls.
- Eight focused Ask tests passed again after final completion authorization/source validation.
- Eight native answer tests and five memory tests passed in the first native run. The remaining socket test initially failed because the command omitted the configured Python runtime and selected Python without `websockets`; it passed when rerun with `TEST_RUNNER_VOICE_TEST_PYTHON` set. No production code change was made for that environment error.
- Four Mac UI tests passed across answer/source and personal-note sync behavior. The final focused personal-source test passed again; its exported screenshot was inspected and showed the original mixed note and personal-note source label. These are synthetic app fixtures.
- iPhone simulator build passed. Physical iPhone acceptance is not yet claimed.

Local evidence: `work/profile-recall-backend-final.log`, `work/profile-ask-completion-final.log`, `work/profile-recall-core-final.log`, `work/profile-recall-socket-final.log`, `work/profile-recall-native.log`, `work/profile-recall-native-final.log`, `work/profile-recall-phone-build.log`, `work/profile-live-recall-v1.log`, `work/profile-live-recall-irrelevant-v2.log`, and `work/profile-recall-screens/`. These working files are intentionally untracked.

## Aggregate QA accounting

Approval `personal-profile-qa-2026-09-25-100`: $1 maximum across checkpoints 2–3. At this checkpoint, 38 calls total: 15 Luna and 23 Jev, conservatively reserved at $0.01 each. $0.38 reserved; $0.62 remains. This is reservation accounting, not verified billing. Checkpoint 3 added eight calls. The rejected `busy` request used none. All provider calls used the canonical hosted subledger; local evidence copies cannot authorize spend. No automatic paid retries.

## Concrete internal rollout and remaining gate

After rollout authorization:

1. Confirm no active capture/Ask or queued learning jobs that would unexpectedly consume the QA allowance. Preserve the canonical usage and profile ledgers. Make a consistent SQLite backup on the persistent disk before migrating memory schema 2 to 3. Record the deployed commit and migration evidence.
2. Deploy this reviewed branch commit to the existing private-trial Render service, keeping automatic deployment off. Enable personal learning and personal recall with the existing memory flags and approved allocation. Verify health and existing owner mapping; never enroll a replacement identity merely to bypass quota or access failures.
3. Build/install the matching iPhone app with its existing identity and configuration. Wait for explicit founder readiness before manual QA.
4. Use synthetic personal text only: save an interest/relationship note; from another session ask a relevant question and open the source; save an explicit correction; ask again; relaunch and reopen. Delete the personal sources in the app and inspect service deletion and recall eligibility. Reserve a maximum of 20 additional provider calls ($0.20 conservatively) for these two notes/two Asks; stop and reassess rather than retry blindly if anything fails. Confirm daily Ask admission permits the two planned requests, using only explicit date-scoped QA grants if required, never quota resets.
5. Record physical results, final spend and deployed/native commits in this document and PR. Review and merge only after acceptance passes.

Rollback: disable both personal flags to isolate the feature while retaining source data and the current-schema binary. Do not deploy the old schema-2 binary against schema 3. A database restore requires review of post-backup changes, especially deletions; never silently resurrect deleted content. Prefer a forward fix. Hosted rollout and physical QA remain outstanding, not passing by proxy from local tests.

## Approved rollout — September 25, 2026

Founder approved deployment in the task. Deployed implementation `85e72cd8dd630c529b9fc7a043e7cc0b9cc5f229`, Render deployment `dep-darh9k0jo6nc73fvindg`. Both personal flags are enabled; automatic deployment remains off. The running process reports that exact commit, `/health` returns 200, memory schema is 3 and SQLite integrity is `ok`. Existing owner mapping is unchanged. Jobs remain five done/one obsolete; no active or queued work was carried into rollout.

All three canonical databases were backed up with SQLite's backup API to `/var/data/voice-companion/backups/personal-profile-85e72cd` before migration, and each backup passed integrity checking. Usage history and the canonical profile allocation were preserved. There were zero Asks today under the existing 20/day policy, so the planned two questions need no grant. Profile spend is unchanged at 38 calls/$0.38 reserved.

Built and installed the matching signed `ai.voicecompanion.phone` app on the existing physical iPhone 16 Pro without re-enrollment. Evidence: `work/profile-phone-device-build.log` and `work/profile-phone-install.log`. Installation is not behavioral acceptance. Waiting for founder readiness before opening or exercising the manual flow; this PR remains draft and unmerged.
