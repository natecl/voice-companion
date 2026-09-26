# Recording deletion and retained knowledge

Status: implementation candidate, September 26, 2026. Local storage/writer replay and iPhone simulator presentation are verified. Live Jev/Luna checks, physical-iPhone acceptance and hosted enablement remain pending. No new paid calls have been made and the deployed service is unchanged.

## Product contract

Deleting an ordinary recording removes its transcript and library entry. Already learned knowledge may remain useful to the companion, with corrections, attribution uncertainty and temporal qualifications intact. A retained memory is not a viewable transcript or a verbatim quotation. Explicit memory erasure remains a separate future behavior. Legacy personal-text deletion keeps its existing invalidation behavior.

## Implementation

Schema 16 adds `retained_recording`: source identifiers, capture time, timezone and supported-passage speaker metadata. At deletion, committed evidence-writer claims retain their existing bounded supporting quotes, independent judgments, identity links and correction relationships. The full source payload, transcript indexes/embeddings, chunks, provider-response caches and live snapshots are removed. Unrelated transcript text is not copied into retained storage. Pending learning is cancelled; late writes and replayed source revisions cannot resurrect a deleted recording.

Retention requires the evidence writer's committed support records. Legacy claims without that evidence keep their previous invalidation behavior; this migration neither invents support nor backfills already deleted content. Retention does not identify an anonymous speaker as the user.

Recall supplies a distinct `retained_memory` item containing derived claim text, lifecycle and unavailable-source status. Bounded lexical discovery feeds the existing Jev ranking and correction expansion. Retained claims do not yet have a semantic embedding index; queries with no matching terms can miss them. Existing recordings retain hybrid retrieval. This is a known retrieval limitation, not a claim of exhaustive memory recall.

Original-source answers are invalidated when the recording disappears. New answers grounded in retained knowledge survive reopening and repeated recording deletion. Their references display “Memory … · recording deleted” without an open-source button. The authenticated source endpoint also rejects retained references. A later correction retires stale answer context through the existing fingerprint checks.

The answer prompt adds retained-memory instructions only when such evidence is supplied. Existing requests without retained evidence are unchanged. The app deletion confirmation explains that learned memories and supporting excerpts may remain.

## Local evidence

- 150 affected backend tests passed (149 in the combined run plus the focused schema-15 upgrade check): retention, writer, identity, corrections, consolidation, temporal rules, migrations, retrieval, main chat, sockets, runtime and independent verification.
- `python3 Backend/retention_fixture.py <new-output-directory>` ran the actual writer with exact saved provider responses: learn Juniper → delete original → learn correction → delete correction → retrieve → save answer → reopen. The fixture's answer is deliberately injected for storage/UI QA; it does not establish live answer quality.
- Observed state: morning preference active, library superseded, community center active; both original transcripts unavailable. Saved retained-memory answer reopened as complete. Zero paid calls.
- Additional cases cover deletion in the opposite order, repeat deletion, owner isolation, deleted-source resurrection attempts, cancelled learning, in-flight original answers, later corrections, future/expired/unresolved claims, unrelated transcript removal and unchanged personal-note deletion.
- iPhone 17 Pro simulator, iOS 26.5: `PhoneUITests/CompanionPhoneUITests/testRetainedMemoryReferenceAfterReopen` launched the actual app against the local socket service, showed the retained answer and unavailable-recording label, found no source button, and reopened successfully. Screenshot inspected. This is not physical-device or microphone evidence.
- Mac and iPhone simulator app builds passed. Capture/transcription paths are unchanged; no additional STT test is justified by this slice.

Local artifacts live under ignored `work/retention/`: `offline/report.json`, `backend.log`, `phone-ui.xcresult`, `screenshots/`, and `mac-build.log`. Synthetic reproducible fixtures are checked in. No private conversation or provider credential is included.

## Remaining acceptance and rollout

The concrete provider QA input is prepared in `work/retention/provider-qa-inputs.json`: three synthetic questions covering corrected recall, refusal to invent an exact deleted-transcript quote, and no account-owner inference. Proposed upper bound: three Jev rankings plus three Luna answers, no automatic retries, at most $0.05 after approval. Preserve actual requests/responses and repeat locally thereafter. No new extraction or transcription is required.

Do not merge as a completed feature until the changed model/context interaction is verified. Before physical-iPhone QA, explain the short deletion/recall check and wait for founder readiness. Do not start capture automatically.

Hosted opt-in is `VOICE_RETAIN_RECORDING_MEMORIES=1`, requiring companion mode. Default is off. Deploy only after review, provider QA and explicit internal rollout approval; install the matching native UI before enabling retention. Keep the existing Render plan and global spend cap.

Back up current databases consistently before schema migration. Rollback uses a schema-16-compatible binary and disables new retention; already retained knowledge remains readable. Never restore an old database to resurrect deleted recordings or reset usage charges. Historical backups remain governed by their existing retention policy; this implementation does not claim to erase every historical backup.
