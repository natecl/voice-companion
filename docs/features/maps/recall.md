# Past-context retrieval

Feature ID: `recall` · Context reviewed September 29, 2026 against main `3a30e25`.

## Purpose and user outcome

Select relevant original evidence and preserve corrections. Product direction: **AI notes that proactively contribute to discussions**. Canonical [product](../../product-source-of-truth.md) and [engineering](../../engineering-principles.md) guidance govern this map.

## Current implementation

Unified recall uses notes for discovery and hydrates original evidence. One Jev rank plus an independent two-excerpt reserve is documented; attached/live/history context remains separate from past retrieval.

## Gaps and non-goals

Retrieval can miss useful evidence. Retained claims use lexical retrieval, not their own semantic embeddings. A pre-retrieval classifier experiment remains disabled; ranking is not a factual verifier.

## Flow and implementation entry points

Current question/topic → notes/transcript/retained candidates → original evidence deduplication → bounded ranking/reserve → qualified context packet → answer.

- [Backend/notes_recall.py](../../../Backend/notes_recall.py)
- [Backend/companion_context.py](../../../Backend/companion_context.py)

## Contracts and dependencies

Apply owner/revision/deletion guards before model usefulness. Preserve source qualifiers and corrections through the final context. Missing indexing is not proof that no memories exist.

**Uses:** [Recording library and sync](library.md), [Meeting note summaries](meeting-notes.md), [Automatic memory learning](memory-learning.md), [Personal context and identity](identity.md), [Memory corrections and time](memory-lifecycle.md), [Note deletion and retained answers](deletion.md)

**Consumers / coordinated work:** [Companion chat and follow-ups](chat.md), [Proactive contributions](proactive.md)

These links describe integration boundaries, not a mandatory execution order. The worker packet assigns exact file ownership; listing a shared file here does not authorize concurrent edits.

## Verification and delivery state

- Repository state: implemented foundations; fresh feature verification required.
- [Feature verifier contract](../verification/recall.json): `python3 scripts/verify_feature.py recall`.
- [Mechanical baseline and unresolved checks](../verification-map.md#initial-mechanical-check-results--september-29-2026). Automated success is not full-feature acceptance.
- Required real-path evidence: Actual ranked context → answer pipeline, irrelevant and conflicting evidence cases.
- Merged/deployed/installed are separate states. This map is a repository context audit; it does not freshly inspect hosted flags or the phone. Historical evidence below applies only to its recorded versions and scenarios. Obtain actual version/configuration identities before a runtime claim.

## Next bounded work

Inspect candidates → ranked selection → hydrated packet → response to locate misses; do not rerun audio capture to debug retrieval.

Before editing, read this map and linked code, identify affected contracts, and define observable success/failure cases in the packet. Submit changed behavior, exact commit/configuration, reproducible evidence, remaining gaps and proposed map updates to the orchestrator. Dependent work waits for explicit review acceptance.

## Supporting context and evidence

- [simple-memory-foundation.md](../../simple-memory-foundation.md)
- [memory-related-evidence.md](../../memory-related-evidence.md)
- [companion-capacity.md](../../companion-capacity.md)

## Maintenance

Update this map when behavior, dependencies, verification, deployment evidence or the next blocker changes. Update the linked catalog/verifier with it. Preserve failed evidence and label superseded experiments; do not append contradictory status updates or replace missing verification with a claim of completion.
