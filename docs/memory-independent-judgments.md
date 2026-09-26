# Memory rework checkpoint 3B — evidence lookup and independent judgments

The new candidate reader ranks owner-scoped claims and mention descriptions before limiting results. An old correction target therefore remains available behind 51 unrelated newer claims. It returns original supporting passages, provenance, lifecycle/identity status, matched count, and explicit truncation. Matching words or names does not establish identity. This is lexical/mention retrieval, explicitly marked semantically incomplete; embedding retrieval remains checkpoint 5.

Jev receives separate source-support, subject-attribution, modality and temporal questions. Each question carries the exact value and cited text it judges. A separate pairwise identity request sees old and new evidence; a separate semantic relationship request distinguishes replacement, duplicate, addition, conflict and uncertainty. Neither request writes memory.

Initial acceptance policies: support/modality/time >=0.90; attribution/identity/lifecycle >=0.95. Confidence is retained for diagnostics, not treated as a second independent vote. These are conservative initial policies with bounded fixture evidence, not a broad calibration claim. Uncertainty cannot authorize a write. Final application of accepted decisions through identity/correction storage remains checkpoint 3C.

Luna's change/previous-text fields are retrieval hints only. They cannot authorize or bypass lifecycle judgment, and pairwise comparison must also occur when an extracted change label says none. This avoids asking a source-only question to establish replacement of an existing memory it has not seen.

## Verification and failed evidence

Local real SQLite tests cover the older target, owner isolation, deleted evidence, truncation reporting, and unresolved identity. Request/parser tests cover separate aspects, per-role thresholds, uncertainty and size rejection. Recorded live responses replay through the actual decision policies.

```sh
python3 -m unittest discover -s Backend -p test_memory_judgments.py -v
```

Live QA used the isolated synthetic Render workspace and canonical QA ledger. The final four batched calls passed 15 designated checks: supported fact/subject/modality/time; rejection of false author attribution; unidentified recording preservation; explicit same-person correction; distinct other person; rejection of name-only and anonymous-speaker links; replacement versus added interest and historical description. These are independent model-contract checks, not full writer transition acceptance.

Two earlier calls are preserved under `fixtures/memory_judgments/failed`:

1. Index-only questions mixed several aspects and did not reliably separate subject scopes. Exact per-question claims, values and excerpts resolved the source checks.
2. Source-only change verification remained uncertain. Removed that redundant write gate; the separately tested old/new evidence comparison must authorize replacement. No thresholds were lowered; the positive replacement and negative addition/past-description gates remain mandatory.

Frozen request versions and final responses are retained. Six Jev calls total reserved $0.06, including failures; cumulative ledger 81 calls/$0.81 reserved, **$0.19 remaining** from the existing $1 allocation. Reservations are not verified billing. No deployment, production migration or transcription/device run occurred.
