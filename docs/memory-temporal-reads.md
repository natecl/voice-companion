# Read-time memory validity — checkpoint 4A

This bounded backend change qualifies existing validity intervals consistently in current search, historical search, source evidence and recall snapshots. It does not normalize natural-language dates or infer event completion. `future` means the stored validity start has not arrived, not that an event will certainly happen.

For an otherwise active claim, `valid_from <= now < valid_until` is applicable. Before its start, read state is `future`; at or after its end, read state is `expired`. Missing bounds impose no limit. A read projection retains `stored_state` when it changes the returned state and does not mutate SQLite or raw sources. Existing superseded, invalid, unresolved and expired states are not promoted by a clock change. One clock sample applies throughout each read. Internal maintenance can persist expiry; no model call or user-facing forgetting action is needed.

Temporal qualification precedes pending-correction qualification: an expired or not-yet-applicable target cannot become apparently current merely because a correction is unresolved. The legacy recall guard excludes nonactive claims from current-use context. A validity boundary changes its snapshot digest, so an in-flight answer using stale context cannot complete validation. This does not implement the planned ranking/context assembly replacement.

## Behavioral evidence

September 26, 2026, local macOS / Python 3.13. Synthetic claims were committed through MemoryStore to a temporary real SQLite database. No hosted data, model settings or device capture changed. No paid provider calls.

Controlled-clock inspection of an interval [200, 300):

| Clock | Current results | History / source evidence / recall states | Original source unchanged |
| --- | --- | --- | --- |
| 150 | 0 | future / future / future | yes |
| 200 | 1 | active / active / active | yes |
| 300 | 0 | expired / expired / expired | yes |

After maintenance the inspected SQLite claim state was `expired`. Reopening the store preserved historical availability. Tests also exercise the actual MemoryRecall preparation/validation path with a deterministic relevance-provider double: even a `relevant` answer cannot admit a future-validity claim as current; expiry invalidates an already prepared manifest. This proves local storage/recall enforcement, not live provider answer quality.

Reproduction: from Backend, run `python3 -m unittest test_memory_temporal_reads`. Five cases cover exact boundaries, restart, maintenance, stable-fact retention, owner isolation, source deletion, non-promotion of retired/uncertain claims and in-flight invalidation. Existing duplicate/correction/deletion suites remain passing. Recorded provider replay tests now set their read clock after their 2026 source observations instead of reading those fixtures at epoch +300 seconds; requests and recorded responses are unchanged.

Focused suite: 42 tests passed. Full backend regression suite: `python3 -m unittest discover`, 205 tests passed in approximately 8 seconds. Existing SQLite ResourceWarnings remain a known separate cleanup issue. No native UI, physical-device, model-quality or hosted-rollout claim is made.

## Remaining checkpoint 4 work

Relative expressions and timezone normalization, separate event-time semantics, semantic duplicate consolidation and broader derivative invalidation remain pending. Existing evidence-writer time expressions remain preserved; this change creates no inferred expiry for them. The whole memory rework is not complete or deployed.
