# Memory recall checkpoint — local evidence and rollout proposal

September 25, 2026. Checkpoint 3 is implemented locally and **not complete**: hosted enablement is verified; physical-iPhone memory acceptance remains pending. Follow the canonical engineering principles. The founder approved rollout after reviewing persistent storage; see the deployed-state record below.

## Implemented path

An explicitly memory-enabled question includes its current session ID. Old requests remain compatible. The backend validates the current snapshot, reserves one Ask, looks up the authenticated owner's past sources and lifecycle annotations, and shortlists at most eight passages. Jev judges relevance and historical use in one batch; this is not a pre-search gate. Code filters retired evidence unless selected for historical use. Luna receives the unchanged current snapshot plus bounded selected history. Source manifests arrive before text; current references use p IDs and past references use m IDs. Each past reference includes session, revision, passage, timestamp and lifecycle metadata. The client saves source excerpts and presents their capture date.

Candidate lookup is a bounded lexical/context overlap ranking with a recent fallback, not embedding search. It considers both learned records' lifecycle and raw source passages, so useful unextracted details can be found. Anonymous speakers are not user identities. The profile remains empty without supported user attribution. A source can appear twice when the same supported claim was independently recorded in two sessions; source IDs remain distinct. This is provenance, not duplicate retrieval of the same session/passage. Semantic coverage across a large library is not proven by this small corpus.

Lookup includes both current and historical evidence. Jev returns relevant, historical, irrelevant or uncertain; selection requires probability ≥0.90 and confidence ≥0.60. These are gates, not accuracy guarantees. Retired evidence selected as current is rejected in code. Historical evidence carries its retired status through the prompt, including correction links. Historical/current final-answer grounding remains a model behavior validated on the small test set, not a deterministic natural-language correctness guarantee.

Limits: shortlist ≤8 passages / 7KB; Jev request ≤16KB; combined current input plus selected sources ≤12KB. No current transcript is removed to accommodate history. Recall preparation has a three-second service deadline within the existing twenty-second generation deadline. On unavailable recall, Ask emits a visible past-context-unavailable notice and makes one current-context Luna call. It never claims that no memories exist merely because recall failed. No-match means the bounded search supplied no match.

A consistent owner snapshot hash guards selected context before generation, periodically while streaming and before completion. A source/lifecycle change cancels the answer; the client clears its partial text and copied past sources. This is deliberately coarse: an unrelated owner-memory change may also require asking again. No automatic paid retry. Provider cancellation can leave the already-started HTTP operation billable; its reservation remains spent.

Existing Delete session removes dependent local answers and their source copies before removing the source file. Durable deletion tombstones replay that cleanup after a crash. Server deletion prevents fresh retrieval. Full cross-device session/deletion synchronization remains deferred: this internal rollout enrolls one phone; do not claim an offline second device's previously saved copies are remotely erased. Server answers are not separately persisted.

## Verification

- `work/memory-recall-backend.log`: 59 backend checks passed, including actual local authenticated Ask WebSocket → recall → context event → streamed answer → citation completion, source deletion during generation, unavailable recall fallback and owner isolation. These use deterministic provider fixtures.
- `work/memory-recall-native-focused.log`: existing memory synchronization, answer and live-Ask checks plus new past-source persistence/deletion and partial-answer invalidation checks passed. Earlier broad native run used a Python without fixture dependencies and failed; the runner was corrected to the configured Python 3.13 interpreter, without changing product code to hide the failure.
- `work/memory-recall-ui.log`: actual Mac UI opens a dated past transcript source and retains its link after app relaunch. Screenshot inspected from `work/memory-recall-screens`; not committed because desktop surroundings are visible. This is synthetic UI QA, microphone off.
- `work/memory-recall-phone-build.log`: iPhone simulator build passed. This does not establish physical-iPhone behavior.
- `Fixtures/memory-recall-cases.json`: three fixed live cases. Existing synthetic learning responses seed the writer/store without paid re-extraction. Real Jev retrieval followed by real Luna answers passed **3/3**: Nora agenda preference; corrected Birch expiry September 29; original expiry September 28. Manually inspected answers and source IDs. No new transcription calls.
- `Fixtures/memory-recall-provider-responses.json`: exact synthetic retrieval requests/responses and answers for future offline reproduction. Contains no real conversations or API keys. Keyword checks accompany manual semantic inspection, not replace it.

Six paid calls (3 Jev + 3 Luna), no retries, consumed $0.03 of conservative call reservations inside the existing $0.25 memory allocation. Cumulative allocation reservations are $0.185; $0.065 remains. These are reserved ceilings, not invoice charges. The global $5 ceiling and all earlier charges remain intact. No new grant or copied/reset subledger.

Useful commands:

```sh
python3 -m unittest discover -s Backend -p 'test_memory_recall.py' -v
python3 -m unittest discover -s Backend -p 'test_ask.py' -v
```

`Backend/evaluate_recall.py` is an explicit paid QA runner and refuses to overwrite its results file. Do not run it again for UI/storage debugging. The passing sample is not a broad paraphrase/relevance benchmark. Remaining acceptance includes longer-library recall and the planned founder phone sequence; do not merge checkpoint 3 as complete yet.

## Concrete hosted rollout proposed for founder review

Use the existing single-instance Render service and 1GB persistent disk; no new service, disk size, subscription or provider model. Auto-deploy stays off. Deploy the reviewed checkpoint commit outside active recording/Ask. Preserve and back up the usage ledger using SQLite's backup API. Transfer the one canonical memory subledger and receipt to persistent storage, then retire local spending from it; never create a second active copy. Set the existing server provider credentials and enable MEMORY, MEMORY_LEARNING and MEMORY_RECALL flags. Provision one stable memory owner and renew the founder phone's internal credential for that owner. Old untracked sessions are not imported.

New, opted-in listening sessions will retain transcript passages and derived memories on the existing server until session deletion. Jev/Luna receive the relevant transcript context for learning/answers. Provider retention is not established as zero. Deletion scrubs live source content, unsupported derivatives and cached learning responses; identifiers/tombstones and usage accounting remain. Internal retirement keeps valid history.

Render documents encrypted daily disk snapshots retained for **at least seven days**, not a guaranteed seven-day maximum. Deleted data may remain in these platform copies. Its documentation advises database-native backups rather than restoring disk snapshots for custom databases. See [Render persistent disks](https://render.com/docs/disks), checked September 25, 2026. Do not promise immediate erasure from backups.

For this founder trial, no automatic memory backup/restore job is added. Never put a pre-deletion database snapshot back into live use. On corruption, disable memory and continue current-context Ask; any recovery requires a separately reviewed SQLite restore and reconciliation with the latest phone deletion tombstones/source revisions before re-enabling. If the current tombstone history cannot be recovered, do not serve the restored memory. Platform snapshot restore is not the recovery path. This manual fail-closed policy is intentionally limited to the internal trial.

After rollout approval, verify migrations and preserved accounting, provision/install the tested phone build, then wait for founder readiness before manual QA. Planned sequence: session A states a simple non-sensitive preference; session B asks about it without restating it; session C corrects it; Ask uses the correction; open and reopen source references. Use short recordings within existing caps. No merge as complete until physical-device acceptance passes.


## Approved rollout — September 25, 2026

Founder explicitly approved enabling memory after reviewing the storage change. Render deployment `dep-dardqku0tbcc73b6m0jg` went live at 20:46:00 UTC with tested implementation `890798f735cfc5c2130bba76ebb4a8e5b5b8f4d1`. Existing service `srv-daqtfs7lot8c73dleuug`, existing 1GB disk and manual deployment policy remain. Three memory feature flags are enabled and the existing TypeSafe credential is server-only.

Preflight verified zero active requests and created a SQLite usage backup (`usage-before-memory-890798f.sqlite`) on persistent storage. Startup verified memory schema 2, initially zero sources, preserved 37 memory attempts/$0.185 reserved, and unchanged global reservations of $0.555. The canonical memory budget and receipt were transferred with matching SHA-256 checks; local originals were renamed to read-only evidence files, so existing local QA runners cannot spend that allocation. No budget reset or new grant occurred.

An authenticated empty-source upsert over the hosted WebSocket was acknowledged; the actual background worker completed its empty job without inference. Deletion was acknowledged afterward. The identifier-only probe tombstone remains, not a user transcript. Provider call count and reserves were unchanged. This proves deployed synchronization, migration and worker connectivity, not phone audio or model quality.

The signed `890798f` app was built and installed on the connected physical iPhone 16 Pro. A seven-day memory-enabled internal credential was securely imported into device-only Keychain; transfer-file disappearance confirms the import path completed. Temporary local/server credential exports were deleted. Stable owner/credential identifiers are retained in ignored operational metadata for renewal. The app was launched with `--relay-check`, which does not record or call a provider. No old untracked sessions were imported.

Evidence: ignored `work/memory-rollout-*.log`, deploy JSON, and enrollment metadata. The installed app and server are prepared. Still wait for explicit founder readiness before the short microphone learn → recall → correct → recall-correction sequence. PR #28 remains draft/unmerged until that acceptance passes.

## Physical phone progress and correction defect

The founder recorded the Project Maple morning preference (A), then a separate neutral schedule session (B). Ask in B returned “Project Maple prefers morning meetings. [[m1]]”; the saved native answer contains `memoryStatus=available` and an m1 source pointing to A's exact passage. This proves initial cross-session recall on the phone.

The founder then recorded correction C: afternoon meetings instead of mornings. Its transcript synchronized and Luna extraction was correct, but Jev source support rejected it. PR #28 remains draft: do not mark correction acceptance complete or ask for more audio. See the [source-support replacement and preserved failure evidence](memory-learning.md#source-support-replacement-during-checkpoint-3). Next deploy the verified replacement, recover C through guarded cached-stage review, and after founder readiness ask the same question in B; verify the afternoon answer and source C.
