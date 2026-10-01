# Google refresh and final-revocation contract

October 1, 2026. Base `9c824acc0014eeedb1413f0646b0f7f0b2d3dcbd` (PR184 merge). Uncommitted, not deployed. Backend-only synthetic evidence: fictional Google subjects, fake clock, fake Google revoker, temporary SQLite and loopback WebSockets. No provider network calls, real identities, credentials, model calls or native builds.

## Mapped boundary

- **Google Ellis-session refresh** (`AccountService` `refresh` → `AccountSessions.refresh_owner` → `refresh`) checks only local state: refresh-secret digest, family deadline, consumed flag and credential revocation. A Google owner has no stored provider grant, so no Google request is made. It does **not** observe external Google consent removal; an Ellis family stays refreshable until its 30-day deadline, sign-out, replay, local owner revocation or account deletion.
- **Apple refresh** additionally calls `validate_refresh` once per stored encrypted grant. `provider_authorization_revoked` revokes every local session of that owner; `identity_provider_unavailable` neither rotates nor revokes.
- **Local owner revocation** (`ProviderGrants.revoke_local_owner`) revokes every account-session credential of one owner. It is not an identity reservation: fresh provider proof can enroll the same owner again. Deletion adds the reservation separately.
- **Final Google revocation** (`AccountDeletion.finish_google`) runs after content erasure, calls the fixed Google endpoint once per explicit request, and releases the identity reservation only on success. Failures stay `pending` and are never retried automatically.
- **Native** (read only): a rotation error clears the local account unless a newer sign-in/sign-out generation has replaced it; `unauthorized`/`refresh_replayed` map to sign-in required; `google_authorization_revoked` routes deletion to fresh-proof recovery.

## Diagnosis

**Verified defect (fixed):** the documented contract says replaying an old refresh token revokes its whole family, including the latest access token ([account backend QA](../account-backend/README.md)). On the base, both `refresh` and `refresh_owner` checked the family deadline before the consumed flag. A replay after the deadline returned `unauthorized` without revoking the family. The newest access token, issued up to one hour before the deadline, stayed valid for up to an hour after it, and the theft signal was lost. The fix checks consumed secrets first in both paths. Expired, unconsumed secrets still fail without issuing or revoking anything. The only externally visible change is `unauthorized` becoming `refresh_replayed` for that replay, including through `delete_account`; native maps both to sign-in required. This edit appeared in the worktree from an unknown source before this lane wrote it (see Process note). This lane reproduced the failure independently on base source, reviewed the edit and adopted it unchanged.

**Missing coverage (added, passes on base):** malformed/unknown/cross-kind secrets, the exclusive deadline boundary, family-scoped replay surviving a reopened ledger, retry after a lost rotation response, sign-out and local-owner revocation across devices with other-owner preservation, refresh while Google revocation is held, durable final-revocation failures without automatic retry, and Google-versus-Apple provider-call behavior over sockets. Three race tests start rotation together with sign-out, local owner revocation or deletion `begin` on separate SQLite connections. Each accepts either interleaving and asserts that no owner/family credential remains live; they do not record which order occurred. Both sequential orders are covered deterministically by other tests.

**Unresolved provider/product contracts (not implemented):**

- **External consent removal:** whether removing Ellis from a Google account should end Ellis sessions before their family deadline (for example through Google Cross-Account Protection/RISC events). That would need a founder decision, new configuration and its own evidence.
- **Propagation:** a successful Google revocation response does not prove that external consent removal has propagated.
- **Unbound revoke-token identity:** `finish_google_deletion` revokes whatever Google grant the client sends. The server does not bind that grant to the deleted Google subject or the Ellis client. Any grant Google accepts completes deletion and releases the identity reservation, so Ellis consent could remain on the deleted user's Google account while the server records completion. Exposure is limited: only the holder of the deletion secret can send it, and only after content erasure. Binding the grant is a provider/product decision in files outside this lane (`account_deletion.py`, `account_service.py`, native); it is recorded here and not implemented.

## Evidence

| File | Run | Result |
| --- | --- | --- |
| [baseline-aggregate.txt](baseline-aggregate.txt) | 14 existing account/session/grant/OAuth modules, unmodified base (run from the repository root with `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=Backend`) | 84 passed |
| [failing-before.txt](failing-before.txt) | final red: final test file (sha256 `7a1e21fb620c03a3`) with base `account_sessions.py` extracted to a temporary module | 15 run, 3 failed, 12 passed |
| [after-fix.txt](after-fix.txt) | final green: same test file, fixed working tree (diff sha256 `b4664e8d01b5c3fa`) | 15 passed |
| [after-fix-aggregate.txt](after-fix-aggregate.txt) | new suite plus the 14 modules, same tree | 99 passed |
| [repeat-stability.txt](repeat-stability.txt) | new suite five times, same tree | 5/5 passed |
| [independent-review.md](independent-review.md) | raw independent review report and disposition | no blocking finding |

The three red tests are the deadline-replay tests: direct `refresh`, `refresh_owner` plus deletion request, and the loopback socket. All other tests pass on base and characterize existing behavior.

The reviewer-driven test changes have these final results:
- The other-login, revoked-and-expired and deletion-request deadline cases sit inside two of the red tests, so they fail on base and pass after the fix.
- The `revoked_and_expired` socket assertion sits inside the third red test.
- The three tests using `restart()` pass on both base and fix.

Reproduce from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=Backend /tmp/ellis-auth-venv/bin/python -m unittest -v test_google_refresh_contract
```

For failing-before, place `git show 9c824ac:Backend/account_sessions.py` in a temporary directory ahead of `Backend` on `PYTHONPATH`.

## Process note

Around 05:25Z, files this lane had not written appeared or changed in the worktree. **Their authorship is unknown.** The parent verified that no other authorized Google writer existed. The timeline alone does not identify an author, and this lane did not investigate further.

The observed changes:
- 05:25:01Z: `failing-before.txt` written, logging a 13-test suite with different test names.
- 05:25:09Z: the `account_sessions.py` edit.
- 05:25:17Z: `after-fix-test-authoring-error.txt` written.

At 05:25:28Z this lane wrote its own `Backend/test_google_refresh_contract.py`. That write replaced whatever test file was then at that path; the 13-test version is not recoverable. This lane's later `before-fix.txt` was mislabeled: it ran after the `account_sessions.py` edit, and its single failure was this lane's fixture-clock error. A correction header added at 05:26Z still attributes the edit to a "concurrent agent", which is superseded by this note.

The parent preserved the files outside the repository in `/tmp/google-refresh-conflict-snapshot-Sp1IAj` (`account_sessions.py`, this lane's then 12-test file, `evidence/`). The three superseded evidence files are also kept unchanged in [superseded/](superseded/):
- [unknown-source-failing-before.txt](superseded/unknown-source-failing-before.txt), sha256 `8e1d2d2248c25533`;
- [unknown-source-after-fix-test-authoring-error.txt](superseded/unknown-source-after-fix-test-authoring-error.txt), sha256 `1d0a0322c6d482f7`;
- [mislabeled-before-fix.txt](superseded/mislabeled-before-fix.txt), sha256 `1bb7548c3f589498`.

They are historical only and are not acceptance evidence. The parent then designated this lane as sole writer. Coverage named in the lost suite was rebuilt from its logged test names, and all current receipts come from this lane's final files.

## Independent review

Fresh-context, read-only Cursor subagent on Claude Opus 5.5 High; the coordinator also inspected the completed reviewer card. [Raw report and disposition](independent-review.md). On the test file it reviewed (sha256 `595cff8b8df18f84`), it reran the new suite (15/15), the aggregate (99/99) and the base-module check (3 failures), and matched the evidence hashes. It found no blocking production issue. The fix is correct and minimal, introduces no new check-then-act gap between `refresh_owner` and `refresh`, and issues nothing after expiry, revocation, sign-out or replay.

Fixed in this lane: restarts now reopen both SQLite files. Added coverage for the same owner's other login and the deletion-request path after the deadline, plus a revoked-and-expired secret. One misleading assertion name was corrected, and README wording was tightened (race order, restart, native generation guard, impact bound). Fresh final red/green receipts were produced on the final test file (sha256 `7a1e21fb620c03a3`). The reviewer did not rerun that final file.

Out of this lane's file ownership (reported, not changed):

- `docs/qa/account-backend/README.md` says rotation "revokes old access", but code and tests intentionally keep in-flight access until its original expiry. This is documentation drift.
- `finish_google_deletion` does not bind the grant to the deleted subject (recorded above as an unresolved provider contract).
- The account mutation lock is held across the bounded Google revoke call. This is intentional and an availability concern only.

## Not established

This lane does not establish independent-human isolation, physical iPhone/TestFlight behavior, real Google consent-removal propagation or production deployment. It does not repeat accepted Google/Apple deletion/relaunch evidence. Nathan's report of earlier mirrored physical Google-delete and Apple-delete happy paths (about 90% confident; exact build/date uncertain) remains credited.
