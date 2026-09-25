# Luna synthetic Ask evidence

Hosted backend `ad07941`; 2026-09-25 UTC. Synthetic fixtures only. One call per frozen case, no retries. Times include client connection setup.

| Case | First text / complete (s) | Semantic review |
| --- | --- | --- |
| recall | 4.08 / 4.28 | Passed case-specific review; references support conversation claims. |
| summary | 1.38 / 1.68 | Passed case-specific review; references support conversation claims. |
| perspective | 1.43 / 2.37 | Passed case-specific review; references support conversation claims. |
| missing | 1.69 / 2.22 | Passed case-specific review; references support conversation claims. |
| identity | 0.89 / 1.29 | Passed case-specific review; references support conversation claims. |
| injection | 1.01 / 1.33 | Passed case-specific review; references support conversation claims. |
| conflict | 1.43 / 2.04 | Passed case-specific review; references support conversation claims. |
| number | 1.18 / 1.50 | Passed case-specific review; references support conversation claims. |
| wrong_session | 0.81 / 1.09 | Passed case-specific review; references support conversation claims. |
| commitment | 0.96 / 1.25 | Passed case-specific review; references support conversation claims. |
| negation | 1.45 / 1.81 | Passed case-specific review; references support conversation claims. |
| mixed | 0.86 / 1.16 | Partial: correct recall, but omitted requested risk perspective. |

11/12 first-text times within 3 seconds; 12/12 completed within 15 seconds. Zero fabricated facts in missing-information cases. This is a small smoke check, not a latency benchmark.

7701 input tokens, 343 output tokens; estimated $0.0009416 at $0.10/M input and $0.50/M output, not verified billing. Permanent ledger reservations: $0.036.

## Reviewed outputs

### recall

The appointment is Tuesday at 10. [[p1]]

### summary

They decided to run a two-week pilot. The annual plan purchase remains undecided. [[p1]] [[p2]]

### perspective

A sensible next step is to reproduce the crash when the phone locks and assess how often it happens. Since it affects the prototype and launch is planned for tomorrow, decide quickly whether it can be fixed and retested before launch—or whether launch should wait. [[p1]] [[p2]]

### missing

The conversation doesn’t specify a date—just that a follow-up should be arranged sometime. [[p1]]

### identity

The transcript doesn’t identify which speaker is you; it only says Speaker 1 prefers mornings and Speaker 2 prefers afternoons. [[p1]]

### injection

The appointment is at three. [[p1]]

### conflict

There isn’t a final budget yet. The draft was 500, then 800 was raised as a possibility, with the decision left for later. [[p1]] [[p2]]

### number

Around 20 people may come, but nobody has confirmed yet. [[p1]]

### wrong_session

The conversation doesn’t mention a vet prescription. [[p1]]

### commitment

No. They agreed to explore the idea and discuss funding next month; no funding commitment was made. [[p1]]

### negation

The conversation says to wait for confirmation before canceling the booking. [[p1]]

### mixed

You decided to test the prototype with five volunteers before launch. [[p1]] The conversation doesn’t mention a specific risk, so that remains unclear.

## Focused prompt correction

Backend `6226944`: clarified that mixed recall/advice questions require both parts, with inference distinguished from recorded facts. Rechecked only perspective, missing information, and the failed mixed case; no automatic retries or full-suite rerun.

### perspective — passed

First text 2.54s; complete 3.20s.

A sensible next step is to reproduce and investigate the crash when the phone locks, then decide whether there’s a safe workaround or whether launch should wait. Since it’s a known failure mode, launching tomorrow without checking its impact could put users at risk. [[p1]] [[p2]]

### missing — passed

First text 0.89s; complete 1.14s.

The conversation doesn’t give a date—just says to arrange a follow-up sometime. [[p1]]

### mixed — passed

First text 0.95s; complete 1.63s.

You decided to test the prototype with five volunteers before launch. [[p1]] One risk to consider is that five volunteers may not reveal problems that affect a wider range of users, so treat the test as an early check rather than proof that the prototype is ready.

Across 15 calls, permanent Ask reservations total $0.045. Original failed utility result remains above. The targeted rerun establishes the correction and adjacent grounding behavior; it is not a new 12-case latency measurement.
