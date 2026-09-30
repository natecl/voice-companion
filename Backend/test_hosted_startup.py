"""Exercise the real service process and lock without contacting a provider."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from urllib.request import urlopen
from admission import Admission
from maintenance import database_lease


class HostedStartupTests(unittest.TestCase):
    def test_exclusive_lock_and_crash_recovery_preserve_usage(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Admission(Path(directory) / 'usage.sqlite', total_microusd=5_000_000,
                              limits={'stt': (2_000_000, 20_000, 6)})
            _, token = store.enroll()
            request = store.reserve(token, 'stt')
            store.close()
            with socket.socket() as sock:
                sock.bind(('127.0.0.1', 0))
                port = sock.getsockname()[1]
            env = {**os.environ, 'VOICE_DATA_DIR': directory, 'XAI_API_KEY': 'local-unused-fixture', 'PORT': str(port)}
            command = [sys.executable, str(Path(__file__).with_name('hosted.py'))]
            first = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                for _ in range(100):
                    try:
                        with urlopen(f'http://127.0.0.1:{port}/health', timeout=.2) as response:
                            self.assertEqual(response.status, 200)
                            break
                    except OSError:
                        time.sleep(.02)
                else:
                    self.fail('Service failed to become healthy')
                with self.assertRaises(BlockingIOError):
                    with database_lease(directory):
                        self.fail("Offline operator acquired a running service database")
                second = subprocess.run(command, env=env, capture_output=True, timeout=5)
                self.assertNotEqual(second.returncode, 0)
                self.assertIn(b'BlockingIOError', second.stderr)
                store = Admission(Path(directory) / 'usage.sqlite', total_microusd=5_000_000,
                                  limits={'stt': (2_000_000, 20_000, 6)})
                try:
                    self.assertEqual(store.usage(), [('stt', 1, 20_000)])
                    self.assertEqual(store.db.execute('SELECT state FROM request WHERE id=?', (request,)).fetchone()[0], 'interrupted')
                finally:
                    store.close()
            finally:
                first.terminate()
                first.wait(timeout=5)
