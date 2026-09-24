#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
platform="${1:-mac}"
action="${2:-test}"
case "$action" in build|test) ;; *) echo 'Use build or test' >&2; exit 2;; esac
case "$platform" in
  mac)
    scheme=Mac; destination='platform=macOS'
    if [[ -n "${DEVELOPMENT_TEAM:-}" ]]; then
      signing=("DEVELOPMENT_TEAM=$DEVELOPMENT_TEAM" "CODE_SIGN_IDENTITY=Apple Development" -allowProvisioningUpdates)
    else
      signing=(CODE_SIGN_IDENTITY=-)
    fi ;;

  simulator) scheme=Phone; destination="platform=iOS Simulator,id=${SIMULATOR_ID:?Set SIMULATOR_ID}"; signing=(CODE_SIGNING_ALLOWED=NO) ;;
  device) scheme=Phone; destination="id=${DEVICE_ID:?Set DEVICE_ID}"; signing=("DEVELOPMENT_TEAM=${DEVELOPMENT_TEAM:?Set DEVELOPMENT_TEAM}" -allowProvisioningUpdates) ;;
  *) echo 'Use mac, simulator, or device' >&2; exit 2 ;;
esac
if [[ "$action" == test ]]; then
  if [[ "$platform" == mac ]]; then
    signing+=(-skip-testing:MacUITests/MicrophoneUITests -skip-testing:MacUITests/SavedRecordingUITests)
  else
    signing+=(-skip-testing:PhoneUITests/MicrophoneUITests -skip-testing:PhoneUITests/SavedRecordingUITests)
  fi
fi
xcodegen generate
xcodebuild -project VoiceCompanion.xcodeproj -scheme "$scheme" \
  -destination "$destination" \
  -derivedDataPath "$HOME/Library/Developer/Xcode/DerivedData/VoiceCompanion-$platform" \
  "${signing[@]}" "$action"
