# Local semantic candidates — checkpoint 5B

A replaceable local embedding adapter and versioned SQLite cache now provide semantic source-span candidates. This is a backend foundation, not integration into the installed Ask path or final relevance ranking.

## Model/runtime choice

Use BAAI/bge-small-en-v1.5 for the bounded English internal slice: 384 dimensions, compact quantized CPU execution, a maintained adapter and no embedding-provider API. [FastEmbed](https://qdrant.github.io/fastembed/) documents its ONNX runtime; the [BAAI model card](https://huggingface.co/BAAI/bge-small-en-v1.5) identifies its English/512-token scope. This is a practical tested candidate, not a universal quality claim. Larger multilingual models and paid APIs remain replaceable alternatives.

Optional requirements-semantic.txt pins fastembed 0.8.1. The adapter explicitly downloads repository revision aa8f8b060edb00e03bfdd08813a2949946c8ba55 and uses that path; no remote custom model code is executed. First initialization downloads public weights, not user data. Inference stays on the backend host. Default dependencies/startup are unchanged.

Source windows remain <=400 measured tokens, prefer nearby sentence/newline boundaries and overlap 80 characters. Exact original spans remain attached. No text is deleted from the canonical source. Token counting saturates at 512, which still makes the <=400 test conservative. Oversized queries fail explicitly instead of silently truncating.

## Cache and lifecycle

Schema 11 adds an empty cache; initialization loads no model and schedules no inference. Explicit indexing snapshots a source, computes bounded windows, then rechecks revision/deletion before atomic writes. Keys include model revision, adapter version and window contract. Repeated unchanged indexing reuses the cache. Source revision/deletion invalidates all model versions transactionally. Limits: 512 windows per source, 20,000 per owner/model. Missing vectors remain a coverage gap until background integration indexes them; lexical retrieval remains available.

Query candidates are filtered by owner/live revision/model before scoring normalized vectors. The initial implementation performs an exact vector scan over the owner/model index, not a full transcript-payload scan. It is not ANN infrastructure. Only selected original snippets are loaded. Candidates are relevance hints, not approved current facts; lifecycle/identity admissibility and final context assembly come next. Similarity is not a confidence threshold.

## QA

Local macOS/Python 3.13.7, isolated optional venv. The real model probe retrieved all six designated everyday-life paraphrases in the top five at 10/100/1000 documents. Mean query embedding time: 1.403 ms; process peak RSS: 355598336 bytes (~339 MiB). These are bounded synthetic checks, not broad quality or hosted sizing guarantees.

Actual pinned adapter → SQLite → retrieval passed the same targets at 10/100/1000 sources. Predefined max-query target <100 ms passed: 3.017/4.585/18.959 ms. A five-window long source retained a late fact, cache reuse succeeded, and deletion removed results. Returned spans matched original text; owner scopes stayed separate. Evidence: Backend/fixtures/memory_semantic/.

Five default-runtime tests cover cache versions, reopen, isolation, revision/deletion, stale in-flight indexing, invalid vectors and schema-10 migration without inference. Full backend suite: 230 tests passed. Existing SQLite ResourceWarnings remain. No paid calls; QA balance remains $0.09.

Reproduce real-model proof after installing optional dependencies with `python Backend/evaluate_semantic_store.py --cache work/embedding-models`. From Backend, storage checks run with `python3 -m unittest test_memory_vectors`. No production migration, hosted model installation or app deployment. Hosted resource measurement is required before enabling this on the 1GB service.
