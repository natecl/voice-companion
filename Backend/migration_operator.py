"""Offline operator command. Requires verified identity and deployed maintenance.

Prepare creates private backups and upgrades schema; it is not a read-only plan.
Never run against an old runtime that does not honor database.lock.
"""
import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import uuid
from account_deletion import SCHEMA
from account_migration import migrate_offline
from maintenance import database_lease
from memory_store import MemoryStore


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory(directory):
    paths = sorted(directory.glob('*.sqlite'))
    if not {'memory.sqlite', 'usage.sqlite'} <= {p.name for p in paths}:
        raise ValueError('Required existing databases missing')
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError('Database path is not a regular file')
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
            if db.execute('PRAGMA journal_mode').fetchone()[0] != 'delete':
                raise ValueError('All database files must use rollback journals')
    return paths


def hashes(paths):
    return {p.name: digest(p) for p in paths}


def prepare(directory, identity, plan_path):
    directory, plan_path = Path(directory).resolve(), Path(plan_path).absolute()
    if plan_path.exists():
        raise ValueError('Refusing to overwrite an existing plan')
    if set(identity) != {'source_owner', 'google_owner', 'google_subject'}:
        raise ValueError('Exact verified identity fields required')
    with database_lease(directory):
        paths = inventory(directory)
        with sqlite3.connect(directory/'memory.sqlite') as db:
            if db.execute('PRAGMA user_version').fetchone()[0] not in (20, 21):
                raise ValueError('Unreviewed memory schema')
        backup = directory/'backups'/('founder-migration-' + uuid.uuid4().hex)
        backup.mkdir(parents=True, mode=0o700)
        # Exclude other SQLite writers too while making the coordinated snapshot.
        with ExitStack() as stack:
            for path in paths:
                db = sqlite3.connect(path.as_uri()+'?mode=rw', uri=True, isolation_level=None, timeout=2)
                stack.callback(db.close)
                db.execute('BEGIN IMMEDIATE')
            for path in paths:
                target_path = backup/path.name
                descriptor = os.open(target_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                os.close(descriptor)
                with sqlite3.connect(path.as_uri()+'?mode=ro', uri=True) as source, sqlite3.connect(backup/path.name) as target:
                    source.backup(target)
                    if target.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                        raise ValueError('Backup integrity check failed')
        backup_hashes = hashes(sorted(backup.glob('*.sqlite')))
        MemoryStore(directory/'memory.sqlite')
        with sqlite3.connect(directory/'usage.sqlite') as db:
            db.executescript(SCHEMA)
        result = migrate_offline(directory/'memory.sqlite', directory/'usage.sqlite', **identity)
        plan = dict(version=1, directory=str(directory), identity=identity,
                    backup=str(backup), backup_hashes=backup_hashes,
                    prepared_hashes=hashes(inventory(directory)), migration=result)
        # Private: contains owner IDs and provider subject, never print the plan.
        with plan_path.open('x') as output:
            os.chmod(plan_path, 0o600)
            json.dump(plan, output, indent=2)
            output.flush(); os.fsync(output.fileno())
        return dict(status='prepared', databases_backed_up=len(paths),
                    credentials_to_revoke=result['credentials_to_revoke'], schema=21)


def apply(plan_path):
    plan = json.loads(Path(plan_path).read_text())
    if plan['version'] != 1:
        raise ValueError('Unreviewed operator plan')
    directory = Path(plan['directory']).resolve()
    with database_lease(directory):
        if hashes(inventory(directory)) != plan['prepared_hashes']:
            raise ValueError('Databases changed since preparation; inspect before proceeding')
        backup = Path(plan['backup'])
        if hashes(sorted(backup.glob('*.sqlite'))) != plan['backup_hashes']:
            raise ValueError('Backup changed or is incomplete')
        result = migrate_offline(directory/'memory.sqlite', directory/'usage.sqlite',
                                 **plan['identity'], expected_plan=plan['migration']['plan'])
        # No blind replay: after success, prepared hashes no longer match.
        return dict(status=result['status'], credentials_revoked=result['credentials_to_revoke'],
                    content_owner_preserved=result['content_owner_preserved'])


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prep = commands.add_parser('prepare')
    prep.add_argument('--directory', required=True)
    prep.add_argument('--identity-file', required=True)
    prep.add_argument('--plan', required=True)
    finish = commands.add_parser('apply')
    finish.add_argument('--plan', required=True)
    args = parser.parse_args()
    if args.command == 'prepare':
        result = prepare(args.directory, json.loads(Path(args.identity_file).read_text()), args.plan)
    else:
        result = apply(args.plan)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
