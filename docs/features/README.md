# Feature and context map

Checked against main `3fb8d4b` on September 26, 2026 (through PR 84). This is a navigation aid for humans and coding agents, not a new product specification or a claim of public-release readiness.

> Granola with an AI that listens alongside you and can join the conversation.

The product is an iPhone-first personal companion with Mac support. Its two entry points are **Capture meeting note** and **Talk to companion**. Meeting recordings and voice notes are the same source type. Granola remains the Proven.

## Read in this order

1. [Product source of truth](../product-source-of-truth.md), [engineering principles](../engineering-principles.md), and [historical V0 boundary](../v0-scope.md).
2. The relevant feature below in [feature details](features.md), then its named implementation files and evidence.
3. [Learned lessons and debugging routes](lessons.md) before changing a known failure path.

Canonical product/engineering documents retain authority. Maps describe verified code and bounded evidence; plans describe intent. Older checkpoint documents may say “not deployed” or describe deletion cascades that later checkpoints superseded. Read their dates and follow the current rollout links below. For live quota, credential, flag or deployment state, inspect the actual system rather than treating a dated document as current runtime truth.

## Feature index

| Feature | Current boundary | Detail |
| --- | --- | --- |
| Microphone capture and live transcript | Internal Mac/iPhone flow; speaker labels best-effort | [Capture](features.md#capture-and-live-transcript) |
| Recording library and evidence sync | Local saved transcripts; backend evidence outbox, not full cross-device library sync | [Library](features.md#recording-library-and-evidence-sync) |
| Persistent companion chat | One main chat; typed questions during/after capture and across recordings | [Companion](features.md#companion-chat-and-source-navigation) |
| Automatic learning | Background evidence extraction, independent verification, atomic writes | [Learning](features.md#automatic-memory-learning) |
| Personal context and identity | Whole-life facts/relationships with provenance; no voice enrollment | [Identity](features.md#personal-context-and-identity) |
| Corrections, time and maintenance | Qualified lifecycle, bounded expiry and consolidation; no memory-management UI | [Lifecycle](features.md#corrections-time-and-maintenance) |
| Retrieval and answer context | Live/attached/history/past evidence; hybrid original-source retrieval, lexical retained-memory retrieval | [Recall](features.md#retrieval-and-answer-context) |
| Recording deletion and retained memory | Transcript removed; eligible learned knowledge retained with unavailable-source label | [Deletion](features.md#recording-deletion-and-retained-memory) |
| Internal access, budgets and deployment | Explicit enrollment, admission caps, persistent single-instance service | [Operations](features.md#internal-access-budgets-and-rollout) |

## System flows

```text
Capture meeting note
  microphone -> transcription relay/provider -> transcript events
       -> local session/library -> durable evidence outbox -> backend source
            +-> background learning -> verified claims + evidence + lifecycle
            +-> background indexing -> lexical/vector source retrieval

Talk to companion (the same main chat during and between recordings)
  question + optional recording/live snapshot + recent chat
       + relevant past evidence -> bounded context -> Luna answer
            -> saved turn + references -> source passage OR retained-memory label

Delete recording
  local library removal + durable deletion sync
       -> remove backend transcript/index/snapshots; tombstone source
       -> preserve eligible learned claims + bounded supporting excerpts
       -> invalidate answers depending on original source
       -> new retained-memory answers cannot open the deleted recording
```

These are data dependencies, not a guarantee that background learning has finished when transcription stops. An answer can use original transcript evidence before any derived memory is committed.

## What is not delivered by these maps

Voice recognition/enrollment; silent continuous recording; proactive spoken participation; Mac computer-audio capture; generated meeting summaries and note editing; side chats; full recording-library synchronization between devices; public account/subscription/distribution operations; explicit memory-erasure UX. These need their own approved slices. Recording remains user-started and internally capped. Do not infer launch readiness from the bounded harness acceptance.

## Keep context useful

Update the affected feature entry when a checkpoint changes behavior, module ownership, a cross-feature contract, verification evidence or a material limitation. Add a lesson only when a failure or decision changes how future work should be done: trigger → cause → guard → evidence. Link evidence instead of copying logs, mutable budget balances, transcripts or secrets. Retain failed evidence, mark superseded guidance, and avoid duplicating canonical policy. No runtime/provider testing is warranted for map-only edits; verify paths, links and factual alignment with code.
