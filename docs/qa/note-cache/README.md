# CACHE-1 local persistence checkpoint

September 29, 2026; base `47eadb4c8be3a46593bb6f17250f4c24335ea02c`. Candidate only: not merged, deployed or installed on a physical phone. Full feature acceptance remains incomplete: real logout, owner-transition clearing and explicit reset entry points do not exist yet. `clear(owner:)` and `clearAll()` mechanics are tested, not wired account behavior.

## Behavior and inspected evidence

The actual Debug iPhone app fetched a fictional summary through the existing authenticated local NotesService, persisted it, terminated, and reopened it with the server stopped. The summary remained readable after the refresh failed, with saved-content status and Refresh notes. A gated local response replaced it without blanking the content: the test asserts and screenshots the old text before releasing the response, then asserts and screenshots the replacement. Actual source revision/deletion operations produce `stale_notes` and `source_unavailable` errors through NotesService; both remove summary content and reset its derived title. A second fixture owner opened an empty library. No microphone, real model, production account or paid provider was used. Offline means stopped loopback server, not a physical airplane-mode check.

- [Online](online.png), [offline after process relaunch and failed refresh](offline.png).
- [Before delayed update](before-update.png), [after update](update.png).
- [Actual stale-revision response](outdated.png), [actual remote deletion](remote-delete.png), with sanitized [stale service messages](stale-service-responses.jsonl) and [deletion service message](deleted-service-responses.jsonl).
- [Final disk inspection](invalidated-disk.json) found zero summary JSON files for both invalidated fixtures. Revision/invalidation markers remain so a later stale view cannot resurrect content. A remote-deleted fixture also reopened without its old notes/title after stopping the server.
- [Other owner](other-owner.png), [before local deletion](before-delete.png), [settled local deletion](after-delete.png) retain the initial candidate's bounded UI evidence. Final local-deletion changes are freshly exercised through both actual controller/store/outbox paths with a simulated cache-cleanup error; those initial screenshots are not evidence of error handling.
- Eleven unit tests exercise disk reopen, server generation replacement, source revision high-water rejection, owner isolation, failed/pending refresh preservation, coalescing, explicit retry behind concurrent read, both controller deletion methods (including failed cache cleanup with selection/library/sync completion), typed service errors versus transport failures, revision-marker preservation after outdated responses, and invalidation racing late responses.
- Cache identity stores owner, recording, revision and server generation version together. Local schema version is independent. Only ready results persist. Offline content is the last successful server result, not proof of latest server generation.
- Invalidating one recording removes its summary JSON and cancels its flights, retaining a content-free deletion marker. An in-flight identifier check rejects late writes. New known transcript revisions purge old entries; old revision reads cannot restore them. Read/foreground revalidation uses the read operation only; explicit Retry notes retains the existing generation operation.

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
3. `python3 scripts/note_cache_fixture.py update --stage testBackgroundUpdate`; start `python3 scripts/note_cache_fixture.py read` in another terminal. Run `testBackgroundUpdate`. The read server reuses the same local credential/owner/port and gates notes until the test asserts/screenshots the old text and creates `release-update`; it does not run a generation worker.
4. `python3 scripts/note_cache_fixture.py source-revision --stage testOutdatedSource`; run that test. This calls `MemoryStore.put_source` with a higher revision; inspect the real `stale_notes` response in `notes-responses.jsonl` and verify content/title are removed. The old `outdated` helper only changes a notes row and is insufficient evidence for this contract.
5. `python3 scripts/note_cache_fixture.py stage --stage testOwnerIsolation`; run that test. It changes only the in-memory fixture configuration to a new owner and checks that no previous recording/content appears; this does not implement sign-out.
6. Stop the read server and move the fixture directory aside. Run a new `populate --stage testPopulateCache` and its test to create a new independently cached recording/owner. Stop populate, run `python3 scripts/note_cache_fixture.py source-delete --stage testRemoteDeletedSource`, start `read`, and run that test. It calls `MemoryStore.delete_source`, then the real NotesService sends `source_unavailable`. Stop read and repeat the test to verify process relaunch without network cannot restore deleted notes.
7. Local deletion UI testing, if needed, uses another fresh populate fixture, followed by `stage --stage testDeleteCachedRecording` and its test. Inspect that source's summary JSON is gone while content-free deletion/revision metadata remains. Stop the fixture server and shut down the isolated simulator.

The helper binds only loopback and uses fixed fictional outputs. Its configuration contains a disposable local credential: do not commit it. Extract retained test screenshots using `xcrun xcresulttool export attachments --path RESULT.xcresult --output-path OUTPUT`.

## Limits and failed attempts

Initial test compilation used an unnecessary app-module import and actor-unsafe test captures; both were fixed before the passing CoreTests runs. First phone test omitted `--enable-companion-ui` and opened the legacy shell; corrected fixture launch passed. The initial deletion selector matched multiple accessibility nodes; narrowed it to the first matching confirmation control. No app layout/style changes were made to accommodate tests.

Primary review rejected the initial source-invalidation proof: NotesService sends typed error envelopes for deleted/stale sources, while the candidate treated them as transport errors and retained notes. It also found that content invalidation deleted the revision marker, allowing old revisions to return later, and that the initial before/after update screenshots both showed new text. Those initial claims at `f187446` are superseded, not counted as passing evidence. The repair adds typed authoritative errors, durable invalidation/deletion metadata, the exact high-water regression, and a response gate with explicit old/new assertions. The local deletion cleanup error previously prevented selection/library/outbox completion; the final regression exercises successful source deletion plus failed cache cleanup and verifies the deletion reaches the sync transport while showing an honest cleanup error.

Final source error, transport preservation, update and disk evidence use the repaired implementation. Account lifecycle acceptance, physical protected-storage behavior while locked, and provider quality remain unverified. A disk cleanup failure is surfaced and does not claim successful erasure. Primary must review and accept this bounded checkpoint; do not mark the full note-cache feature verified until remaining access integration is exercised.
