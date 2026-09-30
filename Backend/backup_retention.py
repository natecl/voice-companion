"""Opt-in managed-file expiry. No snapshot creation or retention-duration default."""
import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path

from managed_backups import RegistryBusy, checked_path, expire_registered, now, private, write_json

STATUS_FILE = 'managed-backup-retention-status.json'


def settings(env):
    enabled = env.get('VOICE_MANAGED_BACKUP_EXPIRY_ENABLED', '0')
    if enabled not in ('0', '1'):
        raise ValueError('Invalid managed backup expiry flag')
    raw = env.get('VOICE_MANAGED_BACKUP_SCAN_SECONDS')
    if enabled == '0':
        if raw is not None:
            raise ValueError('Backup scan interval requires explicit expiry enablement')
        return None
    if raw is None or not raw.isascii() or not raw.isdecimal() or not 1 <= int(raw) <= 86400:
        raise ValueError('Explicit backup scan interval of 1..86400 seconds required')
    return int(raw)


class RetentionWorker:
    def __init__(self, directory, interval, *, clock=None):
        if type(interval) is not int or not 1 <= interval <= 86400:
            raise ValueError('Invalid backup scan interval')
        self.directory = checked_path(directory, True)
        self.interval = interval
        self.clock = clock
        self.stop = asyncio.Event()
        self.status = dict(version=1, kind='managed-backup-retention', state='starting', scan_count=0, pruned_count=0,
                           last_success_at=None, next_expiry=None, failure=None)

    def read_status(self, path):
        previous = json.loads(private(path).read_text())
        if (not isinstance(previous, dict) or set(previous) != set(self.status)
                or previous.get('version') != 1 or previous.get('kind') != 'managed-backup-retention'
                or previous.get('state') not in ('starting', 'idle', 'deferred', 'stopped', 'failed')):
            raise ValueError('Unrecognized status file; preserve for operator inspection')
        return previous

    def save_status(self):
        path = self.directory / STATUS_FILE
        if path.exists() or path.is_symlink():
            self.read_status(path)
        write_json(path, self.status, replace=True)

    def start(self):
        path = self.directory / STATUS_FILE
        if path.exists() or path.is_symlink():
            previous = self.read_status(path)
            if previous['state'] == 'failed':
                self.status = previous
                raise ValueError('Previous failure requires operator inspection')
        self.save_status()

    def scan(self):
        try:
            result = expire_registered(self.directory, clock=self.clock)
        except RegistryBusy:
            # Acquisition failed before any plan/deletion; normal scheduling
            # resumes next tick. Never treat a later prune I/O failure this way.
            self.status.update(state='deferred')
            self.save_status()
            return
        self.status.update(state='idle', scan_count=self.status['scan_count'] + 1,
                           pruned_count=self.status['pruned_count'] + result['expired_count'],
                           last_success_at=now(self.clock), next_expiry=result['next_expiry'])
        self.save_status()

    async def run(self):
        try:
            await asyncio.to_thread(self.start)
        except Exception as error:
            # Startup refusal must preserve prior incident evidence byte-for-byte,
            # including recognized failures, malformed JSON and foreign files.
            if self.status['state'] != 'failed':
                self.status.update(state='failed', failure=type(error).__name__)
            print('Managed backup expiry startup blocked; existing status preserved; operator inspection required', flush=True)
            return
        try:
            print('Managed backup expiry worker started', flush=True)
            while not self.stop.is_set():
                await asyncio.to_thread(self.scan)
                try:
                    await asyncio.wait_for(self.stop.wait(), timeout=self.interval)
                except TimeoutError:
                    pass
            self.status['state'] = 'stopped'
            await asyncio.to_thread(self.save_status)
        except Exception as error:
            # Deliberately omit paths, identifiers, SQL, content, and exception text.
            self.status.update(state='failed', failure=type(error).__name__)
            try:
                await asyncio.to_thread(self.save_status)
            except Exception:
                print('Managed backup expiry failed; status file unavailable; operator inspection required', flush=True)
            else:
                print('Managed backup expiry failed; inspect private status; worker stopped', flush=True)


@asynccontextmanager
async def running(directory, interval):
    if interval is None:
        yield None
        return
    worker = RetentionWorker(Path(directory), interval)
    task = asyncio.create_task(worker.run())
    try:
        yield worker
    finally:
        # Do not cancel a filesystem operation running in a thread mid-prune.
        worker.stop.set()
        await task
