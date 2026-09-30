"""Managed SQLite sets. No retention default or legacy adoption.

Only runtimes honoring database.lock are excluded. Verify maintenance/version
before live use. Hashes detect accidental modification, not a malicious operator
who can rewrite both registry and files. Failed partial pruning needs inspection.
"""
import argparse
from contextlib import contextmanager, ExitStack, closing
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import time
import uuid
from maintenance import database_lease

MAX_TIMESTAMP = 253402300799  # Last whole UTC second representable in year 9999.
ROOT = 'managed-backups'
REGISTRY = 'registry.json'


class RegistryBusy(BlockingIOError):
    """No managed-file mutation was attempted; another operation owns the lease."""


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def checked_path(path, directory=False):
    path = Path(path).absolute()
    for component in (*reversed(path.parents), path):
        if component.is_symlink():
            raise ValueError('Symlink paths are forbidden')
    info = path.stat()
    if not (stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)):
        raise ValueError('Expected regular file or directory')
    if not directory and info.st_nlink != 1:
        raise ValueError('Hard-linked files are forbidden')
    return path


def private(path, directory=False):
    path = checked_path(path, directory)
    if path.stat().st_mode & 0o077:
        raise ValueError('Managed artifacts must be private')
    return path


def timestamp(value):
    if type(value) is not int or not 0 <= value <= MAX_TIMESTAMP:
        raise ValueError('Invalid bounded timestamp')
    return value


def now(clock):
    return timestamp(clock() if clock else int(time.time()))


def write_json(path, value, replace=False):
    # Atomic registry replacement; no overwrite for manifests/plans.
    temporary = path.with_name('.write-' + uuid.uuid4().hex) if replace else path
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as out:
        json.dump(value, out, sort_keys=True, indent=2)
        out.write('\n'); out.flush(); os.fsync(out.fileno())
    if replace:
        os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@contextmanager
def lease(directory):
    directory = checked_path(directory, True)
    checked_path(directory / 'database.lock')  # Never create a missing runtime lease.
    with database_lease(directory):
        yield directory


@contextmanager
def registry_lease(directory):
    """Serialize managed files only; never open or lease active databases.

    Operations requiring both leases always take database.lock first. Pruning
    does not need the runtime lease and can run while the service holds it.
    """
    directory = checked_path(directory, True)
    path = directory / 'managed-backups.lock'
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, 'a') as lock:
        private(path)
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RegistryBusy('Managed registry is busy') from error
        yield directory


@contextmanager
def snapshot_read_lease(snapshot_path):
    """Keep a managed snapshot alive during an offline restore inspection."""
    path = checked_path(snapshot_path)
    if path.parent.parent.name == ROOT:
        with registry_lease(path.parent.parent.parent):
            yield
    else:
        yield


def registry(directory, create=False):
    root = directory / ROOT
    if not root.exists() and create:
        root.mkdir(mode=0o700)
        write_json(root / REGISTRY, {'version': 1, 'sets': {}, 'expired': []})
    private(root, True)
    if (root / 'prune-pending.json').exists():
        raise ValueError('Interrupted prune requires operator reconciliation of prune-pending.json')
    path = private(root / REGISTRY)
    data = json.loads(path.read_text())
    if set(data) != {'version', 'sets', 'expired'} or data['version'] != 1 or not isinstance(data['sets'], dict) or not isinstance(data['expired'], list):
        raise ValueError('Invalid managed registry')
    for identifier, expected in data['sets'].items():
        if not re.fullmatch(r'[0-9a-f]{32}', identifier) or not isinstance(expected, str) or not re.fullmatch(r'[0-9a-f]{64}', expected):
            raise ValueError('Invalid registered snapshot')
    return root, path, data


def inspect_set(root, identifier, expected):
    folder = private(root / identifier, True)
    manifest_path = private(folder / 'manifest.json')
    if digest(manifest_path) != expected:
        raise ValueError('Manifest hash changed')
    manifest = json.loads(manifest_path.read_text())
    if set(manifest) != {'version', 'id', 'created_at', 'expires_at', 'retention_seconds', 'databases'} or manifest['version'] != 1 or manifest['id'] != identifier:
        raise ValueError('Invalid manifest')
    created, expires = timestamp(manifest['created_at']), timestamp(manifest['expires_at'])
    duration = manifest['retention_seconds']
    if type(duration) is not int or duration <= 0 or expires - created != duration:
        raise ValueError('Invalid retention duration')
    databases = manifest['databases']
    if not isinstance(databases, dict) or not {'memory.sqlite', 'usage.sqlite'} <= set(databases):
        raise ValueError('Incomplete snapshot')
    if {p.name for p in folder.iterdir()} != set(databases) | {'manifest.json'}:
        raise ValueError('Unexpected snapshot contents')
    for name, expected_hash in databases.items():
        if not re.fullmatch(r'[A-Za-z0-9_.-]+\.sqlite', name) or name.startswith('.'):
            raise ValueError('Invalid database name')
        path = private(folder / name)
        if digest(path) != expected_hash:
            raise ValueError('Snapshot database changed')
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
            if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise ValueError('Snapshot integrity check failed')
    return manifest


def snapshot(directory, retention_seconds, clock=None):
    created = now(clock)
    if type(retention_seconds) is not int or retention_seconds <= 0 or retention_seconds > MAX_TIMESTAMP - created:
        raise ValueError('Explicit positive bounded retention seconds required')
    with lease(directory) as directory, registry_lease(directory):
        paths = sorted(directory.glob('*.sqlite'))
        if not {'memory.sqlite', 'usage.sqlite'} <= {p.name for p in paths}:
            raise ValueError('Required databases missing')
        for path in paths:
            checked_path(path)
            if not re.fullmatch(r'[A-Za-z0-9_.-]+\.sqlite', path.name) or path.name.startswith('.'):
                raise ValueError('Invalid database name')
        root, registry_path, data = registry(directory, create=True)
        identifier = uuid.uuid4().hex
        folder = root / identifier
        folder.mkdir(mode=0o700)
        with ExitStack() as stack:
            for path in paths:
                db = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True, isolation_level=None, timeout=2)
                stack.callback(db.close)
                if db.execute('PRAGMA journal_mode').fetchone()[0] != 'delete':
                    raise ValueError('Coordinated snapshots require rollback journals')
                db.execute('BEGIN IMMEDIATE')
            for path in paths:
                target_path = folder / path.name
                fd = os.open(target_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(fd)
                with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as source, closing(sqlite3.connect(target_path)) as target:
                    source.backup(target)
        manifest = dict(version=1, id=identifier, created_at=created,
                        expires_at=created + retention_seconds, retention_seconds=retention_seconds,
                        databases={p.name: digest(folder / p.name) for p in paths})
        write_json(folder / 'manifest.json', manifest)
        manifest_hash = digest(folder / 'manifest.json')
        inspect_set(root, identifier, manifest_hash)
        data['sets'][identifier] = manifest_hash
        write_json(registry_path, data, replace=True)
        return manifest


def _plan_locked(directory, planned_at):
    root, registry_path, data = registry(directory)
    expired = {}
    next_expiry = None
    for identifier, expected in data['sets'].items():
        manifest = inspect_set(root, identifier, expected)
        expires = manifest['expires_at']
        if expires <= planned_at:
            expired[identifier] = expected
        elif next_expiry is None or expires < next_expiry:
            next_expiry = expires
    return (dict(version=1, directory=str(directory), planned_at=planned_at,
                 registry_sha256=digest(registry_path), expired=expired), next_expiry)


def plan_prune(directory, plan_path, clock=None):
    planned_at = now(clock)
    plan_path = Path(plan_path).absolute()
    checked_path(plan_path.parent, True)
    with registry_lease(directory) as directory:
        root = directory / ROOT
        if (plan_path in (directory / 'database.lock', directory / 'managed-backups.lock')
                or plan_path.suffix == '.sqlite' or root == plan_path or root in plan_path.parents):
            raise ValueError('Plan destination overlaps protected paths')
        plan, _ = _plan_locked(directory, planned_at)
        write_json(plan_path, plan)
        return dict(plan_sha256=digest(plan_path), expired_count=len(plan['expired']))


def _apply_locked(directory, plan, expected_sha256, applied_at):
    if set(plan) != {'version', 'directory', 'planned_at', 'registry_sha256', 'expired'} or plan['version'] != 1:
        raise ValueError('Invalid prune plan')
    if str(directory) != plan['directory'] or applied_at < timestamp(plan['planned_at']):
        raise ValueError('Clock moved before inspected plan or directory changed')
    root, registry_path, data = registry(directory)
    if digest(registry_path) != plan['registry_sha256']:
        raise ValueError('Registry changed since plan')
    manifests = {}
    for identifier, expected in data['sets'].items():
        manifest = inspect_set(root, identifier, expected)
        if manifest['expires_at'] <= plan['planned_at']:
            manifests[identifier] = manifest
    if plan['expired'] != {key: data['sets'][key] for key in manifests}:
        raise ValueError('Prune plan does not match registered expiry')
    pending = root / 'prune-pending.json'
    write_json(pending, dict(plan=plan, plan_sha256=expected_sha256, manifests=manifests))
    # Validate the entire set before deleting any file. Never recurse.
    for identifier, manifest in manifests.items():
        folder = root / identifier
        for name in manifest['databases']:
            (folder / name).unlink()
        (folder / 'manifest.json').unlink()
        folder.rmdir()
        data['expired'].append(dict(id=identifier, manifest_sha256=data['sets'].pop(identifier),
                                    expired_at=manifest['expires_at'], pruned_at=applied_at,
                                    plan_sha256=expected_sha256))
    write_json(registry_path, data, replace=True)
    pending.unlink()
    return dict(status='pruned', expired_count=len(manifests))


def apply_prune(plan_path, expected_sha256, clock=None):
    path = private(plan_path)
    if digest(path) != expected_sha256:
        raise ValueError('Plan approval hash mismatch')
    plan = json.loads(path.read_text())
    with registry_lease(plan['directory']) as directory:
        return _apply_locked(directory, plan, expected_sha256, now(clock))


def expire_registered(directory, clock=None):
    """One authorized automatic scan, with an inspectable exact-hash plan.

    No active database opens, snapshot creation, or historical adoption. Errors
    propagate to the worker, which stops instead of retrying failed pruning.
    """
    with registry_lease(directory) as directory:
        root = directory / ROOT
        if not root.exists() and not root.is_symlink():
            return dict(expired_count=0, next_expiry=None)
        planned_at = now(clock)
        plan, next_expiry = _plan_locked(directory, planned_at)
        if plan['expired']:
            path = root / ('automatic-prune-plan-' + uuid.uuid4().hex + '.json')
            write_json(path, plan)
            expected = digest(path)
            pinned = json.loads(path.read_text())
            if digest(path) != expected or pinned != plan:
                raise ValueError('Automatic plan changed')
            _apply_locked(directory, pinned, expected, planned_at)
        return dict(expired_count=len(plan['expired']), next_expiry=next_expiry)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    create = commands.add_parser('snapshot')
    create.add_argument('--directory', required=True)
    create.add_argument('--retention-seconds', type=int, required=True)
    plan = commands.add_parser('plan')
    plan.add_argument('--directory', required=True)
    plan.add_argument('--plan', required=True)
    apply = commands.add_parser('apply')
    apply.add_argument('--plan', required=True)
    apply.add_argument('--expected-sha256', required=True)
    args = parser.parse_args()
    if args.command == 'snapshot':
        result = snapshot(args.directory, args.retention_seconds)
    elif args.command == 'plan':
        result = plan_prune(args.directory, args.plan)
    else:
        result = apply_prune(args.plan, args.expected_sha256)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
