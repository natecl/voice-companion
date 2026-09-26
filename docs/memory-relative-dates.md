# Source-relative calendar references — checkpoint 4B

An accepted memory's preserved temporal expression now has a deterministic, versioned calendar reference in search, source-evidence and recall reads. The reference is derived from its live source revision; no second factual store, schema migration, inference call or new expiry is introduced.

Supported whole expressions: today, yesterday, tomorrow and ISO YYYY-MM-DD. Resolve against the captured source date in its recorded IANA timezone, using calendar arithmetic rather than 24-hour offsets. Keep the exact expression, source timestamp/timezone, reported temporal status, modality, session and revision. A resolved date means a source-relative calendar reference only. It does not establish event time with sub-day precision, completion or validity boundaries. Historical quotations and sources spanning midnight may need a different reference anchor; this version explicitly labels its anchor as source_capture and does not claim discourse-time resolution.

Until Friday, this semester, ranges, negated expressions and expressions containing a time remain unresolved. Invalid timezone, timestamp or calendar date also remains unresolved rather than failing an entire source read. Never silently trim words to force a supported match. Relative dates stay anchored to capture, not the server's current date or the date the user reopens the source. Unsupported phrases retain original evidence for later interpretation.

## QA

September 26, 2026; local macOS / Python 3.13; synthetic source with fixture-accepted model decisions through the real atomic writer and SQLite store. No paid providers, hosted changes or physical device claims. Models and prompts are unchanged; these checks prove deterministic interpretation and storage integration, not provider extraction quality.

`python3 -m unittest test_memory_time` from Backend reproduces four cases covering source timezone boundaries, DST calendar arithmetic, leap/year transitions, bad anchors, ambiguous expressions, and a real atomic-store path. A tentative future swimming plan captured at 2026-09-27 02:00 UTC in America/New_York resolves tomorrow to 2026-09-27. Reopening seven days later preserves tentative/future status, the same reference date, null expiry and the original source. All three read paths agree. Current-memory search does not promote the plan; another owner cannot read it, and source deletion removes the annotations with the evidence.

Direct resolver inspection at that capture instant returned today=2026-09-26, tomorrow=2026-09-27; until Friday and this semester returned unresolved with no date. Focused temporal and writer replay checks: 24 passed. Full backend regression: 209 passed in approximately 8 seconds. Existing SQLite ResourceWarnings remain separate cleanup work.

Remaining checkpoint 4 work: evidence-backed expiry interpretation, richer event/validity distinctions, semantic consolidation and broader derivative invalidation. This bounded checkpoint does not claim that automatic expiry or the whole memory rework is complete. No deployment is included.

## Checkpoint 4C — explicit weekday context

Founder clarification: do not interpret every bare weekday as its next occurrence. Use context and keep uncertainty when multiple dates remain plausible.

`calendar-reference-v2` additionally resolves whole expressions `Tuesday [of] this/next/last week`, `this coming Tuesday`, `upcoming Tuesday` and `this past Tuesday` (all seven full English weekday names). Calendar-week phrases use a Monday-start week convention. Directional phrases on the named day remain unresolved because today versus a week away is unclear. Bare Tuesday, next Tuesday, last Tuesday, recurring weekdays, negation, ranges and time-of-day qualifiers remain unresolved. The existing verified past/future status acts as a contradiction guard for weekday dates, not proof of which week a bare weekday means. Broad conversational interpretation is still pending; this is not a claim that tense alone establishes an exact date.

Source-capture anchoring remains explicit. Quoted/discourse time, user-specific week-start conventions, other languages and recordings spanning midnight need further handling; the normalized date is supporting metadata, not an authoritative replacement for the original words. Date interpretation still never creates expiry, event completion or account-owner attribution.

QA, local macOS/Python 3.13: 11 focused temporal checks and 211 backend tests passed. Tests exercise timezone-local week boundaries, DST/year rollover, conflicting temporal status, same-day ambiguity and ambiguous wording. A synthetic accepted future plan containing Tuesday next week ran through the actual atomic writer, SQLite persistence/reopen, all read surfaces and deletion. No paid provider calls or model changes. For a Saturday September 26 capture in New York, inspected output: Tuesday/next Tuesday unresolved; Tuesday next week/this coming Tuesday = September 29; this past Tuesday = September 22. Sources and tentative status remain unchanged. Reproduce via `python3 -m unittest test_memory_time test_memory_temporal_reads` from Backend. This is deterministic integration QA, not a new live model or deployed-device claim.
