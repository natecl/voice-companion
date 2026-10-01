# Independent review: raw report and disposition

- Reviewer: fresh-context, read-only Cursor `generalPurpose` subagent, model Claude Opus 5.5 High (`claude-opus-5-5-high`), agent ID `700d3927-3441-4654-8a79-192d12134048`. The coordinator separately inspected the completed reviewer card labeled Claude Opus 5.5 High.
- Reviewed tree: base `9c824acc0014eeedb1413f0646b0f7f0b2d3dcbd`, `account_sessions.py` diff sha256 `b4664e8d01b5c3fa`, test file sha256 `595cff8b8df18f84` (15 tests, before the reviewer-driven test changes below).
- Final tree after disposition: same production diff `b4664e8d01b5c3fa`, test file sha256 `7a1e21fb620c03a3`. Final receipts were rerun on that file; see the README evidence table.

## Raw report (verbatim)

No blocking findings. The `account_sessions.py` fix is correct, minimal and safe, and the base behavior is a real, low-impact defect against the documented contract. Everything else is low or nit: gaps in test coverage, wording in the README, and one observation outside this lane's allowed files. I modified nothing in the repository.

### Commands run

| Command | Result |
|---|---|
| `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=Backend …/python -m unittest -v test_google_refresh_contract` | 15 run, 15 pass |
| Aggregate (new suite plus the 14 listed modules), same environment | 99 run, 99 pass |
| Base check: `git show 9c824acc:Backend/account_sessions.py` written into a new temp dir under `$TMPDIR` (`review-base-wslp`, left in place), then `PYTHONPATH=$B:Backend … test_google_refresh_contract` | 15 run, 3 fail, 12 pass. The 3 failures are the deadline-replay tests (direct, owner lookup, socket), each `'unauthorized' != 'refresh_replayed'`. I confirmed the import resolved to the temp base file. |
| Read-only `git status`/`diff`/`show` and `shasum` | Diff hash `b4664e8d01b5c3fa`, test file `595cff8b8df18f84` and base file `8d51ae315be1be90` all match the evidence file headers |

### A. The `account_sessions.py` change: no finding

- **The base behavior is a real defect.** The account backend QA doc (`docs/qa/account-backend/README.md:11`) and the native accounts doc (`docs/qa/native-accounts/README.md:55`) both say replay revokes the family with no deadline exception. On base, both functions checked the deadline before the consumed flag. So a replay after the deadline returned `unauthorized` and left the newest access token alive. Impact is small: that token lives for less than an hour past the deadline, and the theft signal is lost.
- **Nothing that should succeed is newly rejected.** Issuance (the `else` branch, `account_sessions.py:131-138`) still requires not consumed, not revoked and not expired, checked inside `BEGIN IMMEDIATE`. The only new effect is that a replay after the deadline revokes credentials that can be at most an hour from expiry. Native never resends a consumed secret: `AccountSessionManager.swift:69-77` clears the account on any rotation error, and `current()` drops the account past `refreshExpires`.
- **Native sees no semantic change.** The only change visible outside the backend is `unauthorized` becoming `refresh_replayed`. `AccountTransport.swift:162` maps both to `signInRequired`, and `scripts/qa/real-session-refresh.py` already expects `refresh_replayed`.
- **No new TOCTOU.** `refresh_owner` is advisory; `refresh` re-checks expiry and revocation inside its transaction (`:117-130`). If the deadline passes during Apple validation, the result is `unauthorized` with no issuance. The consumed branch in `refresh_owner` always raises. Both callers (`account_service.py:89`, `account_deletion.py:100`) call it outside a transaction, so the nested `BEGIN` it triggers is safe.
- **Side effect worth knowing:** `delete_account` with a consumed secret after the deadline now revokes the family and returns `refresh_replayed` (it used to return `unauthorized`). That's consistent with the contract but untested (see B3).

### B. Tests

1. **Low.** `test_google_refresh_contract.py:109-128`, used by the race tests at `:236-275`. The race helper accepts either outcome but never records which interleaving actually happened, so a run proves nothing about the order it didn't hit. The 5/5 stability runs don't show that either. This is mitigated: both sequential orders are covered deterministically elsewhere (`:206-210`, `:222-228`, `:278-283`, and `test_account_sessions.py:58-64`). **Action:** either record the outcome counts in the evidence, or describe these as tolerating either interleaving, without claiming both orders were exercised.
2. **Nit.** `:190`, `:212`, `:297-300`. The "restart" only builds new `AccountSessions`/`MemoryStore`/`AccountDeletion` objects on the same open Admission connection. **Action:** reopen the ledger with `self.ledger()`, or call it "new service instances."
3. **Low (missing coverage).**
   - The deadline-replay test (`:160-170`) checks preservation for another owner (BRAM) only, not for another login of the same owner after the deadline.
   - Nothing covers deletion `begin` with a consumed secret after the deadline (the behavior change noted in A).
   - Nothing covers a signed-out (revoked), unconsumed secret after the deadline. This is trivial.
4. **Nit.** `:362`. The `expired` request uses a secret that is both past the deadline and family-revoked, so `unauthorized` doesn't isolate expiry. The name overstates it slightly.
5. **Nit.** The `google.calls == []` checks on refresh paths (`:366`, `:396`) can't fail, because refresh has no reference to the revoker. The meaningful no-provider checks are `verifier.verify.assert_not_called()` and `validate_refresh` call counts. Not vacuous, just low value.

Everything else holds up:
- No fixture-clock problems. The newest access expires at the deadline − 1 + 3600 (or − 60 + 3600), and BRAM is enrolled late enough to stay valid.
- Owners are separate. The deletion race uses a fresh subject per round, built before both enrollments.
- Failures fail loudly. A non-`Rejected` exception or a timeout propagates as a test error, never a silent pass.
- The held-revocation test is stricter than production, which serializes those operations with `AccountService.mutations`.
- The final-revocation test asserts exact call counts and the durable `pending` state.

### C. README (`docs/qa/google-refresh-contract/README.md`)

It correctly separates the verified defect, the missing coverage and the unresolved provider/product semantics. Its table matches the raw files (84, 15/3 failed, 15, 99, 5/5) and the hashes match.

1. **Low (outside this lane's files).** The README cites `docs/qa/account-backend/README.md:11` as the contract. That same line also says rotation "revokes old access," which the code intentionally doesn't do (`account_sessions.py:133-135`, `test_account_sessions.py:39-46`, `native-accounts/README.md:55`). **Action:** flag this drift in the PR, or fix it in a separate docs change.
2. **Nit.**
   - The phrases "family-scoped replay across restart" and "Restart keeps the reservation" are slightly overclaimed (see B2).
   - The native bullet "any rotation error clears the local account" is not quite exact: it only clears if the generation is unchanged (`AccountSessionManager.swift:70`).
   - "Rotation racing sign-out…" should say the order isn't asserted (see B1).
3. **Nit.** The evidence headers aren't uniform:
   - `baseline-aggregate.txt` omits `PYTHONPATH` and the working directory.
   - The run headers omit the `PYTHONDONTWRITEBYTECODE=1` that the README's reproduce command uses.
   - `repeat-stability.txt` doesn't include the command.

   Consider also stating the defect's impact bound: under an hour of the newest access token, plus the lost theft signal. The duplicate-writer process note can't be verified from the repository, but it is consistent with the files.

### D. Other security observations

1. **Low (outside the allowed files): `account_deletion.py:143-171`, `account_service.py:107-111`.** `finish_google` revokes whatever `google_refresh_token` the client sends. Nothing binds that token to the deleted owner's Google subject or to the Ellis client. Any token Google accepts gets a 200, which completes deletion and releases the identity reservation. Only the holder of the deletion request secret can do this, and content is already erased, so impact is limited: Ellis consent may remain on Google while the server records completion. **Action:** the README already says a successful response isn't proof of propagation. Add that the server also can't verify the token belongs to the deleted identity. Any binding is a product decision, not in this lane.
2. **Nit (outside the allowed files): `account_service.py:45`.** The `mutations` lock is held across the Google revoke call (up to about a 5-second timeout), which blocks all account operations for all users in the meantime. This is intentional per the code comment and is about availability only.
3. **No finding** in `provider_grants.py` for this boundary. Google families remain refreshable after external consent removal until the 30-day deadline. That matches the stated constraint, and the README correctly lists it as unresolved.

**In-scope verdict:** no change needed in `account_sessions.py` or `provider_grants.py` beyond the reviewed diff.

## Disposition

| Finding | Disposition |
| --- | --- |
| A (fix correctness) | Accepted; production diff unchanged (`b4664e8d01b5c3fa`). |
| B1 race order not recorded | README now says the race tests tolerate either interleaving and do not record which order occurred; sequential orders are covered deterministically. No test change. |
| B2 restart did not reopen the ledger | Fixed: `restart()` reopens both SQLite files with new service objects; used in three tests. |
| B3 missing deadline cases | Fixed: same owner's other login preserved and refreshable after the deadline; deletion `begin` with a replayed secret after the deadline returns `refresh_replayed` and creates no deletion row; revoked-and-expired secret returns `unauthorized`. |
| B4 misleading `expired` name | Fixed: renamed to `revoked_and_expired`. |
| B5 low-value `google.calls` checks | Kept; harmless. Meaningful no-provider checks are the verifier and `validate_refresh` counts. |
| C1 drift in `docs/qa/account-backend/README.md` ("revokes old access") | Reported to the parent; outside this lane's file ownership, not edited. |
| C2 README wording | Fixed (restart, native generation guard, race order). |
| C3 evidence headers / impact bound | Final receipts now record cwd, `PYTHONDONTWRITEBYTECODE=1`, `PYTHONPATH`, exact commands and hashes. The raw baseline file is retained unchanged; the README states its environment. Impact bound added. |
| D1 unbound Google revoke-token identity | Recorded as an unresolved provider contract in the README. No implementation; outside this lane's file ownership and needs a product decision. |
| D2 mutation lock held across revoke | Reported; intentional, availability only. No change. |
| D3 | No finding. |
| "duplicate-writer process note" | Corrected after parent QA: the README now records the unexpected changes with unknown authorship. |
