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
