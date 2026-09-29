#!/usr/bin/env python3
"""Run a product feature's checks and collect its required behavioral evidence."""
import argparse
import json
from pathlib import Path
import re
import sys
import uuid

import verify_checkpoint as checkpoint

ROOT = checkpoint.ROOT


def catalog(root=ROOT):
    features = json.loads((root / 'docs/features/catalog.json').read_text())
    for key, feature in features.items():
        if not re.fullmatch(r'[a-z][a-z0-9-]*', key):
            raise ValueError('Invalid feature ID')
        for module in feature['test_modules']:
            if not re.fullmatch(r'Backend\.test_[a-z0-9_]+', module):
                raise ValueError('Only reviewed test modules are allowed')
            if not (root / (module.replace('.', '/') + '.py')).is_file():
                raise ValueError('Missing test module')
        if feature['test_modules']:
            checkpoint.REGISTRY['feature:' + key] = [sys.executable, '-m', 'unittest', *feature['test_modules']]
    return features


def verify(feature_id, checks_only=False, root=ROOT):
    features = catalog(root)
    if feature_id not in features:
        raise ValueError('Unknown feature; use --list')
    feature = features[feature_id]
    path = checkpoint.local_path(root, feature['manifest'])
    manifest = json.loads(path.read_text())
    if checks_only:
        checks = [c for c in manifest['checks'] if c['group'] == 'mechanical_checks']
        if not checks:
            raise ValueError('No automated verifier implemented for this feature yet')
        manifest.update(packet='CONTRACTS-' + feature_id, checks=checks,
                        acceptance=['Automated contracts only; full feature remains unverified'],
                        not_applicable={group: 'Checks-only run; full feature evidence still required'
                                        for group in ('live_behavior_checks', 'inspection')})
        folder = root / 'work/verification'; folder.mkdir(parents=True, exist_ok=True)
        path = folder / (uuid.uuid4().hex + '-manifest.json')
        path.write_text(json.dumps(manifest, indent=2) + '\n')
    receipt = checkpoint.run(root, path)
    receipt.update(feature=feature_id, feature_status=feature['status'],
                   verification_scope='mechanical_only' if checks_only else 'full_feature',
                   feature_verified=False)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('feature', nargs='?')
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--checks-only', action='store_true')
    args = parser.parse_args()
    try:
        if args.list:
            for key, feature in catalog().items():
                print(f"{key}: {feature['name']} — {feature['status']}")
            return 0
        if not args.feature:
            parser.error('Choose a feature or --list')
        receipt = verify(args.feature, args.checks_only)
        folder = ROOT / 'work/verification'; folder.mkdir(parents=True, exist_ok=True)
        output = folder / (uuid.uuid4().hex + '.json')
        output.write_text(json.dumps(receipt, indent=2) + '\n'); output.chmod(0o600)
        print(json.dumps(dict(receipt=str(output), feature=args.feature, scope=receipt['verification_scope'],
                              status=receipt['status'], feature_verified=False, unresolved=receipt['unresolved'])))
        return 1 if receipt['unresolved'] else 0
    except (ValueError, OSError, KeyError, checkpoint.subprocess.CalledProcessError) as error:
        print('Feature verification blocked: ' + str(error), file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
