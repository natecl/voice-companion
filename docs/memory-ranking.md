# Bounded memory usefulness ranking

Checkpoint 5D adds an opt-in Jev usefulness ranker; installed Ask and hosted deployment are unchanged. It ranks up to twelve already-hydrated source windows, with a competing `none` alternative. It preserves the probability ordering and does not delete evidence or alter claims. The initial context selector takes **one** highest-ranked passage only when it beats `none`. Lower categorical probabilities are not treated as calibrated evidence that several additional passages are useful. Multi-passage comparisons and correction-related expansion remain subsequent integration work.

Source identity and lifecycle are independent of usefulness. Candidate text is quoted evidence, not instructions. Selected source qualifications are carried intact; the selector validates the original selected snapshot again after inference. Deletion, revision, identity/lifecycle changes and expiry can invalidate it. Context is capped at 10,000 serialized UTF-8 bytes, with an explicit `context_limited` outcome if it cannot fit. Inputs over 2,000 characters per window fail explicitly rather than silently truncating. These are component bounds, not the completed answer prompt budget.

## Role selection and frozen gate

The [MiniLM model card](https://huggingface.co/cross-encoder/ms-marco-MiniLM-L6-v2) describes an English passage ranker trained on MS MARCO. The small pinned ONNX variant was tested locally through FastEmbed 0.8.1. It failed the predeclared top-one gate: topical distractors outranked the actual answer in four of six cases. Its roughly 11–14 ms ranking time did not compensate for that failure. `local_reranker.py` and the evaluator preserve an **unadopted research candidate**, never instantiated by the application. `failed-minilm.json` records the failure; rerunning its evaluator should still fail that gate.

Jev was compared on the same six positives and topical distractors, plus three unrelated questions. A single request batched nine independent questions. Each positive had to choose the actual answer-bearing source; all unrelated queries had to choose `none`. All nine passed. This supports this narrow role, not general ranking superiority or model-verified identity. The production single-question object is byte-for-byte structurally equal to its saved batch question in replay tests.

The actual SQLite → hydrated packet → ranker → selected packet → validation path was then exercised with those recorded responses. Positive and no-match behavior, one reservation per call, and deletion during inference were checked. No new paid call was needed for unchanged role inputs. Four targeted tests passed. No STT or device test applies to this backend-only component.

## Cost and remaining work

Canonical remote ledger after this check: Luna 82 calls / $0.82 reserved; Jev 130 calls / $1.30 reserved; total **$2.12 of $2.20**, leaving **$0.08**. The single new Jev call reserved $0.01; reservations are conservative allowances, not verified invoiced cost. No retries.

Final answer integration, related correction/conflict expansion, multi-source questions, attachment/live-transcript context budgeting, indexing coverage, hosted resource acceptance and physical QA remain pending. Preserve those gates rather than claiming the whole memory rework is finished.
