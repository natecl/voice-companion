# Real account lifecycle QA preparation

September 30, 2026. Historical preparation record. The subsequent interactive
[Google and Apple run](account-lifecycle/README.md) passed its bounded checks.

The Release simulator app uses source `7f715477a15b92f65a4e0a31dbf3885baf17a20d`
with a temporary localhost account endpoint and account deletion enabled only in
this QA binary. The source Phone Info plist was restored. Bundle version is
0.1.0 (1); executable SHA256 is
`3151e25d7d9a4d77a4ad0e11fdeda5bc5a9f26d9871a493b134c5f35d62cc3dd`.
Build and code-signature verification passed. Install and launch succeeded on
the separate **Ellis Real Account Lifecycle** simulator
(`2DABEECA-2BFE-4B62-8B92-DA8972B49D0D`). The initial screen was inspected:
existing Google-first/Apple sign-in presentation, no enrolled account.

`scripts/qa/real-account-server.py` runs the actual account adapters and deletion
workflow against empty, private local databases. Every generation reservation
is rejected. The positive one-microUSD Admission constructor value is not usable
spending capacity. No hosted database is opened. The localhost certificate is
trusted only by this dedicated simulator. Health and both sign-in challenge
routes passed; initial status has zero identities, sessions and instrumented
provider calls. This is preparation evidence, not real-provider acceptance.

Private runtime files are under
`/Users/n.chinlue/.config/ellis/qa/account-lifecycle-20260930`.
Use `endpoint.txt`, `status.json` and `build-receipt.json` there to inspect the
current run. Do not commit the directory: it contains keys and will contain real
QA account data. The harness refuses an existing usage database; do not erase
the directory to work around that guard if a process needs recovery.

Before interactive testing, explain the sequence and obtain explicit readiness:
Google sign-in, relaunch/session check, deletion with real grant revocation;
then Apple. Revocation may require signing into Ellis again elsewhere. It does
not delete the provider's Google or Apple account. Existing hosted recordings
are outside this local erasure test. Record sanitized observed transitions and
provider outcomes; never infer success from a button tap or user confirmation
alone. At preparation time no sign-in or revocation had been initiated. See the linked
run record for subsequent actual outcomes.

Hosted rollout, populated cross-owner isolation, founder-data migration,
physical-device acceptance and distribution remain separate unfinished gates.
