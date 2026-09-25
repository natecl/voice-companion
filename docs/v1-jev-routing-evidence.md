# Jev routing evidence

Synthetic question-only QA from the hosted Render instance, September 25, 2026. No retries.

## development

Model/rubric: `jev-1.13.0` / `question-intent-v1`.

| Case | Expected | Observed | Reason | Seconds |
| --- | --- | --- | --- | --- |
| dev-01 | recall | recall | classified | 0.383 |
| dev-02 | recall | recall | classified | 0.103 |
| dev-03 | recall | recall | classified | 0.112 |
| dev-04 | summary | summary | classified | 0.163 |
| dev-05 | summary | summary | classified | 0.125 |
| dev-06 | summary | summary | classified | 0.131 |
| dev-07 | perspective | direct | uncertain | 0.184 |
| dev-08 | perspective | direct | uncertain | 0.132 |
| dev-09 | perspective | perspective | classified | 0.104 |
| dev-10 | direct | direct | mixed_uncertain | 0.149 |
| dev-11 | direct | direct | mixed_uncertain | 0.093 |
| dev-12 | direct | direct | mixed_uncertain | 0.100 |

## development-focus

Model/rubric: `jev-1.13.0` / `question-intent-v2`.

| Case | Expected | Observed | Reason | Seconds |
| --- | --- | --- | --- | --- |
| dev-07 | perspective | perspective | classified | 0.453 |
| dev-08 | perspective | perspective | classified | 0.167 |

## heldout

Model/rubric: `jev-1.13.0` / `question-intent-v2`.

| Case | Expected | Observed | Reason | Seconds |
| --- | --- | --- | --- | --- |
| held-01 | recall | recall | classified | 0.337 |
| held-02 | recall | recall | classified | 0.151 |
| held-03 | recall | recall | classified | 0.151 |
| held-04 | recall | recall | classified | 0.112 |
| held-05 | recall | recall | classified | 0.141 |
| held-06 | recall | recall | classified | 0.104 |
| held-07 | summary | summary | classified | 0.152 |
| held-08 | summary | summary | classified | 0.145 |
| held-09 | summary | summary | classified | 0.278 |
| held-10 | summary | summary | classified | 0.147 |
| held-11 | summary | summary | classified | 0.131 |
| held-12 | summary | summary | classified | 0.136 |
| held-13 | perspective | perspective | classified | 0.119 |
| held-14 | perspective | perspective | classified | 0.110 |
| held-15 | perspective | perspective | classified | 0.204 |
| held-16 | perspective | perspective | classified | 0.116 |
| held-17 | perspective | perspective | classified | 0.146 |
| held-18 | perspective | perspective | classified | 0.123 |
| held-19 | direct | direct | mixed_uncertain | 0.114 |
| held-20 | direct | direct | mixed_uncertain | 0.129 |
| held-21 | direct | direct | uncertain | 0.145 |
| held-22 | direct | direct | mixed_uncertain | 0.149 |
| held-23 | direct | direct | mixed_uncertain | 0.102 |
| held-24 | direct | direct | mixed_uncertain | 0.175 |

Held-out: 24/24 acceptable routes, no harmful route mistakes. One mixed question used the uncertainty fallback, which is the expected direct path. Median 0.143s, max 0.337s; no timeout. Development failures are preserved above. Thresholds were not lowered. This small synthetic set is not a general accuracy guarantee.
