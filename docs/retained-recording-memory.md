# Recording deletion and retained knowledge

Status: verified code checkpoint, September 26, 2026. Storage/writer behavior, live Jev/Luna context handling, saved-chat reopening and iPhone simulator presentation are verified. The [approved internal rollout](retained-memory-rollout.md) is live with matching native builds. The bounded physical-iPhone deletion, recall and reopen check has passed; see the rollout evidence.

## Product contract

Deleting an ordinary recording removes its transcript and library entry. Already learned knowledge may remain useful to the companion, with corrections, attribution uncertainty and temporal qualifications intact. A retained memory is not a viewable transcript or a verbatim quotation. Explicit memory erasure remains a separate future behavior. Legacy personal-text deletion keeps its existing invalidation behavior.

## Implementation

Schema 16 adds `retained_recording`: source identifiers, capture time, timezone and supported-passage speaker metadata. At deletion, committed evidence-writer claims retain their existing bounded supporting quotes, independent judgments, identity links and correction relationships. The full source payload, transcript indexes/embeddings, chunks, provider-response caches and live snapshots are removed. Unrelated transcript text is not copied into retained storage. Pending learning is cancelled; late writes and replayed source revisions cannot resurrect a deleted recording.

Retention requires the evidence writer's committed support records. Legacy claims without that evidence keep their previous invalidation behavior; this migration neither invents support nor backfills already deleted content. Retention does not identify an anonymous speaker as the user.

Recall supplies a distinct `retained_memory` item containing derived claim text, lifecycle and unavailable-source status. Bounded lexical discovery feeds the existing Jev ranking and correction expansion. Retained claims do not yet have a semantic embedding index; queries with no matching terms can miss them. Existing recordings retain hybrid retrieval. This is a known retrieval limitation, not a claim of exhaustive memory recall.

Original-source answers are invalidated when the recording disappears. New answers grounded in retained knowledge survive reopening and repeated recording deletion. Their references display “Memory … · recording deleted” without an open-source button. The authenticated source endpoint also rejects retained references. A later correction retires stale answer context through the existing fingerprint checks.

The answer prompt adds retained-memory instructions only when such evidence is supplied. Existing requests without retained evidence are unchanged. The app deletion confirmation explains that learned memories and supporting excerpts may remain.

## Local evidence

- 151 affected backend tests passed (149 in the combined run, the focused schema-15 upgrade check, and exact live-provider-response replay): retention, writer, identity, corrections, consolidation, temporal rules, migrations, retrieval, main chat, sockets, runtime and independent verification.
- `python3 Backend/retention_fixture.py <new-output-directory>` ran the actual writer with exact saved provider responses: learn Juniper → delete original → learn correction → delete correction → retrieve → save answer → reopen. The fixture's answer is deliberately injected for storage/UI QA; it does not establish live answer quality.
- Observed state: morning preference active, library superseded, community center active; both original transcripts unavailable. Saved retained-memory answer reopened as complete. Zero paid calls.
- Additional cases cover deletion in the opposite order, repeat deletion, owner isolation, deleted-source resurrection attempts, cancelled learning, in-flight original answers, later corrections, future/expired/unresolved claims, unrelated transcript removal and unchanged personal-note deletion.
- iPhone 17 Pro simulator, iOS 26.5: `PhoneUITests/CompanionPhoneUITests/testRetainedMemoryReferenceAfterReopen` launched the actual app against the local socket service, showed the retained answer and unavailable-recording label, found no source button, and reopened successfully. Screenshot inspected. This is not physical-device or microphone evidence.
- Mac and iPhone simulator app builds passed. Capture/transcription paths are unchanged; no additional STT test is justified by this slice.

Local artifacts live under ignored `work/retention/`: `offline/report.json`, `backend.log`, `phone-ui.xcresult`, `screenshots/`, and `mac-build.log`. Synthetic reproducible fixtures are checked in. No private conversation or provider credential is included.

## Live provider acceptance

The founder approved an additional $0.05, at most six calls, for this QA. The actual companion socket service and indexed recall used two live Jev rankings and three live Luna answers. Generation used the production prompt/settings via a non-streaming operator transport; this validates context and response behavior, not streaming latency. No transcription or extraction was repeated. The service's normal context deadlines remained in force.

Observed and reviewed answers:

- Corrected recall: community center is current; library is historical. The answer identifies its basis as remembered knowledge and cites a retained-memory reference.
- Exact quotation request: declines to invent the deleted recording's words and explains that only retained knowledge remains. The follow-up used saved chat evidence after retrieval returned no match.
- Account ownership: explicitly says the project's morning-meeting preference does not establish the user's personal preference.

All answers persisted through the real service, returned unavailable from the original-source endpoint, and survived a database reopen. The saved responses replay exactly through the same service with network disabled. Synthetic fixtures are in `Backend/fixtures/retained-memory/`; reproduce with `python3 Backend/evaluate_retention.py <new-output-directory> --replay Backend/fixtures/retained-memory/calls.json`.

Accounting: isolated allowance `retained-memory-20260926-005`; $0.05 reserved globally, $0.030497 conservatively reserved for five completed calls ($0.010497 Luna, $0.02 Jev), $0.019503 unused within that allowance. These are reservation ceilings, not an invoice. Global reserved total is $4.563868/$5. Funding is marked as an allocation so it does not consume a recording attempt; application quotas, runtime budget policy and Render plan are unchanged. No failures or automatic paid retries occurred.

## Remaining rollout acceptance

Code acceptance is complete; the physical-device check is a rollout gate, not a claim established by simulator evidence. Before physical-iPhone QA, explain the short deletion/recall check and wait for founder readiness. Do not start capture automatically.

Hosted opt-in is `VOICE_RETAIN_RECORDING_MEMORIES=1`, requiring companion mode. The code default is off; the founder-approved internal service now enables it after review, provider QA, backup and matching native update. Keep the existing Render plan and global spend cap. See the [rollout record](retained-memory-rollout.md).

Back up current databases consistently before schema migration. Rollback uses a schema-16-compatible binary and disables new retention; already retained knowledge remains readable. Never restore an old database to resurrect deleted recordings or reset usage charges. Historical backups remain governed by their existing retention policy; this implementation does not claim to erase every historical backup.
