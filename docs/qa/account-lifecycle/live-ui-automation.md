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

Available steps: `inspect`, `apple-request`, `signed-in-restart`, `sign-out-google`, `google-permission`,
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
The private pre-refresh snapshot is preserved; automatic rotation remains pending
the normal 600-second lead before 3600-second access expiry. No clocks, expiry
values or Keychain credentials were modified.
