#!/usr/bin/env python3
"""Run one opt-in live account UI step; keep provider screenshots/logs private."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import subprocess
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
DEVICE = '2DABEECA-2BFE-4B62-8B92-DA8972B49D0D'
STEPS = {
    'inspect': 'testInspectCurrentScreen',
    'apple-request': 'testRequestAppleFromSignedOutScreen',
    'sign-out-google': 'testSignOutAndRequestGoogle',
    'google-permission': 'testContinueGooglePermission',
    'google-account': 'testChooseObservedGoogleAccount',
    'google-request': 'testRequestGoogleFromSignedOutScreen',
    'google-pending': 'testContinueReturningGoogleSignIn',
    'google-recovery': 'testRecoverPendingGoogleDeletion',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('step', choices=STEPS)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--derived-data', type=Path, required=True)
    parser.add_argument('--result', type=Path, required=True)
    args = parser.parse_args()
    os.umask(0o077)
    endpoint = (args.directory / 'endpoint.txt').read_text().strip()
    url = urlparse(endpoint)
    if ((url.scheme, url.hostname, url.path) != ('wss', '127.0.0.1', '/account')
            or url.username or url.password or url.query or url.fragment):
        raise ValueError('Only the isolated localhost account service is allowed')
    app = args.derived_data / 'Build/Products/Release-iphonesimulator/VoiceCompanion.app'
    info = plistlib.loads((app / 'Info.plist').read_bytes())
    if info.get('EllisAccountEndpoint') != endpoint or info.get('EllisAccountDeletionEnabled') is not True:
        raise ValueError('Build does not match the localhost deletion QA configuration')
    installed = Path(subprocess.check_output([
        'xcrun', 'simctl', 'get_app_container', DEVICE, 'ai.voicecompanion.phone', 'app'], text=True).strip())
    if plistlib.loads((installed / 'Info.plist').read_bytes()).get('EllisAccountEndpoint') != endpoint:
        raise ValueError('Installed app does not use the isolated QA endpoint')
    devices = json.loads(subprocess.check_output(['xcrun', 'simctl', 'list', 'devices', '--json']))
    selected = [d for group in devices['devices'].values() for d in group if d['udid'] == DEVICE]
    if len(selected) != 1 or selected[0]['name'] != 'Ellis Real Account Lifecycle' or selected[0]['state'] != 'Booted':
        raise ValueError('Dedicated real-account simulator must be booted')
    if args.result.exists() or args.result.with_suffix('.log').exists():
        raise ValueError('Preserve existing results; choose a new result path')
    env = dict(os.environ, TEST_RUNNER_ELLIS_LIVE_ACCOUNT_QA='localhost-recovery')
    if args.step in ('google-account', 'google-recovery'):
        account = env.get('ELLIS_QA_GOOGLE_ACCOUNT')
        if not account:
            raise ValueError('Set ELLIS_QA_GOOGLE_ACCOUNT from the observed account chooser')
        env['TEST_RUNNER_ELLIS_QA_GOOGLE_ACCOUNT'] = account
    with args.result.with_suffix('.log').open('x') as log:
        subprocess.run([
            'xcodebuild', 'test-without-building', '-project', 'VoiceCompanion.xcodeproj',
            '-scheme', 'Phone', '-configuration', 'Release', '-destination',
            'platform=iOS Simulator,id=' + DEVICE, '-derivedDataPath', str(args.derived_data),
            '-only-testing:PhoneUITests/LiveAccountUITests/' + STEPS[args.step],
            '-resultBundlePath', str(args.result),
        ], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    summary = json.loads(subprocess.check_output([
        'xcrun', 'xcresulttool', 'get', 'test-results', 'summary', '--path', str(args.result)]))
    if (summary['totalTestCount'], summary['passedTests'], summary['failedTests'], summary['skippedTests']) != (1, 1, 0, 0):
        raise RuntimeError('Expected one executed passing test; inspect the private result bundle')
    print(json.dumps(dict(step=args.step, executed=1, passed=1, skipped=0)))


if __name__ == '__main__':
    main()
