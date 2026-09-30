"""Run the real CLI acceptance fixture and print a content-free local receipt.

Usage: PYTHONPATH=Backend python docs/qa/backup-restore/rehearse.py
All created databases live inside TemporaryDirectory and are disposed by cleanup.
"""
import json
from pathlib import Path
import platform

from backup_restore import digest
from test_backup_restore import BackupRestoreTests


def main():
    fixture = BackupRestoreTests('test_actual_cli_populated_deletion_and_validation')
    calls = []
    original = fixture.cli

    def observed(*args, **kwargs):
        result = original(*args, **kwargs)
        calls.append(dict(command=args[0], result=result))
        return result

    fixture.cli = observed
    try:
        fixture.setUp()
        fixture.test_actual_cli_populated_deletion_and_validation()
        receipt = dict(
            provenance='Disposable fictional SQLite; local deletion workflow; mocked provider revocation; actual operator subprocesses',
            python=platform.python_version(), calls=calls,
            assertions_passed=[
                'Every populated erased-owner content table empty',
                'Unrelated owner content and child graph preserved',
                'Authoritative current usage byte-identical in candidate',
                'All original input file hashes unchanged',
                'Old access, refresh and owner-rebinding credentials denied',
                'Quarantine private permissions and manifest validation passed',
            ],
            limitation='Canonical surviving content must equal authoritative current state; no general reconciliation or activation',
            source_hashes={name: digest(Path('Backend')/name) for name in ('backup_restore.py', 'test_backup_restore.py')},
        )
        deletion_fixture = BackupRestoreTests('test_post_snapshot_source_deletion_refused')
        try:
            deletion_fixture.setUp()
            deletion_fixture.test_post_snapshot_source_deletion_refused()
            receipt['post_snapshot_source_deletion_cli'] = 'refused; no manifest; original hashes unchanged'
        finally:
            deletion_fixture.doCleanups()
        print(json.dumps(receipt, indent=2))
    finally:
        fixture.doCleanups()


if __name__ == '__main__':
    main()
