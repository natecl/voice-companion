# Agent-operated real-account simulator QA

The founder requested removing routine manual tapping from the QA loop.
`UITests/LiveAccountUITests.swift` now operates the actual app, system Google
permission prompt and observed saved-account chooser through XCTest. Application
UI, styles and runtime code are unchanged. Tests skip without explicit opt-in
and the dedicated simulator name. Result bundles contain provider identifiers;
keep them private and commit only inspected, sanitized evidence.

The runner `scripts/qa/run-live-account-ui.py` checks the dedicated booted device,
built and installed localhost endpoints, enabled QA deletion capability and a
fresh result path. It requires exactly one executed passing test, rejecting
skipped or zero-test results. Select individual steps; do not run this stateful
class as an unordered suite. No retries, password entry, account creation or
security-challenge handling is automated.

Build the Phone UI tests for Release against the dedicated simulator using a
private copied Info plist with the existing local service endpoint and deletion
enabled. Keep source plists unchanged. Build must succeed before running:

```sh
python3 scripts/qa/run-live-account-ui.py inspect \
  --directory /private/existing-account-QA \
  --derived-data /private/built-QA-derived-data \
  --result /private/new-inspection.xcresult
```

Available steps: `inspect`, `sign-out`, `apple-request`, `apple-pending`,
`apple-recovery-request`, `apple-recovery-complete`, `signed-in-restart`, `sign-out-google`, `google-permission`,
`google-account`, `google-request`, `google-pending`, `google-recovery`.
For account selection/recovery, set `ELLIS_QA_GOOGLE_ACCOUNT` from the current
observed chooser in the process environment, never in committed code. The
`google-recovery` step starts from the verified pending-deletion instruction,
handles the known returning-user flow and verifies signed-out restart. Stop and
inspect unfamiliar screens; this is not a general OAuth bypass.

## Executed behavior

September 30: the running local real-provider server and empty Google QA owner
were backed up. A separate synthetic app session submitted actual TLS deletion
and intentionally stopped at Google finalization; the original client receipt
was never installed in native Keychain. XCTest signed out, selected the saved
Google account, handled the system prompt and returning-user authorization,
and asserted the pending-deletion instruction. A second fresh Google proof
completed recovery and real grant revocation. The final recovery test executed
one test with zero failures in 14.4 seconds; screenshots were inspected. Restart
stayed signed out, and native account/outbox directories contained only erasure
markers. Backend inspection confirmed one recovery receipt, no new content
session, released identity reservation, erased owner/identity and unchanged
budget, policy and request rows. No founder taps or paid calls occurred.

See [receipt](automated-google-recovery.json),
[completion](automated-recovery-complete.png) and
[restart](automated-recovery-relaunch.png). The native binary hash is recorded;
application source is `ebcfbd2`, unchanged by this test-only checkpoint. The
earlier automatic-refresh check used its separately recorded Release binary.

The runner's actual inspect action passed, and a direct test invocation without
opt-in skipped without UI actions. Desktop coordinate input had failed with
`noWindowsAvailable` in both Device Hub windows; native XCTest resolved that
tooling limitation. An initial test compile used an element instead of a query
for `.count`; corrected it. The following stale-binary invocation executed zero
tests, which was detected rather than accepted. Build commands now fail fast and
the runner enforces a nonzero executed count. Preserve these failed private logs.

This is real Google fresh-proof recovery on the simulator with deliberate
interrupted-client setup. Apple fresh-proof recovery, physical erasure,
independent-human isolation and backup retention remain separate gates.

Apple follow-up: `apple-request` activates the existing app and taps its actual
Apple control. Release build and one executed test passed; direct screenshot
inspection showed Apple's existing-account sheet with **Sign In with Password**.
This is authorization-entry evidence only: enrollment and automatic Apple refresh
remain unverified. The password challenge requires the founder; no credentials
were entered. An initial entry test failed because it did not activate the app
after rebuilding; the test now explicitly activates it. Both private result
bundles are preserved (`live-ui-apple-entry.xcresult` and
`live-ui-apple-entry-2.xcresult`). No application/UI source changes or paid calls.

The founder subsequently completed the Apple password challenge. Direct
read-only database inspection verified one Apple identity and one newly issued
session (15 total historical sessions). `signed-in-restart` passed one executed
test: activate, assert signed-in profile, terminate, launch, assert profile and
absence of provider sign-in controls. The resulting screenshot shows Ellis Home;
the backend retained exactly the same session. See
[receipt](automated-apple-restart.json). The test runner closes its managed app
after completion; the operator launched it again for the natural refresh check.
The private pre-refresh snapshot is preserved; automatic rotation subsequently passed
the normal 600-second lead before 3600-second access expiry. No clocks, expiry
values or Keychain credentials were modified.

## Apple pending-deletion recovery support — not yet executed

The three added Apple steps are QA support only. Python syntax and source routing
were checked locally; these new Swift tests have not been built or executed.
They do not establish Apple recovery, revocation, erasure or restart acceptance.
The root operator owns the Release build and real isolated lifecycle execution
after the ongoing natural-refresh check finishes. Existing Google steps are
unchanged. No application UI, credentials, Keychain or server state is modified
by this implementation checkpoint.

Use only a disposable Apple QA account with an independently verified pending
server deletion. The operator must establish and inspect that prerequisite;
these tests neither create a pending deletion nor substitute a synthetic success
message. Run individual steps with the existing private localhost runner:

1. Use `apple-request` for the initial normal enrollment attempt and inspect the
   actual Apple authorization entry. Founder/system authorization is a separate
   handoff; do not enter credentials or click unfamiliar system dialogs blindly.
2. After that attempt returns the exact instruction, `apple-recovery-request`
   asserts **“Sign in with the same provider to finish the account deletion you
   requested.”**, verifies no signed-in profile or retry-deletion control,
   captures the refusal, and taps **Continue with Apple** for fresh proof in the
   same invocation. Inspect the entry attachment before the next founder/system
   authorization handoff. This step establishes only the app request and refusal,
   not completed provider authorization.
3. After real Apple authorization returns, run `apple-recovery-complete`. It
   requires the actual **“Your account was deleted.”** message, captures it,
   terminates/relaunches the app, and asserts both sign-in controls with no
   profile, retry-deletion control or pending-deletion instruction. Independently
   inspect backend recovery/revocation/erasure and unchanged unrelated-owner and
   spending state; UI success alone cannot prove those contracts.

`apple-pending` is an optional assertion-and-capture-only inspection of the same
refusal. Prefer the combined `apple-recovery-request` step when proceeding to
fresh proof: recovery mode is held in the application runtime, and XCTest may
close the app between invocations. A relaunch can discard this transient state.
If the exact pending instruction or completion message is absent, the test fails;
do not treat an ordinary signed-out screen as success or modify Keychain/expiry
values to bypass it. Inspect the state and coordinate a bounded retry with root.
Every invocation uses a new private result path and must report exactly one
executed passing test; preserve failed bundles as well as successful evidence.

## Apple normal timed refresh — September 30, 09:11 UTC

The unchanged Release simulator app issued exactly one new session through its
normal 3,600-second access lifetime and 600-second refresh lead. No clock,
credential expiry or Keychain value was edited. Before/after SQLite inspection
verified the same owner/family, consumed prior refresh and extended access.
The real Apple refresh-validation success counter increased by one.

The opt-in signed-in restart test passed after rotation; the primary inspected
the home screenshot and independently confirmed no extra rotation after restart.
See [sanitized receipt](native-apple-automatic-refresh.json). Private snapshots
and result bundles remain outside the repository. This does not establish Apple
fresh-proof recovery or physical timer behavior.

The new `sign-out` step executed successfully against the real Apple QA session,
returning to both provider controls without starting another provider flow.
Apple recovery steps compile in the dedicated Release test build; full recovery
execution is still pending. The isolated empty owner now has a deliberate pending
deletion established through a separate synthetic app session; its original
receipt was never put in native Keychain. Two coordinated private SQLite backups
and unchanged spending rows were verified. No provider call was made by setup.
Two operator preflight failures (SQLite row comparison and identity constructor
argument order) occurred before deletion began. The corrected setup passed on
private copies before the local QA mutation; all failed artifacts were preserved.

## Apple recovery completion — September 30

The pending check above subsequently completed with real Apple proof and a
successful revocation response. The founder reported the finish-deletion flow
completed and then signed in again. Read-only server inspection verified the
fresh-proof receipt, completed deletion, removed old identity, revoked old
sessions and a distinct empty re-enrolled owner. Spending rows remained unchanged.
The `signed-in-restart` step executed once, passed without skips and produced an
inspected signed-in Home screenshot. See [receipt](apple-fresh-proof-recovery.json).
The transient success screen was not captured; `apple-recovery-complete` was not
executed and must not be reported as passing.

The local QA server stopped during the credential handoff. `--resume` restores
the same localhost endpoint using the original databases, certificate, encryption
key and recorded provider counters. It must refuse missing or invalid retained
state rather than initialize a replacement environment. Keep the process detached
from short-lived tool sessions during manual handoffs, with a private log/PID file;
verify the running command and a TLS challenge before asking for authentication.
Resume does not itself retry provider operations. Counter persistence is based on
the last saved status snapshot, not a crash-proof billing ledger.

Independent review reproduced an empty-database acceptance bug in the first
resume implementation. Read-only integrity/schema/version/foreign-key validation
now runs before mutable initialization. Nine disposable regressions passed under
both worker and primary execution, including byte-preserving refusal, lock
contention and actual localhost TLS listener startup with retained state:

```sh
/tmp/ellis-auth-venv/bin/python -W error::ResourceWarning scripts/qa/test_real_account_server.py -v
```

Those tests substitute provider objects that fail if invoked. The live recovery
above separately exercised the resumed original server, with before/after hashes
confirming preservation of both databases, certificate, key, encryption key and
endpoint before its first challenge. The final schema guard was verified on
disposable state; the running authenticated QA server was not restarted again.
