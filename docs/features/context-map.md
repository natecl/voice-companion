# Per-feature context maps

Each feature has its own working brief. Read it before the verifier or implementation. The map separates existing behavior, gaps, contracts, dependencies, evidence and the next bounded job. These are repository context snapshots, not fresh deployment attestations.

The [social-presence experience](../social-presence-experience.md) is the latest founder direction.

| Feature | Context map | Verifier |
| --- | --- | --- |
| Capture and live transcript | [capture](maps/capture.md) | [Contract](verification/capture.json) |
| Recording library and sync | [library](maps/library.md) | [Contract](verification/library.json) |
| Meeting note summaries | [meeting-notes](maps/meeting-notes.md) | [Contract](verification/meeting-notes.json) |
| On-device note caching | [note-cache](maps/note-cache.md) | [Contract](verification/note-cache.json) |
| Companion chat and follow-ups | [chat](maps/chat.md) | [Contract](verification/chat.json) |
| Composer dictation | [dictation](maps/dictation.md) | [Contract](verification/dictation.json) |
| Notes search | [notes-search](maps/notes-search.md) | [Contract](verification/notes-search.json) |
| Automatic memory learning | [memory-learning](maps/memory-learning.md) | [Contract](verification/memory-learning.json) |
| Past-context retrieval | [recall](maps/recall.md) | [Contract](verification/recall.json) |
| Personal context and identity | [identity](maps/identity.md) | [Contract](verification/identity.json) |
| Memory corrections and time | [memory-lifecycle](maps/memory-lifecycle.md) | [Contract](verification/memory-lifecycle.json) |
| Note deletion and retained answers | [deletion](maps/deletion.md) | [Contract](verification/deletion.json) |
| Proactive contributions | [proactive](maps/proactive.md) | [Contract](verification/proactive.json) |
| Tester access and account controls | [access](maps/access.md) | [Contract](verification/access.json) |
| TestFlight install and update | [distribution](maps/distribution.md) | [Contract](verification/distribution.json) |
| Sign-up and pricing previews | [subscriptions](maps/subscriptions.md) | [Contract](verification/subscriptions.json) |
| Calendar, email and messages | [connected-sources](maps/connected-sources.md) | [Contract](verification/connected-sources.json) |
| Invited social presence and interface | [social-presence](maps/social-presence.md) | [Contract](verification/social-presence.json) |

The orchestrator maintains these maps at accepted checkpoints. Workers submit map deltas with evidence; they do not independently rewrite shared product direction. See [worker packet](../execution/worker-packet-template.md) and [verification map](verification-map.md). Older aggregate [feature details](features.md) and [knowledge history](knowledge.md) provide supporting background; consult dates and exact code before treating historical rollout text as current.
