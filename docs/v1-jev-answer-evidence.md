# Jev answer-policy comparison — failed grounding gate

Backend/evaluation scripts `d5f254e`, September 25, 2026. Eight frozen synthetic cases; 8 Jev and 16 Luna calls, no retries. Same Luna model and base prompt for both variants; order alternated. This is functional policy evaluation, not model selection.

Human-readable semantic review by the implementation agent, not an independent/blinded or statistical study. Two useful improvements were observed, but one grounding regression fails the required gate. Routing must remain disabled pending founder scope resolution.

Median paired added first-text latency: 0.168s, within the 0.500s target. Network/model variation means this is a smoke measurement, not a causal benchmark or general latency promise.

## summary

Equivalent; both preserve the undecided annual purchase.

### direct

First text 2.702s; route direct; routing 0.000s.

They decided to run a two-week pilot. Whether to buy the annual plan remains undecided. [[p1]] [[p2]]

### routed

First text 1.114s; route summary; routing 0.279s.

They decided to run a two-week pilot. Whether to buy the annual plan remains undecided. [[p1]] [[p2]]

## perspective

Useful improvement: routed response distinguishes unknown severity/impact and proposes a conditional launch decision. Both remain grounded.

### direct

First text 0.638s; route direct; routing 0.000s.

A sensible next step is to reproduce and investigate the crash when the phone locks before launching. Since it’s a known failure and the launch is tomorrow, decide based on a quick test whether to fix it, limit the affected behavior, or delay the launch. [[p1]] [[p2]]

### routed

First text 1.049s; route perspective; routing 0.128s.

A sensible next step is to reproduce the crash when the phone locks and assess how often it happens and what users lose. Since launch is tomorrow, I’d make the launch decision depend on that quick check: if the crash is reliable or risks losing work, delay or disable the affected behavior; if it’s contained, document the limitation and ship with a workaround. The conversation establishes the crash and the timeline, but not its severity or impact. [[p1]] [[p2]]

## commitment

Equivalent; neither invents a funding commitment.

### direct

First text 1.051s; route direct; routing 0.000s.

No. They agreed to explore the idea and discuss funding next month, but didn’t agree to fund it. [[p1]]

### routed

First text 0.724s; route recall; routing 0.148s.

No. They agreed to explore the idea and discuss funding next month, but did not agree to fund it. [[p1]]

## mixed

No improvement; routed uses the direct fallback. Both distinguish inferred risk from the decision.

### direct

First text 0.581s; route direct; routing 0.000s.

You decided to test the prototype with five volunteers before launch. [[p1]] One risk to consider is that five volunteers may not reveal problems that affect a broader range of users, so treat the test as an early check rather than proof that the prototype is ready.

### routed

First text 0.675s; route direct; routing 0.101s.

You decided to test the prototype with five volunteers before launch. [[p1]] One risk to consider is that five volunteers may not reveal problems that affect a broader or less similar group of users.

## summary-disagreement

Equivalent; both retain disagreement and the unresolved date.

### direct

First text 0.797s; route direct; routing 0.000s.

Mina favors a Friday release to reach more customers, while Owen objects because the payment flow is still failing. They have not agreed on a release date. [[p1]] [[p2]] [[p3]]

### routed

First text 0.671s; route summary; routing 0.105s.

Mina favored a Friday release to reach more customers, while Owen objected because the payment flow was still failing. They did not agree on a release date. [[p1]] [[p2]] [[p3]]

## summary-actions

Equivalent; both separate decision, unresolved pricing and the explicit task.

### direct

First text 0.823s; route direct; routing 0.000s.

- **Decision:** Invite five volunteers to a pilot. [[p1]]
- **Open question:** Whether to charge $10 later; pricing is undecided. [[p3]]
- **Agreed task:** Ana will send the invitations on Tuesday. [[p2]]

### routed

First text 1.065s; route summary; routing 0.137s.

- **Decision:** Invite five volunteers to join a pilot. [[p1]]
- **Open question:** Whether to charge $10 later; pricing remains undecided. [[p3]]
- **Agreed task:** Ana will send the invitations on Tuesday. [[p2]]

## perspective-reversibility

Useful improvement: routed adds actionable recovery-testing/preservation steps rather than only stating the preference. Suggestions are distinguished from transcript facts.

### direct

First text 0.650s; route direct; routing 0.000s.

I’d prioritize reversibility. The migration would immediately delete the old records, and the backup restore hasn’t been tested; launching the dashboard by tomorrow is a real deadline, but not enough to make an untested rollback safe. [[p1]] [[p2]] [[p3]]

### routed

First text 0.897s; route perspective; routing 0.188s.

I’d prioritize reversibility. The migration would immediately delete the old records, and the backup restore hasn’t been tested [[p1]] [[p2]]. That makes moving fast by tomorrow [[p3]] a risky bet. I’d test recovery—or find a way to preserve the old records—before committing to the migration.

## perspective-risk

FAIL — grounding regression. Routed says varied operating systems are untested, but the source only establishes the same newest iPhone model and no slow-network test. OS-version coverage is unknown. Direct uses conditional language about possible gaps.

### direct

First text 0.524s; route direct; routing 0.000s.

The main blind spot is how narrow the testing was: all five testers used the same newest iPhone, and nobody tried a slow connection. [[p1]] [[p2]] So “ready for everyone” may be premature; older devices, different platforms, and weaker networks could expose problems the test group wouldn’t catch. [[p3]] A broader test across devices and connection speeds would give you a more reliable read.

### routed

First text 0.800s; route perspective; routing 0.145s.

The biggest blind spot is how narrow the testing was: all five testers used the same newest iPhone, and none tried the app on a slow connection. [[p1]] [[p2]] That leaves older or different devices, varied operating systems, and real-world network conditions untested. So “ready for everyone” seems stronger than the evidence supports. [[p3]] A broader test across device types, accessibility needs, and connection speeds would help reveal what’s still missing.

Luna usage: 11,951 input / 916 output tokens, estimated $0.0016531. Comparison Jev usage: 4,613 input tokens, estimated $0.000193746. All checkpoint Jev calls: 46 requests / 25,967 input tokens, estimated $0.001090614. Total checkpoint estimate $0.002743714, not verified billing. Conservative permanent reservations: $0.023 Jev + $0.048 comparison Luna.
