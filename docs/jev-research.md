# Jev research

Reviewed September 24, 2026. Based on official documentation; no API benchmarking performed. These findings and implementation ideas are supporting research, not product requirements.

## Documented capabilities

Jev evaluates text using Choice (categories), Score (rubric levels), and Noul (yes/no probability). Choice and Score include probability distributions and confidence. Multiple independent questions can share one state in a request.

Jev does not transcribe audio or generate prose. Separate components are needed for transcription, notes, conversational answers, speech output, and persistent storage.

Sources: https://docs.typesafe.ai/introduction and https://docs.typesafe.ai/concepts/system-one

## Pricing and limits at review time

- Current documented model: `jev-1.13.0`.
- $0.042 per million input tokens; output tokens free.
- 64k tokens per request, with a separate 32k limit for state plus the longest question.
- Text input only.

Illustrative Jev-only costs: evaluating 2,000 total input tokens every 10 seconds costs $0.03024 per hour; 4,000 every 5 seconds costs $0.12096 per hour. These exclude transcription, generation, storage, and voice output. Actual token usage and request frequency must be measured.

Source: https://docs.typesafe.ai/models

## Potential role in this product

- Classify completed transcript passages.
- Detect possible note updates and topic changes.
- Filter/rank generated candidate questions and check whether already answered.
- Evaluate relevance of retrieved passages for answering a user question.
- Evaluate candidate memories for subject attribution, duplication, and conflict.

These are hypotheses to test. A generative model or parser must create arbitrary text candidates; Jev can evaluate them. Application code controls writes and presentation.

## Constraints that affect the design

Keep evaluations focused on relevant transcript spans and context. TypeSafe documents difficulties with irrelevant long context, numerical precision, multi-step indirection, and adversarial content. Confidence measures answer-distribution concentration; it does not guarantee correctness. Tune thresholds against representative conversations.

Sources: https://docs.typesafe.ai/model-jaggedness/jev-1.13 and https://docs.typesafe.ai/confidence

Batching questions reuses state and can reduce cost and latency. Actual latency remains unmeasured for our workload.

Source: https://docs.typesafe.ai/patterns/fan-out

## Memory implementation hypothesis

Keep original transcripts, editable session notes, and selected longer-term context distinct. Preserve source timestamps, subject, and stated-versus-inferred status. Do not turn a lecturer's example or a friend's statement into a fact about the user. Allow corrections.

TypeSafe says customer requests/responses are not used for model training; zero data retention is offered to enterprise customers. Do not assume all plans have zero retention.

Sources: https://docs.typesafe.ai/models and https://docs.typesafe.ai/legal
