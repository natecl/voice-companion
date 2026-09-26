# Gbrain comparison: local infrastructure checkpoint

September 26, 2026. Founder authorized testing gbrain as a possible memory backend. Adoption remains undecided. The existing iPhone app, production backend and user data are unchanged. No GitHub fork or gbrain service was created. Interrupted Sol comparison work is preserved on `companion/independent-support-screen` at `e9ee2ae` and has not been integrated.

## Reproducible setup

Pinned upstream: `garrytan/gbrain` commit `46ad5153a362815e4bd7a21f804561d492816fc5`, version 0.58.1.0. Bun 1.3.14, macOS, PGLite disk-backed scratch database. Cloned under ignored `work/gbrain-evaluation/upstream`; installed its locked dependencies with `bun install --frozen-lockfile --ignore-scripts`. No global plugin or agent configuration was installed. Provider credentials were omitted with `env -i`; explicit provider transport guards recorded zero calls in the custom probe.

Run from the repository root, using fresh output directories:

```sh
python3 scripts/evaluations/companion-replay.py work/gbrain-evaluation/companion-new
env -i PATH="$PATH" bun scripts/evaluations/gbrain-keyless.ts work/gbrain-evaluation/upstream work/gbrain-evaluation/gbrain-new Backend/fixtures/gbrain-comparison/sources.json
```

The gbrain script checks the pinned revision. Its scratch GBRAIN_HOME, database and usage log stay inside the output directory. It calls the shared MCP dispatcher used by the upstream transports; it does not exercise an HTTP listener or production multi-user authentication. The current backend executes its actual writer with nine exactly matched saved provider responses, then deletes and reopens the database. That is replay evidence, not a fresh model comparison.

## Observed results

The two sources are the same synthetic Project Juniper recordings from our existing QA: the original library location and its community-center correction. Gbrain receives their original text as meeting pages and explicit fact writes for storage testing. This deliberately does **not** present hand-authored facts as successful automatic extraction.

| Check | Gbrain keyless path | Current backend replay |
| --- | --- | --- |
| Store/recall location | Passed | Passed |
| Source provenance | Present as supplied string | Structured original-source support |
| Automatically replace library with community center | Both remain active; no embeddings configured | Correction active, library superseded |
| Delete recording removes its dependent fact | Failed for free-text provenance | Passed, including reopen |
| Delete with structured extraction-style metadata | Fact remains recallable | Structured support invalidated |
| Explicit fact withdrawal | Passed; stale reinsertion rejected | Not a user-facing feature; source deletion tested |
| Scoped reads | Other source cannot recall the fact | Other owner cannot recall the fact |
| Known split preference retention | Not tested: extraction disabled | Known failed retention preserved |

The structured gbrain probe seeded the DB-only fact shape documented in `src/core/facts/backstop.ts`: source/session/context metadata, entity and visibility. It verified visibility before deletion and recall afterward. This isolates storage linkage; it is not a live run of gbrain's extractor. Gbrain's keyless correction result is a documented degraded mode, not evidence that its embedding-enabled correction path fails. Nor does this prove every gbrain deletion configuration fails. These outcomes identify adapter requirements for our recording-level invalidation contract.

The upstream `test/memory-verbs-conformance.test.ts` passed all 36 tests (156 assertions). The first invocation failed because our scratch GBRAIN_HOME contained `..`; using a canonical absolute path fixed our setup without editing upstream. Both logs are retained locally. Gbrain was not blamed for that setup error.

The custom PGLite process reported approximately 1.64 GB peak RSS on this Mac. This is a local cold-start peak, not steady-state server usage or a Postgres deployment measurement. It does not establish fit on our existing 512 MiB Render service; a hosted capacity check or a different deployment topology is required before adoption. No hosting upgrade is authorized.

Evidence: synthetic requests, responses and checks in `Backend/fixtures/gbrain-comparison/`. No paid calls, audio, or manual device QA were used. This checkpoint tests selected contracts, not complete consumer-product readiness.

## Next comparison gate

Before choosing a backend, run bounded real extraction and retrieval on the same frozen everyday transcripts: project preference and correction, family/pet/student context, competing subjects, quotation, negation and topic changes. Use the same extraction model where supported for the controlled comparison, record all provider/configuration differences, and distinguish keyless, embedding-enabled and native-recommended configurations rather than combining their results. Never silently label a substituted configuration as the default.

Compare retained supported facts, false attribution, useful source retrieval, correction and deletion behavior, latency and total provider work. Replay existing matching responses on our side where valid. Do not lower acceptance thresholds or add repeated prompt tuning to make either backend win. A passing model comparison still requires source-to-passage mapping, answer invalidation and constrained-host validation before integration.

The existing $3.20 QA subledger is exhausted, including the prior Sol screen. Proposed additional allowance: up to $0.50 within the unchanged global $5 cap, with per-call reservations, a total cap, fixed cases, no automatic retries and saved responses. Actual testing stops at the cap or on a substantive failure requiring a decision. This allowance is not yet approved. No paid work starts until the founder approves it.

## Approved revision after initial results

The founder explicitly accepts retained memories after recording deletion and their continued use in answers. The earlier deletion rows above measure the previous contract; retained facts are no longer an adoption failure. Citation availability and disclosure still need an adapter. The deployed app has not changed. An additional allowance of up to $0.50 is now approved, within $5 globally, for bounded model-backed comparison. Reservation is per-call against both the evaluation ceiling and existing global/category headroom; unused authorization is not spend.

## Model-backed checkpoint

Completed a bounded four-case screen using the pinned revision, `gpt-6-luna` with reasoning `none`, and real `text-embedding-3-small` vectors (1536 dimensions). These are controlled model choices, **not gbrain's default Sonnet configuration**. The adapter maps gbrain's original prompt/messages/schema to Responses API with non-strict JSON schema; no prompt appendix or case-specific tuning. Sources are synthetic anonymous-speaker transcripts. Their words are shared with the control; gbrain receives its documented speaker-prefixed text format, whereas our extractor receives passage objects and original speaker metadata. This is not byte-identical input or an exhaustive benchmark.

Observed and manually reviewed:

- All four retrieval questions put a relevant recording first. Native hybrid page search used real embeddings; this is a small corpus, not proof of large-library recall or answer correctness.
- Everyday facts about swimming, a dog's allergy and a student's studies/preferences were extracted. Negation and Nora's undecided move were preserved; hypothetical Sam quitting was not asserted as fact.
- The fragmented morning preference was extracted with no named subject. Our current extractor correctly proposed the Juniper preference; our previously saved full-writer replay still shows the later admission/retention miss. Changing storage would not by itself resolve our verifier problem.
- Gbrain generated and retained “The user's dog Milo…” from an anonymous speaker saying “our dog Milo.” That account-owner attribution is unsupported. “Maya is my daughter” also remains deictic. Our extractor proposed named Maya/Milo facts without claiming account ownership.
- Both library and community-center facts remained active; extraction reported no supersession. All stored entity references were null in this DB-only setup without existing canonical entity cards. This establishes the tested integration's gap, not failure of every gbrain entity/fence-backed configuration.
- The four `recall(query)` responses also included all twelve recent facts, independent of query. Page ranking worked, but an answer-context adapter would still need to select facts and handle conflicts.
- The correction remained recallable after deleting its recording. This **passes the revised retention preference**. Original-source availability, deletion disclosure and citation rendering are still integration work, not tested app features.

Evidence: `model-review.json`, `companion-extraction-result.json`, `model-budget.json`, and the full compressed `model-result.json.gz` under `Backend/fixtures/gbrain-comparison/`. The compressed report preserves provider payloads/vectors, operation receipts and queries for replay; no credentials or user recordings. Our new control tests extraction proposals only, not full Jev admission for the two new everyday cases. The earlier nine-call writer replay remains the full-path evidence for the original two sources.

### Cost and harness verification

Founder authorization: up to $0.50. The canonical global ledger records **27 completed unique calls: 8 Luna and 19 embeddings**, reserving **$0.038868** conservatively. Global reservations are **$4.010868 / $5**. Successful repeated requests replayed saved responses without another reservation. The previous $3.20 profile subledger was not enlarged or reused; this evaluation reserves directly against global and existing ask-category headroom, with its own $0.50 ceiling. No application quotas or hosting plan changed.

Reported usage: 10,554 Luna input tokens, 1,730 output tokens and 359 embedding tokens. At a conservative $0.125/M Luna input (including cache writes), $0.50/M output and $0.02/M embedding input, the estimate is about **$0.0022**, not an invoice. Reservation bounds use higher input/output rates plus framing room. Official references checked September 26: [Luna](https://developers.openai.com/api/docs/models/gpt-6-luna), [embedding model](https://developers.openai.com/api/docs/models/text-embedding-3-small).

The initial operator harness used the wrong global-ledger state (`reserved` rather than `active`); the database rejected it before provider calls. The corrected test mirrors the actual CHECK constraint. Further local passes repaired pending-write receipt handling, per-call SSH connection resets, and concurrent embedding transport serialization. Completed responses were cached throughout; these are harness setup issues, not gbrain model failures. Gbrain's built-in price table lacks Luna, so the separate canonical reservation guard enforced costs. Automatic extractor retries and unexpected extra model calls were blocked. No failed paid call was automatically retried.

Six offline guard tests cover duplicate attempts, evaluation cap, existing global/category spend, model allowlist and bounds. Final actual behavior completed in `work/gbrain-evaluation/model-v7/`; the control completed in `companion-extraction-v1/`. Final offline replay reproduced all four top-ranked recordings, the twelve returned facts and retained correction with zero provider cache misses. An additional exact-tail comparison failed: the first replay query omitted one weakly semantic distractor present in the live run. Its cause is unresolved; this screen does not establish deterministic lower-ranked results. Both full reports are preserved, including `model-offline-result.json.gz`. No paid rerun was needed.

Reproduce guard checks:

```sh
python3 scripts/evaluations/test_gbrain_provider.py
```

The operator provider helper runs only on the existing credential host and exposes a bounded JSON-lines transport over SSH; it is not imported into the service. Paid reproduction requires an unspent approved allowance and canonical reservation headroom. `gbrain-model.ts` accepts prior `.json` or `.json.gz` reports as trailing arguments to reuse provider responses. A future changed request must be deliberately reviewed; never rerun paid calls merely to repair presentation or score existing results.

### Recommendation

Do not migrate based on this screen. Gbrain provides useful retrieval and persistence machinery, but this configuration would still need companion-specific identity, entity, lifecycle and context-selection work. Our system also has a real later-stage retention miss to fix; the passing extraction control does not clear it. Prefer a focused repair of that known judgment problem over an immediate backend replacement. A full default-model/canonical-entity benchmark or adopting gbrain remains a separate decision. Recording-retention semantics are approved but have not been implemented or deployed in the app by this evaluation.

Offline behavioral reproduction (requires the pinned local checkout and locked dependencies):

```sh
env -i PATH="$PATH" GBRAIN_EVAL_OFFLINE=1 bun scripts/evaluations/gbrain-model.ts work/gbrain-evaluation/upstream work/gbrain-evaluation/new-offline Backend/fixtures/gbrain-comparison/model-result.json.gz
```

Observed provider API durations for the four extraction calls: gbrain prompt median 2.03 seconds (range 1.44–4.07); control prompt median 3.00 seconds (1.72–3.47). These are tiny-sample request durations, excluding SSH and database/indexing overhead, not production end-to-end latency or a robust speed comparison.
