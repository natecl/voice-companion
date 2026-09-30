"""Disposable-only subprocess CLI rehearsal; emits a sanitized receipt."""
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'Backend'))
from managed_backups import inspect_set, registry


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_cli(clock, *arguments):
    env = dict(os.environ, PYTHONPATH=str(REPO / 'Backend'))
    # Inject only the clock; exercise the actual argument parser and operations.
    code = f'import managed_backups; managed_backups.time.time = lambda: {clock}; managed_backups.main()'
    result = subprocess.run([sys.executable, '-c', code, *arguments], env=env,
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


with tempfile.TemporaryDirectory(prefix='managed-backup-qa-') as temporary:
    directory = Path(temporary).resolve()
    (directory / 'database.lock').touch()
    for name in ('memory.sqlite', 'usage.sqlite', 'historical-spend.sqlite'):
        with closing(sqlite3.connect(directory / name)) as db:
            db.execute('CREATE TABLE evidence(value TEXT)')
            db.execute('INSERT INTO evidence VALUES (?)', ('fictional-' + name,))
            db.commit()
    historical = directory / 'backup-qa-old'
    historical.mkdir(); (historical / 'usage.sqlite').write_bytes(b'unknown ledger')
    originals = {p.name: sha(p) for p in directory.glob('*.sqlite')}
    manifest = run_cli(100, 'snapshot', '--directory', str(directory), '--retention-seconds', '10')
    root, _, data = registry(directory)
    inspected = inspect_set(root, manifest['id'], data['sets'][manifest['id']])
    unknown = root / 'unregistered-old'; unknown.mkdir()
    (unknown / 'keep').write_text('unknown managed-root content')
    early = run_cli(109, 'plan', '--directory', str(directory), '--plan', str(directory / 'early.json'))
    plan_path = directory / 'expiry.json'
    plan = run_cli(110, 'plan', '--directory', str(directory), '--plan', str(plan_path))
    assert (root / manifest['id']).exists()  # Plan is non-destructive.
    applied = run_cli(111, 'apply', '--plan', str(plan_path), '--expected-sha256', plan['plan_sha256'])
    assert not (root / manifest['id']).exists()
    assert originals == {p.name: sha(p) for p in directory.glob('*.sqlite')}
    assert (historical / 'usage.sqlite').read_bytes() == b'unknown ledger'
    assert (unknown / 'keep').read_text() == 'unknown managed-root content'
    assert early['expired_count'] == 0 and applied['expired_count'] == 1
    assert len(registry(directory)[2]['expired']) == 1
    print(json.dumps(dict(status='passed', fixture='disposable fictional SQLite only',
        subprocess_cli_calls=4, snapshot_database_count=len(inspected['databases']),
        injected_created_at=100, injected_expiry_at=110, injected_apply_at=111,
        retention_seconds=10, retention_is_fixture_only=True,
        integrity='ok for every snapshot database', pre_expiry_candidates=0,
        expired_sets_pruned=1, source_ledger_hashes_unchanged=True,
        unknown_historical_and_unregistered_files_preserved=True,
        durable_expiry_receipt=True, production_or_provider_actions=0), indent=2))
