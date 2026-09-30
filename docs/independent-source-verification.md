# Independent source verification — verified internal rollout

> Historical verifier checkpoint. The statement that recording-deletion retention is unimplemented is superseded by the retained-memory rollout; preserve the original independent-verification evidence and its limits. See [current state](current-state.md) for selected behavior and current evidence boundaries.

Current status: enabled internally after the separately approved funding and [hosted rollout check](verification-rollout.md). The preparation and QA history below records the earlier checkpoint boundary.

Founder direction: keep our backend and fix supported memories being rejected. Ordinary recording deletion retaining memory remains a separately approved, unimplemented change.

## Failure and resulting behavior

The deployed Jev verifier rejected the saved Juniper preference at probabilities 0.66 (support), 0.77 (modality), and 0.56 (time), below the unchanged 0.90 gates. Extraction was correct. Earlier atomic classification improved metadata but still rejected factual support. A prior paid Sol screen passed 17 source-only support cases; that alone was insufficient for integration acceptance.

The new `independent-source-v2` recording path:

1. Luna extracts proposals and original evidence.
2. GPT-6 Sol, low reasoning, independently judges each claim against original transcript passages: supported, contradicted or uncertain. It returns original passage IDs, without invented confidence scores.
3. Application code preserves the full original cited passages and their exact spans, along with extraction evidence. Unknown/empty citations fail validation. Existing four-excerpt and 2,000-character-per-quote limits still apply; oversized evidence fails explicitly rather than being truncated. Added context cannot silently establish one speaker's identity.
4. Jev independently classifies modality and source-reported temporal status. Existing 0.90 gates and explicit temporal-expression verification remain. An uncertain time stays unresolved, never silently current.
5. Existing recording identity, pairwise identity, correction/applicability, expiry and atomic storage rules remain in force. Personal text and the non-Luna-identity path retain their previous verifier.

This is a separate source-only judgment, not Luna verifying its own extraction or statistical independence between model errors. It is not a repeated vote or a fallback after Jev rejection. We do not stack the rejected old Jev support score as another veto after Sol.

## Behavioral QA and discovered defect

The first new live run recovered the preference but rejected the location because Sol also cited its surrounding preference passage. The extractor's evidence omitted that passage. Paid calls stopped after this substantive failure. The fix retains complete original verifier evidence instead of discarding it or requiring the extractor and verifier to choose identical passage sets.

The second run reused those exact provider responses. Only changed/new requests incurred calls. Through the actual SQLite writer with chunking, semantic-boundary, expiry and consolidation settings enabled:

- Morning preference and library location both became active.
- A subsequent correction superseded the library with the community center for the same entity; the preference remained active.
- Saved state survived reopening, with no account-owner profile links inferred.
- The frozen six-case verifier gate admitted named-family and student preferences; rejected negation, unsupported account ownership and quoted-person attribution; and rejected future-as-current metadata despite factual support.

The six-case gate tests verification decisions, not six fresh extraction pipelines. Actual writer integration uses the Juniper source and correction. This is bounded development evidence, not a population accuracy benchmark. The prior 17-case support screen and prior default-path rejection remain preserved. Its prompt/schema match the candidate, but its output cap was 1,800 rather than 1,300 tokens; it is historical supporting evidence, not an exact-request replay of the current configuration.

Files under `Backend/fixtures/source-verification/` contain initial failed calls/results, verified calls/results and the frozen input cases. These are synthetic transcripts. Cached responses are reused only when the complete request fingerprint matches. Offline tests run the actual writer against the exact live responses with a transport that cannot call providers. They also cover stale/deleted-source races, unsupported outcomes, citation preservation and incompatible cached verification versions in both flag directions.

Reproduce without credentials or paid calls (choose a new output directory):

```sh
PYTHONPATH=Backend python3 Backend/evaluate_source_verification.py work/source-verification/replay-new --replay Backend/fixtures/source-verification/initial-calls.json --replay Backend/fixtures/source-verification/verified-calls.json --transport false
```

## Allowance and accounting

The founder approved $0.25 specifically for this QA. An operator-only subledger reserves before every new network request, rejects repeats of failed/reserved requests, and preserves completed responses. No automatic paid retries occurred. `scripts/evaluations/source-verification-provider.py` records the credential-host transport used; it never prints keys.

The global $0.25 reservation is funded from unused recording-budget headroom under the explicit approval ID `independent-verification-20260926-025`. Its global `stt` category identifies funding, not transcription usage; the separate model ledger records actual providers. No audio was transcribed, no runtime policy/quotas were increased, and no gbrain allocation was repurposed. Global reservations now total $4.260868 of $5.

| Model | New calls | Conservative reservations | Input / output tokens |
| --- | ---: | ---: | ---: |
| GPT-6 Sol | 3 | $0.074248 | 1,351 / 306 |
| Jev | 8 | $0.080000 | 6,711 / 873 |
| GPT-6 Luna | 3 | $0.009907 | 1,739 / 264 |
| Total | 14 | $0.164155 | |

All 14 attempts completed; the remaining $0.085845 is unspent QA allowance, not automatically available for normal app learning. Reservations are conservative bounds, not a billing invoice. The full $0.25 remains reserved globally.

Local verification: **57 targeted tests passed**, covering the source verifier, historical support screen, original subject-continuity failure, atomic classifier, writer/chunk behavior, runtime startup and budget controls. The exact-response replay made zero provider calls. `git diff --check` passed. Review found and fixed the citation-loss and old-version cache issues before merging.

## Runtime and rollout boundary

`VOICE_ENABLE_INDEPENDENT_VERIFICATION=1` explicitly enables this path only with memory rework. It is off by default. The hosted adapter and ProfileBudget opt-in admit Sol with a conservative $0.04 reservation per request, while retaining the approved aggregate cap and no-retry policy. The support request builder enforces its matching cost bound. A local actual-hosted-process test checks startup/history recovery without queued learning or new spend; budget tests prove enablement cannot mint credit.

This checkpoint is code and provider-backed writer verification, **not deployment or physical-app acceptance**. No hosted flag or app build was changed. The existing app-learning allocation is exhausted; this separate QA ledger is not silently transferred into production learning. Rollout needs an explicit funding path before enabling new learning. No old source is automatically reprocessed; recovery of previously missed memories must be deliberate. Turning the flag off does not erase already learned memories; paused jobs from a different verifier contract fail explicitly for review.

## Research review — September 26, 2026

At the founder's request, a GPT-6 Luna agent at max reasoning used the last30days skill to investigate this separation. The findings support a design hypothesis, not a model-performance guarantee:

- [Fortunate Recall](https://arxiv.org/abs/2609.10413) studies temporal validity and supersession metadata. It supports treating lifecycle state explicitly, but does not validate transcript-to-claim entailment in this application.
- [CLAIM-CAL](https://link.springer.com/article/10.1007/s44163-026-02240-w) studies confidence calibration on a different task with a small calibration set and model-based judging. Its results do not calibrate Jev's probabilities or establish Sol's accuracy here.
- A [September 25 practitioner discussion](https://www.reddit.com/r/AI_Agents/comments/1wpzjri/memory_layer_for_ai_agents_is_totally_fucked/) reports stale preferences, query-dependent answers and entity splitting. This is anecdotal motivation for regression cases, not comparative benchmark evidence.

Decision: evaluate factual entailment against original passages separately from modality, temporal state, identity and lifecycle policy. Do not add the old Jev factual-support score as a second veto after Sol, and do not lower confidence thresholds without labeled calibration evidence. Different models can still make correlated errors; independent verification means a separate source-only judgment, not statistical independence.

Research limitations: the automated search returned substantial off-topic material; Reddit retrieval was partial and rate-limited, and YouTube transcript retrieval returned no transcripts under rate limiting. Primary-source web reads supplemented the search. The frozen live QA gate remains the deciding evidence for this implementation.
