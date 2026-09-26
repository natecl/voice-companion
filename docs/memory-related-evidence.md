# Related correction and conflict evidence

Checkpoint 5E connects stored change relationships to context selection. When Jev selects a source, the harness follows its established supersession chain and unresolved proposed-change links in both directions. It includes live supporting passages even when their wording did not win similarity ranking. Historical and unresolved evidence retain their labels; no model score promotes them to current facts.

The selected-evidence fingerprint now includes these relationships. Adding/removing a pending change invalidates earlier selected context even if the older claim's stored state did not change. Invalid/deleted targets are excluded: deleting a historical source does not make a surviving supported correction unusable. Relationship traversal is bounded to 20 claims and 12 passages, and ranked context remains under 10,000 serialized bytes. Overflow fails explicitly rather than silently omitting a known correction. This component remains opt-in and is not yet installed Ask behavior.

Four focused real-SQLite tests passed: a three-source correction chain reachable from either end; unresolved-change inclusion and deletion; overflow/owner/deleted-source safeguards; actual ranker integration where a synthetic judgment deliberately chooses the old source and deterministic expansion still returns the correction. Six adjacent context tests and four recorded-ranking integration tests also passed. The source/lifecycle logic changed; model request semantics did not, so existing recorded provider evidence was reused without another paid call.

No schema migration, deployment, native change or provider spending. Final answer context assembly, broader multi-source retrieval, background indexing and physical acceptance remain pending.
