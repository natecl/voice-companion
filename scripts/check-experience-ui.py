#!/usr/bin/env python3
"""Isolated native UI checks: local service, synthetic capture, no paid provider calls."""
import argparse
import os
from pathlib import Path
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
TESTS = [
    'CompanionPhoneUITests/testCompanionAndCaptureNavigation',
    'CompanionPhoneUITests/testHomeSearchSharedDraftAndTranscriptSheet',
    'RecordingNotesPhoneUITests/testNotesSupportingPassageRelaunchAndDeletion',
]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--simulator', required=True)
    parser.add_argument('--derived-data', default='/tmp/VoiceCompanion-ExperienceQA')
    args = parser.parse_args()
    subprocess.run(['xcodegen', 'generate'], cwd=ROOT, check=True)
    for test in TESTS:
        with tempfile.TemporaryDirectory(prefix='companion-ui-') as directory:
            service = subprocess.Popen([os.sys.executable, str(ROOT / 'Backend/companion_fixture.py'), directory, '--ui', '--notes'], cwd=ROOT)
            try:
                config = Path(directory) / 'config.json'
                deadline = time.monotonic() + 10
                while not config.exists():
                    if service.poll() is not None or time.monotonic() > deadline:
                        raise RuntimeError('Local fixture did not become ready')
                    time.sleep(0.1)
                env = os.environ.copy()
                env['TEST_RUNNER_VOICE_MEMORY_UI_CONFIG'] = config.read_text()
                print(f'Running {test} with a fresh local owner', flush=True)
                subprocess.run(['xcodebuild', '-scheme', 'Phone', '-destination', f'platform=iOS Simulator,id={args.simulator}', '-derivedDataPath', args.derived_data, 'test', f'-only-testing:PhoneUITests/{test}', 'CODE_SIGNING_ALLOWED=NO'], cwd=ROOT, env=env, check=True)
            finally:
                service.terminate()
                service.wait(timeout=10)

if __name__ == '__main__':
    main()
