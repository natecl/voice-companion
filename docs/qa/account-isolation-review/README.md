# Account isolation review — September 30, 2026

Bounded independent review on `codex/restore-deletion-guard`, base
`9ca0e3fddd8be46b6dd700662175219a87a5200c`. Synthetic identities, temporary
SQLite databases and actual loopback WebSockets only. No live provider, private
account, simulator, physical device or paid API was accessed. The root agent
owns the production fix; this review owns the regression and these receipts.

## Confirmed finding and fix

**P1: revoked sessions could still receive companion content on an already-open
socket.** Baseline `Backend/companion_service.py:54–68` authenticated before
waiting for the initial request, then returned history, a source or an existing
answer without another authorization check. Its generation monitor checked at
250 ms intervals; `:106` could emit a subsequent provider delta after revocation
and before that monitor ran. `AccountSessions.sign_out` correctly revoked the
family, but existing sockets were not closed by that operation.

Four deterministic regressions fail against the baseline CompanionService:

- Connect, wait until server awaits the request, sign out, request history:
  complete synthetic question and answer were returned.
- Sign out after the SQLite history read has produced its result but before the
  executor returns it: complete history was returned.
- Connect, sign out, replay a completed question ID: the saved answer was returned.
- Sign out between two synthetic provider deltas without yielding to the
  periodic monitor: the second delta was returned.

The root fix reauthorizes after request reception and immediately before each
non-error response (`Backend/companion_service.py:52–61`). The same send boundary
covers source, history, existing replies and streamed content. Errors remain
sendable so a revoked client receives `unauthorized`. Independent inspection
found this fix appropriately scoped. All four regressions now pass; the streamed
case also verifies a failed durable turn and settled usage reservation.

This is stale-session disclosure of that session's owner content, not evidence
of a direct owner-A credential reading owner-B data. Owner-scoping checks in the
reviewed service/store paths remain server-derived. Existing two-owner socket
and identity/session tests passed.

## Reproduction and raw evidence

Final command, from the repository root:

```sh
PYTHONPATH=Backend /tmp/ellis-auth-venv/bin/python -m unittest Backend.test_account_isolation_regression Backend.test_companion_service Backend.test_account_sessions Backend.test_account_identity Backend.test_account_service Backend.test_account_deletion_recovery Backend.test_provider_grants -q
```

Result: **38 tests passed**. [Raw final output](fixed-regression.txt).
The environment was macOS with Python 3.13 and the existing isolated auth venv.
Final tested SHA-256 values:

```text
8021afdd6cfc1ce9a85b14d8fdc013e6fbe60e0169331083ed1f8c3cb3036458  Backend/companion_service.py
e80336d517f2d6f111221be8c082480f1cce9632602a0afd4095120df2321f41  Backend/test_account_isolation_regression.py
```

[Baseline output](baseline-regression.txt): **four expected failures**. Baseline
replay used the committed CompanionService loaded into memory; it did not alter
the shared checkout or other workers' changes:

```sh
PYTHONPATH=Backend /tmp/ellis-auth-venv/bin/python - <<'PY'
import subprocess, types, unittest
import test_account_isolation_regression as regression
baseline = types.ModuleType('baseline_companion_service')
exec(subprocess.check_output(['git', 'show', '9ca0e3fddd8be46b6dd700662175219a87a5200c:Backend/companion_service.py'], text=True), baseline.__dict__)
regression.CompanionService = baseline.CompanionService
result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(regression))
raise SystemExit(not result.wasSuccessful())
PY
```

## Acceptance gap map

| Contract | Evidence from this review | Remaining evidence |
| --- | --- | --- |
| Stable ownership, provider separation, refresh replay and sign-out | Existing identity/session/service fixtures pass; new stale-socket regressions pass | Live provider/final native configuration acceptance is not established here |
| Owner isolation and account switching | Existing two-owner SQLite/socket checks pass; reviewed native manager generation/owner guards and owner-keyed notes cache | Independent second-person isolation and physical lifecycle remain explicit feature-map gates |
| Deletion/recovery | Existing fresh-proof deletion recovery fixtures pass; reviewed identity/expected-owner checks and owner quiescence | Apple real-provider recovery/rotation and physical deletion must be supported by their own receipts |
| Backup restore and deletion retention | Separate assigned lane; not tested or modified here | Root must review that lane's exact restore evidence |
| Native cache/sign-out behavior | Read-only review of AccountRuntime, AccountSessionManager and owner-keyed cache; no additional critical defect reproduced | No new native execution evidence; fixture success cannot establish Keychain/device behavior |
| Delivery | Narrow fix independently reproduced and inspected locally | Not deployed; feature remains incomplete and later phases must not advance on this receipt alone |

The neighboring notes handler checks authorization after its executor read and
before returning content. Memory writes recheck before dispatch; their response
contains an acknowledgement rather than source text. This bounded review does
not certify every asynchronous persistence interleaving or all service routes.
