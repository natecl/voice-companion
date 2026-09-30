"""Actual hosted-process/socket evidence; no provider credentials or live data."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen
from websockets.sync.client import connect
from websockets.exceptions import InvalidStatus
import maintenance


class MaintenanceTests(unittest.TestCase):
    def test_flag_requires_explicit_boolean(self):
        self.assertFalse(maintenance.enabled({}))
        self.assertTrue(maintenance.enabled({'VOICE_MAINTENANCE': '1'}))
        with self.assertRaises(ValueError):
            maintenance.enabled({'VOICE_MAINTENANCE': 'yes'})

    def test_actual_maintenance_process_never_opens_databases_or_accepts_work(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            # Invalid SQLite bytes detect accidental startup migrations/recovery.
            originals = {'memory.sqlite': b'private memory sentinel', 'usage.sqlite': b'budget sentinel'}
            for name, data in originals.items(): (root/name).write_bytes(data)
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
            env = {k: v for k, v in os.environ.items() if not k.startswith('VOICE_')}
            env.update(VOICE_MAINTENANCE='1', VOICE_DATA_DIR=directory, PORT=str(port))
            env.pop('XAI_API_KEY', None); env.pop('OPENAI_API_KEY', None)
            command = [sys.executable, str(Path(__file__).with_name('hosted.py'))]
            with maintenance.database_lease(root):
                process = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
                try:
                    for _ in range(100):
                        try:
                            with urlopen(f'http://127.0.0.1:{port}/health', timeout=.2) as response:
                                self.assertEqual(json.load(response), {'state':'maintenance','database_open':False,'workers':'stopped'})
                            break
                        except OSError: time.sleep(.02)
                    else: self.fail('Maintenance did not become healthy')
                    for route in ('account','memory','notes','companion','stt','ask','proactive','health/learning','health/indexing','health/notes'):
                        with self.assertRaises(HTTPError) as failure:
                            urlopen(f'http://127.0.0.1:{port}/{route}', timeout=1)
                        self.assertEqual(failure.exception.code, 503)
                        self.assertEqual(failure.exception.headers['Retry-After'], '60')
                    with self.assertRaises(InvalidStatus) as failure:
                        connect(f'ws://127.0.0.1:{port}/account', open_timeout=1)
                    self.assertEqual(failure.exception.response.status_code, 503)
                    duplicate = subprocess.run(command, env=env, capture_output=True, timeout=5)
                    self.assertNotEqual(duplicate.returncode, 0)
                    self.assertIn(b'BlockingIOError', duplicate.stderr)
                    for name, data in originals.items(): self.assertEqual((root/name).read_bytes(), data)
                    self.assertEqual({p.name for p in root.iterdir()}, set(originals) | {'service.lock','database.lock'})
                finally:
                    process.terminate(); process.wait(timeout=5)
                    process.stderr.close()

    def test_database_lease_blocks_normal_startup_before_ledger_access(self):
        with tempfile.TemporaryDirectory() as directory:
            env = {k:v for k,v in os.environ.items() if not k.startswith('VOICE_')}
            env.update(VOICE_DATA_DIR=directory, XAI_API_KEY='unused')
            with maintenance.database_lease(directory):
                result = subprocess.run([sys.executable, str(Path(__file__).with_name('hosted.py'))], env=env, capture_output=True, timeout=5)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(b'BlockingIOError', result.stderr)
                self.assertFalse((Path(directory)/'usage.sqlite').exists())
            # Exclusion releases on normal exit; no stale lockfile bypass needed.
            with maintenance.database_lease(directory): pass


if __name__ == '__main__': unittest.main()
