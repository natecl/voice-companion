"""Prepare and validate a quarantined memory candidate; never activate a restore.

Surviving-owner historical changes are not reconciled: any content difference
from authoritative current state is refused. Activation remains unsupported.

Inputs must be independently verified authoritative current state and a pinned
memory snapshot. Hashes detect changes, not freshness or authenticity. Historical
usage is never an input. See docs/qa/backup-restore/README.md before operation.
"""
import argparse
from contextlib import ExitStack, closing
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3

from account_erasure import erase_content
from maintenance import database_lease
from managed_backups import snapshot_read_lease
from memory_store import MemoryStore

# Exact reviewed schema21 and account-enabled usage schema (including grants).
# Fail closed even if a future schema forgets to increment user_version.
SCHEMAS = {
    'memory': '37ff29910ffdc7afab69c80a9ab2e54976086cf64c806669542d6655fbd56b37',
    'usage': '651fdae7778a664ca9109b6ee03695a57806c5aa8c9b70571d5ea0bb4a4a8301',
}
AUTH_TABLES = ('credential_owner', 'account_identity', 'erased_account_credential', 'erased_account')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def regular(path):
    path = Path(path).absolute()
    if path.is_symlink() or not path.is_file() or path.resolve() != path or path.stat().st_nlink != 1:
        raise ValueError('Require canonical regular single-link files without symlinks')
    for suffix in ('-wal', '-shm', '-journal'):
        if Path(str(path) + suffix).exists():
            raise ValueError('Database sidecar present; require clean offline files')
    return path


def pin(path, expected):
    if not isinstance(expected, str) or len(expected) != 64 or digest(regular(path)) != expected:
        raise ValueError('File hash changed or unverified input')


def rows(db, table):
    return set(db.execute(f'SELECT * FROM "{table}"').fetchall())


def inspect(db, kind):
    schema = db.execute('SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name').fetchall()
    actual = hashlib.sha256(json.dumps(schema, separators=(',', ':')).encode()).hexdigest()
    if actual != SCHEMAS[kind] or db.execute('PRAGMA user_version').fetchone()[0] != (21 if kind == 'memory' else 0):
        raise ValueError('Unreviewed database schema')
    if db.execute('PRAGMA journal_mode').fetchone()[0] != 'delete':
        raise ValueError('Require rollback journal databases')
    if db.execute('PRAGMA integrity_check').fetchall() != [('ok',)] or db.execute('PRAGMA foreign_key_check').fetchall():
        raise ValueError('Database integrity failure')
    if kind == 'usage':
        if db.execute("SELECT 1 FROM account_deletion WHERE state!='complete'").fetchone():
            raise ValueError('Pending deletion')
        if db.execute("SELECT 1 FROM request WHERE state='active'").fetchone():
            raise ValueError('Active work')
    else:
        # Queued work is also refused: the candidate must not silently schedule it.
        for table, states in (
            ('job', ('queued', 'running')), ('memory_index_job', ('queued', 'running')),
            ('recording_notes', ('pending', 'generating')), ('companion_turn', ('pending',)),
            ('proactive_attempt', ('pending',)),
        ):
            marks = ','.join('?' for _ in states)
            if db.execute(f'SELECT 1 FROM {table} WHERE state IN ({marks})', states).fetchone():
                raise ValueError('Active work')


def check_relationships(snapshot, current, usage):
    erased = rows(current, 'erased_account')
    erased_owners = {r[0] for r in erased}
    completed = {r[0] for r in usage.execute('SELECT owner FROM account_deletion')}
    if completed != erased_owners:
        raise ValueError('Deletion ledger and tombstones disagree')
    if rows(current, 'owner') & {(owner,) for owner in erased_owners}:
        raise ValueError('Erased owner still present')
    if not rows(snapshot, 'erased_account') <= erased or not rows(snapshot, 'erased_account_credential') <= rows(current, 'erased_account_credential'):
        raise ValueError('Deletion history regressed')
    expected = rows(snapshot, 'owner') - {(owner,) for owner in erased_owners}
    if expected != rows(current, 'owner'):
        raise ValueError('Owner mapping changed; migration or re-enrollment requires separate recovery')
    identities = {r for r in rows(snapshot, 'account_identity') if r[2] not in erased_owners}
    if identities != rows(current, 'account_identity'):
        raise ValueError('Identity mapping changed')
    current_credentials = dict(rows(current, 'credential_owner'))
    tombstones = dict(rows(current, 'erased_account_credential'))
    if current_credentials.keys() & tombstones.keys():
        raise ValueError('Erased credential still mapped')
    for credential, owner in rows(snapshot, 'credential_owner'):
        if owner in erased_owners:
            if tombstones.get(credential) != owner:
                raise ValueError('Historical credential missing deletion protection')
        elif credential in current_credentials and current_credentials[credential] != owner:
            raise ValueError('Credential owner mapping changed')
    for credential, owner, revoked in usage.execute(
            'SELECT s.credential,s.owner,c.revoked FROM account_session s JOIN credential c ON c.id=s.credential'):
        if owner in erased_owners:
            if revoked != 1 or tombstones.get(credential) != owner:
                raise ValueError('Deleted session lacks revocation or tombstone')
        elif current_credentials.get(credential) != owner:
            raise ValueError('Current session owner mapping inconsistent')
    if rows(usage, 'deleting_identity'):
        raise ValueError('Incomplete provider deletion')
    if usage.execute('SELECT 1 FROM apple_grant g JOIN account_deletion d ON d.owner=g.owner').fetchone():
        raise ValueError('Incomplete provider deletion')
    if usage.execute('SELECT 1 FROM google_deletion WHERE content_erased!=1').fetchone():
        raise ValueError('Incomplete provider deletion')
    return erased_owners


def check_content(candidate, current):
    # Deliberately strict: no attempt to infer safe source/correction rollback.
    # FTS virtual/shadow tables are index representations rebuilt by erasure;
    # their source, notes and full provenance remain in canonical tables.
    canonical = {r[1] for r in current.execute('PRAGMA table_list') if r[0] == 'main' and r[2] == 'table'}
    tables = [r[0] for r in current.execute("SELECT name FROM sqlite_schema WHERE type='table'") if r[0] in canonical]
    for table in tables:
        if table not in AUTH_TABLES and rows(candidate, table) != rows(current, table):
            raise ValueError('Historical content differs from authoritative current state')


def private_quarantine(output):
    if (output.is_symlink() or not output.is_dir() or output.resolve() != output
            or output.stat().st_mode & 0o777 != 0o700):
        raise ValueError('Require private canonical quarantine directory')
    for name in ('memory.sqlite', 'usage.sqlite', 'manifest.json'):
        path = regular(output/name)
        if path.stat().st_mode & 0o777 != 0o600:
            raise ValueError('Require private quarantine artifacts')


def locked_inputs(stack, paths, pins):
    connections = []
    for path, expected, kind in zip(paths, pins, ('memory', 'memory', 'usage')):
        pin(path, expected)
        db = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True, isolation_level=None, timeout=0)
        stack.callback(db.close)
        db.execute('BEGIN IMMEDIATE')  # excludes SQLite writers that ignore the lease
        pin(path, expected)
        inspect(db, kind)
        connections.append(db)
    return connections


def prepare(directory, snapshot, output, *, snapshot_hash, memory_hash, usage_hash):
    directory = Path(directory).absolute()
    snapshot = regular(snapshot)
    output = Path(output).absolute()
    paths = [snapshot, regular(directory/'memory.sqlite'), regular(directory/'usage.sqlite')]
    if len({p.stat().st_ino for p in paths}) != 3:
        raise ValueError('Inputs must be distinct files')
    pins = [snapshot_hash, memory_hash, usage_hash]
    if output.exists() or output.is_symlink() or output.parent.resolve() != output.parent:
        raise ValueError('Require new quarantine directory with canonical parent')
    regular(directory/'database.lock')  # Existing runtime lease; do not create authority.
    with database_lease(directory), snapshot_read_lease(paths[0]), ExitStack() as stack:
        old, current, usage = locked_inputs(stack, paths, pins)
        erased_owners = check_relationships(old, current, usage)
        output.mkdir(mode=0o700)
        # Failure deliberately leaves an unmanifested quarantine for inspection.
        for source, name in ((snapshot, 'memory.sqlite'), (paths[2], 'usage.sqlite')):
            target = output/name
            with target.open('xb') as stream, source.open('rb') as original:
                os.chmod(target, 0o600)
                shutil.copyfileobj(original, stream)
                stream.flush()
                os.fsync(stream.fileno())
        candidate = MemoryStore(output/'memory.sqlite')
        replayed = 0
        for owner in sorted(erased_owners):
            if old.execute('SELECT 1 FROM owner WHERE id=?', (owner,)).fetchone():
                erase_content(candidate, owner)
                replayed += 1
        with candidate.transaction() as db:
            for table in AUTH_TABLES:
                db.execute(f'DELETE FROM {table}')
            for table in reversed(AUTH_TABLES):
                values = sorted(rows(current, table))
                if values:
                    marks = ','.join('?' for _ in values[0])
                    db.executemany(f'INSERT INTO {table} VALUES({marks})', values)
        with closing(sqlite3.connect(output/'memory.sqlite')) as db:
            inspect(db, 'memory')
            check_relationships(db, current, usage)
            check_content(db, current)
            for table in AUTH_TABLES + ('owner',):
                if rows(db, table) != rows(current, table):
                    raise ValueError('Candidate account state mismatch')
        for path, expected in zip(paths, pins):
            pin(path, expected)
        pin(output/'usage.sqlite', usage_hash)
        manifest = dict(version=1, status='quarantined', directory=str(directory),
                        snapshot=str(snapshot), input_hashes=pins,
                        candidate_hashes={name: digest(output/name) for name in ('memory.sqlite', 'usage.sqlite')},
                        replayed_deletions=replayed, activation_supported=False)
        manifest_path = output/'manifest.json'
        with manifest_path.open('x') as stream:
            os.chmod(manifest_path, 0o600)
            json.dump(manifest, stream, indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        return dict(status='quarantined', replayed_deletions=replayed,
                    manifest_sha256=digest(manifest_path), activation_supported=False)


def validate(output, manifest_hash):
    output = Path(output).absolute()
    private_quarantine(output)
    manifest_path = output/'manifest.json'
    pin(manifest_path, manifest_hash)
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('version') != 1 or manifest.get('status') != 'quarantined' or manifest.get('activation_supported') is not False:
        raise ValueError('Unreviewed manifest')
    directory = Path(manifest['directory'])
    paths = [Path(manifest['snapshot']), directory/'memory.sqlite', directory/'usage.sqlite']
    regular(directory/'database.lock')  # Existing runtime lease; do not create authority.
    with database_lease(directory), snapshot_read_lease(paths[0]), ExitStack() as stack:
        _, current, usage = locked_inputs(stack, paths, manifest['input_hashes'])
        for name, kind in (('memory.sqlite', 'memory'), ('usage.sqlite', 'usage')):
            pin(output/name, manifest['candidate_hashes'][name])
            db = sqlite3.connect((output/name).as_uri() + '?mode=rw', uri=True, isolation_level=None, timeout=0)
            stack.callback(db.close)
            db.execute('BEGIN IMMEDIATE')
            inspect(db, kind)
            pin(output/name, manifest['candidate_hashes'][name])
            if kind == 'memory':
                check_relationships(db, current, usage)
                check_content(db, current)
                for table in AUTH_TABLES + ('owner',):
                    if rows(db, table) != rows(current, table):
                        raise ValueError('Candidate account state mismatch')
        pin(manifest_path, manifest_hash)
        private_quarantine(output)
    return dict(status='validated_quarantine', activation_supported=False)


def main():
    os.umask(0o077)
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    prep = commands.add_parser('prepare')
    for name in ('directory', 'snapshot', 'output', 'snapshot-hash', 'memory-hash', 'usage-hash'):
        prep.add_argument('--' + name, required=True)
    check = commands.add_parser('validate')
    check.add_argument('--output', required=True)
    check.add_argument('--manifest-hash', required=True)
    args = vars(parser.parse_args())
    command = args.pop('command')
    try:
        result = prepare(**args) if command == 'prepare' else validate(args['output'], args['manifest_hash'])
    except ValueError as error:
        parser.exit(1, f'Restore preparation/validation refused: {error}.\n')
    except (OSError, sqlite3.Error):
        parser.exit(1, 'Restore preparation/validation refused; inspect file access, locks and database integrity.\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
