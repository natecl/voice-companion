# CACHE-1 local persistence checkpoint

September 29, 2026; base `47eadb4c8be3a46593bb6f17250f4c24335ea02c`. Candidate only: not merged, deployed or installed on a physical phone. Full feature acceptance remains incomplete: real logout, owner-transition clearing and explicit reset entry points do not exist yet. `clear(owner:)` and `clearAll()` mechanics are tested, not wired account behavior.

## Behavior and inspected evidence

The actual Debug iPhone app fetched a fictional summary through the existing authenticated local NotesService, persisted it, terminated, and reopened it with the server stopped. The summary remained readable after the refresh failed, with saved-content status and Refresh notes. A delayed local response replaced it without blanking the content; authoritative `outdated` removed summary content and reset its derived title. A second fixture owner opened an empty library. No microphone, real model, production account or paid provider was used. Offline means stopped loopback server, not a physical airplane-mode check.

- [Online](online.png), [offline after process relaunch and failed refresh](offline.png).
- [Before delayed update](before-update.png), [after update](update.png).
- [Outdated content and title removed](outdated.png), [other owner](other-owner.png), [before deletion](before-delete.png), [settled deleted-source state](after-delete.png). Local disk inspection found the deleted source cache directory absent; a different recording remained cached.
- Unit tests exercise disk reopen, server generation replacement, source revision high-water rejection, owner isolation, failed/pending refresh preservation, coalescing, explicit retry behind concurrent read, both controller deletion methods, and invalidation racing late responses.
- Cache identity stores owner, recording, revision and server generation version together. Local schema version is independent. Only ready results persist. Offline content is the last successful server result, not proof of latest server generation.
- Invalidating one recording removes its entries and cancels its flights. An in-flight identifier check rejects late writes. New known transcript revisions purge old entries; old revision reads cannot restore them. Read/foreground revalidation uses the read operation only; explicit Retry notes retains the existing generation operation.

## Environment and commands

Xcode 27.0 (27A266a), macOS 26.6.2, XcodeGen 2.46.0. Isolated simulator `F4EFCAA1-44CE-41AB-ABA0-3BBDC4589A76`, iPhone 17, iOS 26.5 (23F77). DerivedData: `/tmp/note-cache-derived` (CoreTests) and `/tmp/note-cache-phone-derived` (phone). New environments should create their own simulator ID.

```sh
xcodegen generate
xcodebuild -project VoiceCompanion.xcodeproj -scheme Mac -destination 'platform=macOS' -derivedDataPath /tmp/note-cache-derived -only-testing:CoreTests/RecordingNotesCacheTests test CODE_SIGNING_ALLOWED=NO
```

Phone QA uses an intentionally staged test; ordinary suite runs skip these external-fixture scenarios. Use a fresh `/tmp/voice-note-cache-qa` (move any previous QA directory aside), then run the local fixture in a separate terminal:

```sh
python3 scripts/note_cache_fixture.py populate --stage testPopulateCache
```

Run each selected stage with:

```sh
xcodebuild -project VoiceCompanion.xcodeproj -scheme Phone -destination 'platform=iOS Simulator,id=YOUR_ISOLATED_SIMULATOR_ID' -derivedDataPath /tmp/note-cache-phone-derived -only-testing:PhoneUITests/RecordingNotesCacheUITests/TEST_METHOD test CODE_SIGNING_ALLOWED=NO
```

1. Run `testPopulateCache`. Stop the populate fixture process.
2. `python3 scripts/note_cache_fixture.py stage --stage testReopenSavedCache`; run that test with the server stopped. This proves disk/process relaunch and failed-refresh preservation.
3. `python3 scripts/note_cache_fixture.py update --stage testBackgroundUpdate`; start `python3 scripts/note_cache_fixture.py read` in another terminal. Run `testBackgroundUpdate`. The read server reuses the same local credential/owner/port and delays notes by two seconds; it does not run a generation worker.
4. `python3 scripts/note_cache_fixture.py outdated --stage testOutdatedSource`; run that test. Inspect that content and generated title are no longer shown as current.
5. `python3 scripts/note_cache_fixture.py stage --stage testOwnerIsolation`; run that test. It changes only the in-memory fixture configuration to a new owner and checks that no previous recording/content appears; this does not implement sign-out.
6. `python3 scripts/note_cache_fixture.py ready --stage testDeleteCachedRecording`; run that test. Inspect the source-specific cache directory in the app data container before/after deletion, then stop the read server and shut down the isolated simulator.

The helper binds only loopback and uses fixed fictional outputs. Its configuration contains a disposable local credential: do not commit it. Extract retained test screenshots using `xcrun xcresulttool export attachments --path RESULT.xcresult --output-path OUTPUT`.

## Limits and failed attempts

Initial test compilation used an unnecessary app-module import and actor-unsafe test captures; both were fixed before the passing CoreTests runs. First phone test omitted `--enable-companion-ui` and opened the legacy shell; corrected fixture launch passed. The initial deletion selector matched multiple accessibility nodes; narrowed it to the first matching confirmation control. No app layout/style changes were made to accommodate tests.

The first online/update/owner screenshots precede the explicit-retry coalescing regression fix; that change affects only an explicit retry while a read is in flight and is covered by its dedicated test. Final phone build/deletion QA compiles the final production implementation. Account lifecycle acceptance, physical protected-storage behavior while locked, and provider quality remain unverified. Primary must review and accept this bounded checkpoint; do not mark the full note-cache feature verified until remaining access integration is exercised.
