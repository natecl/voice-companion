# Learned lessons for future work

These are engineering observations and decisions, not new product requirements. Follow the [canonical principles](../engineering-principles.md); use the [feature map](README.md) to locate the affected layer. Avoid storing personal transcripts, secrets or mutable credentials in this guide.

## Diagnose the exact stage

| Symptom | First inspection | Lesson / evidence |
| --- | --- | --- |
| Transcript displayed incorrectly | Saved provider events, transcript reducer, native rendering | Replay events; another paid audio run usually adds no evidence. [Capture evidence](../v1-acceptance.md) |
| Recording stopped unexpectedly | Stop reason, permission, audio interruption/input route, connection, duration/quota | An incoming call can interrupt before answer. Preserve received text and report the reason; don't bypass permissions. [Edge cases](../reliability-edge-cases.md) |
| Saved locally but unavailable to memory | Outbox acknowledgment, source revision, upload state | Local persistence and backend learning are separate milestones. [Foundation](../memory-foundation.md) |
| Learning says done but nothing remembered | Accepted-claim count, cached extraction and each verification judgment | Job completion is not useful-memory acceptance. Cedar passed support/identity but failed time classification. [Cedar](../uncertain-memory-time.md) |
| Correct answer despite missing learned claim | Actual selected evidence type and lifecycle | A model can answer from the original transcript. That does not prove extraction, identity linking or supersession. [Initial rollout limitations](../companion-internal-rollout.md) |
| Wrong person/profile attribution | Source provenance, named subject, speaker label, identity evidence | Never promote a speaker number to the account owner; don't force every mentioned person into the user's profile. [Identity](../memory-identity.md) |
| Old fact returned after correction | Candidate retrieval, identity/relation/applicability, related evidence expansion | “More recent” is not sufficient; an unresolved supported change should not silently look settled. [Transitions](../memory-identity-transitions.md) |
| Supported memory absent from answer | Search candidates, ranking, bounded context packet, then answer | Isolate retrieval from generation. Ranking usefulness and factual verification are different jobs. [Recall](../memory-indexed-recall.md) |
| Deleted recording still opens or answer disappears incorrectly | Reference type, tombstone, chat dependencies | Original-source and retained-memory references have different lifecycles. [Retention](../retained-recording-memory.md) |
| Request hits a limit | Daily attempts, global/category reservations, model subledger separately | More dollars do not automatically grant another recording/Ask. Preflight before involving the founder. [Final rollout](../retained-memory-rollout.md) |
| UI fixture fails before app behavior runs | Python/runtime dependencies, fixture launch environment, process output | A harness failure is not an app regression. Preserve failed output and rerun only the affected layer. [V1 acceptance](../v1-acceptance.md) |

## Decisions worth preserving

**Separate factual support from metadata confidence.** Cedar's undated location was supported while Jev's current-time probability was 0.59, below the unchanged 0.90 gate. The fix retained unresolved knowledge, not a weakened threshold or an invented date. Explicit unverified dates still fail. Keep the original proposal/judgment audit. Regression: `Backend/test_uncertain_memory_time.py`.

**Models earn specific roles.** Current recording verification uses Sol for source entailment, Jev for modality/time and other bounded judgments, and Luna for extraction/recording identity. The gbrain comparison did not authorize adoption; the founder chose our backend. Do not revert to old model-role descriptions based on an earlier research document. [Verification decision](../independent-source-verification.md), [comparison](../gbrain-comparison.md), [canonical revisions](../engineering-principles.md).

**Verify the full evidence boundary.** A standalone verifier pass is insufficient if its cited passage is dropped by extraction or the writer cannot commit it. Preserve bounded original passages actually used by the verifier, while retaining exact source spans and size limits. Exercise extraction → verification → atomic write → retrieval, including negative cases. [Verification rollout](../verification-rollout.md).

**Uncertainty should preserve useful information without claiming certainty.** Unknown identity and timing belong in stored/context metadata. They must not authorize profile attribution or current-state replacement. Answers should express uncertainty when relevant to the question, not mechanically add unrelated disclaimers. Cedar's physical answer used “From what I remember”; this did not prove every temporal question will receive a precise caveat. [Final evidence](../retained-memory-rollout.md).

**Deletion semantics changed intentionally.** Ordinary recording deletion now retains eligible learned memories and supporting excerpts. Historical cascade tests document the old contract. Do not restore the old cascade to make an old test pass, and do not equate recording deletion with complete memory/account erasure. Revision, personal-text deletion, backup retention and explicit erasure are separate concerns. [Product decision](../product-source-of-truth.md#recording-deletion-and-retained-memory--september-26-2026).

**A deployed feature can still have a bounded limitation.** Retained-memory retrieval is lexical; expiry supports a narrow explicit date form; anonymous speakers remain unidentified; real-time diarization is best-effort. Keep these visible rather than calling the entire harness universally accurate or reopening every verified subsystem for each change.

**Recover failures without erasing their history.** Cedar recovery used the guarded empty-job review path, reused four exact cached verification responses, and made only the necessary two relationship/identity calls. The old zero-claim job remained evidence. Recovery required deployment approval; it was not an automatic retry or quota reset. [Recovery record](../uncertain-memory-time.md).

## Minimum context before changing a feature

State the intended user outcome, identify its feature entry and active code path, and read the linked current contract. Follow the flow to its immediate upstream/downstream dependencies. Name the invariant at risk and the smallest realistic QA that can prove it. Keep backend, simulator, physical-device and founder-observed evidence distinct. Do not copy historical budget balances into a new allowance or infer a provider run is free.

After verification, update only changed status/ownership/contracts and add a durable lesson if something newly learned would alter future work. Keep detailed commands, fixtures and failed runs in the relevant checkpoint evidence. This map should reduce rediscovery, not become a second implementation or an activity log.


### Isolate notes UI runs while preserving relaunch evidence

A native fixture owner keys both backend evidence and the app's saved session directory. Reusing that owner across failed test runs leaves valid older recordings behind; deleting the current recording should not erase those sessions. Use a fresh owner/server directory per independent run and the same owner only for the relaunch portion. `scripts/qa-recording-notes-phone.sh` enforces this. Keep failed receipts; distinguish macOS static-text values from iOS labels, scroll controls into view, and scope duplicate nested iOS alert elements before tapping. These are fixture/driver corrections, not permission to remove product persistence or loosen deletion behavior.

### Notes are a discovery layer, not complete evidence

The [offline comparison](../notes-retrieval-comparison.md) recovered required evidence in 7/7 small notes-expansion cases versus 6/7 lexical-only candidates. This is not a full-harness accuracy result. A controlled summary omission defeated both note discovery and cited-passage expansion; direct transcript fallback remains necessary. Deleted notes cannot replace independently retained learned knowledge. Preserve these contracts when consolidating, and measure matched answers before replacing the deployed retrieval path.

### Notes index foundation

Schema18 indexes sourced note entries transactionally and invalidates them with their source. Use `Backend/notes_search.py` for the new bounded candidate boundary; it is not yet connected to the deployed companion. The [consolidation plan](../notes-first-memory-plan.md) records actual migration/search QA and the remaining Jev/answer gate. Keep runtime retrieval claims separate from this storage checkpoint.

### Notes can change usefulness judgments even when evidence is duplicated

In the [matched semantic comparison](../matched-recall-comparison.md), adding note versions of two competing venue reports caused Jev to classify the unconfirmed alternative as topical. Notes-first then omitted that side of the disagreement while indexed recall preserved both. Treat omitted counterevidence as an acceptance failure even when the answer still says it is uncertain. Preserve the failed candidate pool and judgments; do not count shorter incomplete answers as a cost improvement or tune thresholds to one fixture.

### Summary duplication and disagreement selection

The notes-first comparison lost one of two uncertain venue reports. Ranking summaries and their original excerpts separately changed the candidate pool, and a helpful/topical hard cutoff removed counterevidence. The unified candidate ranks original excerpts once and reserves two discovery hits independently of Jev. Ten-case QA restores the frozen disagreement and preserves abstention on an absent ticket price. This bounded reserve can include noise; do not treat it as exhaustive recall or general relevance proof. See [checkpoint evidence](../simple-memory-foundation.md#approved-checkpoint-2-qa-result).
