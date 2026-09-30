#!/usr/bin/env python3
"""Offline checkpoint receipts. Runs only reviewed checks; never self-approves."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = {
    'verifier-self-tests': [sys.executable, '-m', 'unittest', 'discover', '-s', 'scripts/verification', '-p', 'test_*.py'],
    'proactive-controls': [sys.executable, '-m', 'unittest', 'Backend.test_proactive_policy', 'Backend.test_proactive_stream', 'Backend.test_proactive_socket', 'Backend.test_admission'],
}
GROUPS = {'mechanical_checks', 'live_behavior_checks', 'inspection'}
KINDS = {'fixture', 'live_provider', 'live_identity_provider', 'simulator', 'physical_device', 'review'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def local_path(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Evidence path must stay inside the checkout')
    return path


def identity(root):
    def git(*args):
        return subprocess.check_output(['git', *args], cwd=root, text=True).strip()
    if git('status', '--porcelain'):
        raise ValueError('Commit the work first: evidence requires a clean checkout')
    return git('rev-parse', 'HEAD')


def artifact(root, name):
    path = local_path(root, name)
    if not path.is_file():
        raise ValueError('Required evidence file is missing')
    return {'path': str(path.relative_to(root.resolve())), 'sha256': digest(path)}


def validate(manifest):
    if not isinstance(manifest, dict):
        raise ValueError('Manifest must be an object')
    if not all(manifest.get(key) for key in ('packet', 'base', 'acceptance')):
        raise ValueError('Packet, base and acceptance criteria are required')
    checks = manifest.get('checks', [])
    if not isinstance(checks, list) or any(not isinstance(check, dict) for check in checks):
        raise ValueError('Checks must be objects')
    ids = [check.get('id') for check in checks]
    if not checks or any(not x for x in ids) or len(set(ids)) != len(ids):
        raise ValueError('Checks need unique IDs')
    covered = set()
    for check in checks:
        if check.get('group') not in GROUPS or check.get('kind') not in KINDS:
            raise ValueError('Invalid evidence category')
        if check['kind'] == 'live_identity_provider' and (
                check['group'] != 'live_behavior_checks' or check.get('provider') not in ('google', 'apple')):
            raise ValueError('Identity-provider evidence requires its actual provider and live category')
        covered.add(check['group'])
        if ('runner' in check) == ('evidence' in check):
            raise ValueError('Each check needs one runner or external evidence receipt')
        if 'runner' in check:
            if check['runner'] not in REGISTRY or check['kind'] != 'fixture' or check['group'] != 'mechanical_checks':
                raise ValueError('Only allowlisted offline mechanical checks can execute')
    exemptions = manifest.get('not_applicable', {})
    if set(exemptions) - GROUPS or set(exemptions) & covered:
        raise ValueError('Invalid or conflicting category exemption')
    if any(not isinstance(reason, str) or not reason.strip() for reason in exemptions.values()):
        raise ValueError('Not-applicable categories require reasons')
    if covered | set(exemptions) != GROUPS:
        raise ValueError('Declare every verification category; do not silently skip checks')


def execute(root, command):
    # Keep API keys/tokens out of children and omit raw output entirely: it may
    # contain credentials or private text. This is not a network sandbox.
    environment = {k: os.environ[k] for k in ('PATH', 'SYSTEMROOT', 'TMPDIR') if k in os.environ}
    environment.update(PYTHONPATH=str(root / 'Backend'), PYTHONDONTWRITEBYTECODE='1')
    started = time.monotonic()
    try:
        result = subprocess.run(command, cwd=root, env=environment, stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL, timeout=120)
        return result.returncode, round(time.monotonic() - started, 3)
    except subprocess.TimeoutExpired:
        return 124, round(time.monotonic() - started, 3)


def run(root, manifest_path):
    manifest = json.loads(manifest_path.read_text())
    validate(manifest)
    commit = identity(root)
    subprocess.check_call(['git', 'merge-base', '--is-ancestor', manifest['base'], commit], cwd=root,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    receipt = dict(packet=manifest['packet'], commit=commit, base=manifest['base'],
                   manifest=artifact(root, str(manifest_path.resolve().relative_to(root.resolve()))),
                   environment=platform.platform(), acceptance=manifest['acceptance'],
                   not_applicable=manifest.get('not_applicable', {}), checks=[],
                   paid_calls=0, reserved_microusd=0, unresolved=[],
                   review=dict(status='pending', reviewed_commit=None, released_packets=[]))
    for check in manifest['checks']:
        result = dict(id=check['id'], group=check['group'], evidence_kind=check['kind'], result='not_run', artifacts=[])
        try:
            if 'runner' in check:
                command = REGISTRY[check['runner']]
                code, duration = execute(root, command)
                result.update(command=command, exit_code=code, seconds=duration, result='pass' if code == 0 else 'fail')
            else:
                evidence_path = local_path(root, check['evidence'])
                result['artifacts'].append(artifact(root, check['evidence']))
                evidence = json.loads(evidence_path.read_text())
                if not isinstance(evidence, dict):
                    raise ValueError('External evidence must be an object')
                if evidence.get('commit') != commit or evidence.get('kind') != check['kind']:
                    raise ValueError('Evidence commit or provenance does not match')
                if evidence.get('result') not in ('pass', 'fail') or not evidence.get('artifacts'):
                    raise ValueError('External evidence needs a result and underlying artifacts')
                if not isinstance(evidence.get('artifacts'), list) or any(not isinstance(name, str) for name in evidence['artifacts']):
                    raise ValueError('Evidence artifacts must be file paths')
                if not evidence.get('procedure') or not evidence.get('observed'):
                    raise ValueError('External evidence needs reproduction and observed results')
                if check['kind'] == 'live_identity_provider':
                    if evidence.get('provider') != check['provider']:
                        raise ValueError('Identity-provider evidence does not match the required provider')
                    if not all(isinstance(evidence.get(key), str) and evidence[key].strip()
                               for key in ('configuration', 'pipeline_layer')):
                        raise ValueError('Identity-provider evidence needs final configuration and pipeline identity')
                    if type(evidence.get('provider_calls')) is not int or evidence['provider_calls'] <= 0:
                        raise ValueError('Identity-provider evidence needs actual provider-call accounting')
                    # OAuth proof has no model identity; never invent one or
                    # count a synthetic token fixture as provider authorization.
                    result['provider'] = evidence['provider']
                    result['provider_calls'] = evidence['provider_calls']
                if check['kind'] == 'live_provider':
                    if not all(evidence.get(k) for k in ('request_sha256', 'model', 'ledger', 'pipeline_layer')):
                        raise ValueError('Live evidence needs request/model/ledger/pipeline identity')
                    for key in ('paid_calls', 'reserved_microusd'):
                        if type(evidence.get(key)) is not int or evidence[key] < 0:
                            raise ValueError('Invalid external spending receipt')
                        receipt[key] += evidence[key]
                for name in evidence['artifacts']:
                    result['artifacts'].append(artifact(root, name))
                result['result'] = evidence['result']
            if result['result'] != 'pass':
                receipt['unresolved'].append(check['id'])
        except (OSError, ValueError, KeyError):
            result.update(result='not_run', reason='Missing, invalid, or stale evidence; inspect the declared receipt')
            receipt['unresolved'].append(check['id'])
        receipt['checks'].append(result)
    if identity(root) != commit:
        raise ValueError('Source changed during verification')
    receipt['status'] = 'needs_review' if not receipt['unresolved'] else 'incomplete'
    return receipt


def review(root, receipt, reviewer, decision, notes, released):
    if receipt.get('verification_scope') == 'mechanical_only' and released:
        raise ValueError('Mechanical checks cannot release dependents; collect full feature evidence')
    if identity(root) != receipt['commit']:
        raise ValueError('Receipt is stale for this checkout')
    for item in [receipt['manifest']] + [a for c in receipt['checks'] for a in c['artifacts']]:
        if artifact(root, item['path']) != item:
            raise ValueError('Evidence changed since verification')
    if not reviewer.strip() or not notes.strip():
        raise ValueError('Reviewer and inspection notes required')
    if decision == 'accepted_for_integration' and (receipt['unresolved'] or any(c['result'] != 'pass' for c in receipt['checks'])):
        raise ValueError('Required checks have not passed')
    if released and decision != 'accepted_for_integration':
        raise ValueError('Only accepted evidence can release dependent packets')
    receipt['status'] = decision
    if receipt.get('verification_scope') == 'full_feature':
        receipt['feature_verified'] = decision == 'accepted_for_integration'
    receipt['review'] = dict(status=decision, reviewer=reviewer, notes=notes,
                             reviewed_commit=receipt['commit'], released_packets=released)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet')
    parser.add_argument('--review-receipt')
    parser.add_argument('--reviewer', default='')
    parser.add_argument('--decision', choices=['accepted_for_integration', 'changes_required', 'blocked'])
    parser.add_argument('--notes', default='')
    parser.add_argument('--release', action='append', default=[])
    args = parser.parse_args()
    if bool(args.packet) == bool(args.review_receipt):
        parser.error('Choose a packet run or receipt review')
    try:
        if args.packet:
            receipt = run(ROOT, local_path(ROOT, args.packet))
        else:
            if not args.decision: parser.error('Review requires a decision')
            receipt = review(ROOT, json.loads(local_path(ROOT, args.review_receipt).read_text()),
                             args.reviewer, args.decision, args.notes, args.release)
        folder = ROOT / 'work/verification'; folder.mkdir(parents=True, exist_ok=True)
        output = folder / (uuid.uuid4().hex + '.json')
        output.write_text(json.dumps(receipt, indent=2) + '\n'); output.chmod(0o600)
        print(json.dumps(dict(receipt=str(output), status=receipt['status'], review=receipt['review']['status'])))
        return 1 if receipt['unresolved'] else 0
    except (ValueError, OSError, subprocess.CalledProcessError):
        print('Verification blocked: check manifest, clean commit, base and evidence identities.', file=sys.stderr)
        return 2

if __name__ == '__main__':
    sys.exit(main())
