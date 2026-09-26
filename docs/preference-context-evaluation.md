# Preference verification: unsuccessful context candidate

September 26, 2026. Follow-up to [subject quality](companion-subject-quality.md). This is an evaluation checkpoint, not a repaired memory-retention checkpoint. Production code, thresholds and deployment remain unchanged.

## Diagnosis and hypothesis

The original Project Juniper preference received support 0.66, modality 0.77 and time 0.56, below unchanged 0.90 gates. It already included both cited fragments; lack of concatenation alone was not the explanation. Tested a context-only candidate and then a candidate with explicit ordered original context and clearer support/modality/time questions. Claims remained proposals, never supporting evidence. No model-generated normalization was substituted for original text.

The [current TypeSafe documentation](https://docs.typesafe.ai/introduction) recommends atomic, independently evaluated questions. This informs the next hypothesis; it does not guarantee performance or validate these candidate prompts.

## Results

Nine bounded live Jev calls: one context-only case and eight candidate cases. The context-only case failed both project facts. The revised candidate retained pet preferences and a family member's corrected work schedule; it rejected competing names, an unrelated quotation, a superseded historical preference, and a hypothetical. It still rejected the project preference, its previously passing location fact, and the person interest. Thus it fails acceptance and must not replace production verification.

Two additional complete-sentence controls tested the same candidate questions. “Project Juniper prefers morning meetings.” passed all three gates at 1.0. “Maya enjoys swimming.” still failed support (0.86) and time (0.78), while modality passed at 1.0. This limits the fragmentation hypothesis: formatting can matter, but adding context or completing sentences is not a sufficient demonstrated repair. Small synthetic samples do not establish a general error rate or prove a causal mechanism.

Requests, responses, expected outcomes and decisions are preserved in `Backend/fixtures/preference-context/`. The evaluator constructs deterministic cases, reserves before each call, uses the canonical budget, and never retries. `--controls` selects two separate synthetic complete-sentence controls. They are not rewritten user recordings. No user data, audio, Luna generation or production-memory writes were involved.

Verification: `PYTHONPATH=Backend python3 -m unittest test_preference_context test_subject_continuity` passed four tests, including exact request/response replay for the failed candidate and the still-working production location lifecycle. Passing replay tests proves reproducibility of the failure, not successful memory retention. No threshold was lowered.

## Budget and next gate

This evaluation used 11 calls at $0.01 conservative reservation each. Canonical profile QA is now $2.90/$2.90: Luna 121 calls/$1.21, Jev 169 calls/$1.69. Reservations are not invoices; no automatic retries or additional allowance were used.

Next proposed bounded experiment: replace compound “is this annotation supported?” questions with direct, atomic classifications of expressed content, modality and temporal status, composing acceptance in code. Compare against these preserved cases and add held-out positives and negatives before considering rollout. Keep Jev independent from Luna and preserve ownership and lifecycle gates. If the quality criterion still fails, reassess the verifier role rather than weakening thresholds or endlessly tuning to Juniper. Additional provider-backed evaluation requires founder approval; proposal is up to $0.30/30 conservative call reservations within the global $5 cap. No rollout until representative and writer-path checks pass.

Founder approved the additional $0.30. The operator-only preference allowance raises the QA subledger to $3.20, reserves $0.10 in Ask and $0.20 in Jev, and redistributes unused category headroom while retaining the global $5 cap. Existing reservations are never reset. Hosted callers do not opt into this evaluation-only allowance. Nine focused budget/runtime checks exercised provisioning, idempotency, cap exhaustion, preserved history and service restart against real temporary SQLite ledgers.
