#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${SIMULATOR_ID:?Set SIMULATOR_ID for local simulator QA}"
python="${VOICE_TEST_PYTHON:-python3}"
mkdir -p work
receipt=$(mktemp -d work/notes-phone-XXXXXX)
# A fresh owner isolates saved app state; never reuse a failed run's enrollment.
"$python" Backend/companion_fixture.py "$receipt" --ui --notes > "$receipt/service.log" 2>&1 &
fixture_pid=$!
trap 'kill "$fixture_pid" 2>/dev/null || true; wait "$fixture_pid" 2>/dev/null || true' EXIT
for ((i=0;i<50;i++)); do
  [[ -f "$receipt/config.json" ]] && break
  kill -0 "$fixture_pid"
  sleep .1
done
[[ -f "$receipt/config.json" ]]
xcodegen generate
export TEST_RUNNER_VOICE_MEMORY_UI_CONFIG="$(cat "$receipt/config.json")"
xcodebuild -project VoiceCompanion.xcodeproj -scheme Phone \
  -destination "platform=iOS Simulator,id=$SIMULATOR_ID" \
  -derivedDataPath "$HOME/Library/Developer/Xcode/DerivedData/VoiceCompanion-simulator" \
  CODE_SIGNING_ALLOWED=NO -only-testing:PhoneUITests/RecordingNotesPhoneUITests \
  -resultBundlePath "$receipt/native.xcresult" test > "$receipt/native.log" 2>&1
printf 'Notes simulator QA passed: %s\n' "$receipt"
