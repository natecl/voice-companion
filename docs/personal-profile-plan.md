# Personal companion profile — implementation plan

> Historical/bounded delivery document. The [current product definition](product-source-of-truth.md), [current state](current-state.md) and [release handoff](execution/testflight-release-handoff.md) govern positioning, selected implementation and the current sequence. The September 28 gap audit is historical. Older one-liners, exclusions and pending stages below retain their original checkpoint meaning.

Superseded delivery direction: the founder-approved companion-first architecture is now planned in [memory rework](memory-rework-plan.md). Retain this document as checkpoint history; its failed correction gate remains unresolved, not accepted.

Status: checkpoints 1–2 implemented and verified within their bounded scopes; checkpoint 3 implemented with local/provider QA; hosted rollout complete; physical acceptance pending. See [historical recall evidence](https://github.com/natecl/voice-companion/blob/c3b8e9a1ccc6e3355ee3a7fe63fcd075b4f195df/docs/personal-profile-recall.md). See [learning evidence](personal-profile-learning.md). See [foundation evidence](personal-profile-foundation.md). Founder direction, September 25, 2026. Follow the [engineering principles](engineering-principles.md) and [product source of truth](product-source-of-truth.md). Voice recognition follows this slice.

## Outcome and boundary

The companion remembers the person and their life: relationships, family, pets, background, interests, routines, preferences, values, goals and current circumstances. These are flexible examples, not mandatory profile fields. Relevant understanding helps across journaling, appointments, lectures, meetings and everyday conversations. Do not infer personality, diagnoses, family roles or permanent traits from sparse evidence.

Complete means: explicit personal input → automatic supported profile memory → useful source-linked answer → correction → corrected answer → persistence and source-deletion verification on iPhone. This is an internal slice, not a public-launch declaration or a promise to remember everything.

The existing profile query only selects stated preferences with subject `user`; the writer does not establish that subject. Recall currently selects source passages. Broader profile learning and retrieval therefore require implementation, not just prompt wording.

Reuse the existing SQLite store, source synchronization, Luna extraction, independent Jev verification, lifecycle and answer-source contracts. The profile is a derived view of supported memories, not a second biography database or a generated summary that becomes its own evidence. No new provider, graph database, broad UI redesign, voice enrollment, bulk historical ingestion or proactive companion behavior.

Provide one small explicit personal-text entry path on iPhone. Its authenticated app action establishes user authorship, not that every statement concerns the user. Ordinary recordings remain identity-unknown. Ask questions, pasted quotations and assistant answers do not automatically become personal declarations. Future voice recognition adds evidence through the same identity boundary.

No memory suggestions, per-fact approvals or memory-management screen. Personal sources must be saveable, reopenable and deletable. Keep local saving independent of cloud learning and show truthful pending/failed state without automatic paid retries.

## PR 1 — personal sources and profile foundation

**Deliver:** personal-text sources through the actual app/service path and a broader derived profile contract. Model-backed personal learning remains disabled until PR 2 passes.

- Version source provenance and API compatibility. Derive ownership server-side; arbitrary owner IDs and model-generated names cannot grant identity. Legacy sources remain identity-unknown.
- Add minimal text-entry/save/open/delete UI; reuse the durable synchronization boundary and preserve offline input across relaunch.
- Represent user facts and user-linked relationships without conflating subjects. “My daughter Maya likes swimming” relates Maya to the user but assigns the preference to Maya. Matching names alone must not merge people. Keep ambiguous relationships separate.
- Extend profile selection beyond preferences, reusing claim kinds where sufficient. Add only necessary identity/relationship metadata. Retain source, modality, dates and lifecycle for every selected fact.
- Reuse correction, expiry, consolidation and deletion. Stable preferences do not expire through inactivity; temporary feelings do not become permanent traits. Source deletion invalidates unsupported derivatives and affected answer snapshots using the existing contract.

**QA gate:** execute local app/service save → sync → reopen and inspect persisted provenance. Exercise offline replay, duplicate delivery, two-owner isolation, legacy migration, revisions/deletion and stale-job rejection. Inject fixture judgments to prove profile derivation, relationships and lifecycle, explicitly labeling this as fixture evidence rather than model learning. Build affected native targets and inspect the actual changed UI. No provider calls needed.

## PR 2 — automatic personal learning with Luna and Jev

**Deliver:** actual personal sources automatically populate and update a broad, source-backed profile.

- Version Luna extraction to accept trusted identity metadata separately from untrusted text. Extract life context and relationships as well as work context; preserve who said something and who it concerns.
- Update independent Jev support and attribution/lifecycle judgments to understand the same provenance. Do not simply remove first-person safeguards: ordinary recorded “I” remains unknown. Code enforces subject eligibility, ownership and transitions.
- Preserve emotions, tentative plans, historical states and reported advice with their qualifications. Appointment instructions do not establish diagnoses; lecture examples do not establish personal beliefs.
- Commit claims with source/version checks. Preserve budget admission, cached stage results and observable failure reasons. No silent verifier substitution, weakened thresholds or automatic paid retries.

**QA gate:** freeze a small synthetic development/held-out corpus before prompt iteration. Cover student, parent, athlete and work examples; relationships and same-name ambiguity; quotes, hypotheticals, temporary feelings, anonymous recordings, corrections and third-party facts. Replay locally first. Within a newly approved allowance, run real Luna → Jev → writer and inspect stored claims. Designated positives must retain intended facts; critical negatives must produce no false user attribution, invented relationships, unsupported claims or stale resurrection. Preserve failures and fix the affected stage before merging. Check restart, duplication, expiry and deletion locally without repeating inference.

## PR 3 — profile-aware answers and physical iPhone acceptance

**Deliver:** relevant personal understanding informs Ask alongside current and past conversations, with working source references.

- Add user/relationship-aware candidates before Jev relevance selection. Test older facts and paraphrased questions; recent passages and keyword overlap alone are insufficient proof of profile recall.
- Use bounded profile candidates and the existing relevance batch/context manifest. Deduplicate shared sources. Set explicit item/byte/time limits before implementation; preserve current-session context and the Ask deadline. Do not inject the entire profile into every answer or add an extra model call when existing batching suffices.
- Keep current/historical states distinct. Revalidate ownership, sources and deletion generations before generation. Personalize only when useful, cite evidence and preserve reported/uncertain information.
- Keep ordinary answers useful without personal context. Memory failure must remain explicit and must not interrupt recording or silently appear as an empty profile.
- Resolve personal-note sources in the app and saved answers; preserve old-answer compatibility and shared Mac builds without claiming untested device parity.

**QA gate:** cached-response replay proves candidate recall, relevance, budgets, source display, irrelevant-context exclusion, lifecycle filtering, outage fallback and deletion races. A bounded live check proves real retrieval judgments feed the actual answer. After founder readiness, on physical iPhone: save a personal note, ask from another session, open its source, save a correction, ask again, relaunch and reopen. Verify source deletion through actual app/service state; repeat live Ask only if needed to resolve uncertainty. Audio capture is unchanged: reuse transcript fixtures and existing capture evidence rather than retranscribing to debug profile behavior.

## Delivery and spending

Each checkpoint: verified main → implement → run and inspect actual claimed behavior → focused PR → review → merge after gates pass. Record tested commit, input provenance, expected/observed results, commands, costs and limitations. Diagnose at the failing layer; broaden checks only for changed contracts or unresolved risk. No unrelated cleanup.

The existing $0.28 memory QA allocation is exhausted. Founder approval, September 25, 2026: an additional maximum **$1 total** for this personal-profile slice's provider QA, covering Luna extraction/answers and Jev verification/retrieval across PRs 2–3. This is a ceiling, not a spending target or a separate allowance per checkpoint. Approval ID: `personal-profile-qa-2026-09-25-100`. The allocation is now provisioned in the canonical hosted ledger. Checkpoints 2–3 have used 38 calls ($0.38 conservatively reserved); $0.62 remains for this slice. See the learning evidence for accounting details.

Planning and local fixture work need no provider spend. Before live QA, define the concrete cases and maximum call counts and provision this allowance idempotently in the existing accounting path. Track all covered calls against the aggregate $1 cap, preserve earlier spending, and stop before exceeding the allowance; any increase requires new approval. Reuse saved responses and make no automatic paid retries or quota resets. Review concrete deployment/migration and rollback before hosted enablement; preserve the spend ledger and existing working path, with a profile feature gate.

Wait for explicit readiness before founder-dependent device checks. Stop at required access, spend or rollout blockers. Final acceptance distinguishes simulated, live-provider and physical-device evidence. Voice recognition is a separate later slice.
