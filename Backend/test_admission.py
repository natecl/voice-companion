import concurrent.futures
from pathlib import Path
import tempfile
import threading
import unittest
from admission import Admission, Rejected


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / 'usage.sqlite'
        self.now = 10 * 86400
        self.policy = dict(total_microusd=100, limits={'stt': (80, 20, 3), 'ask': (40, 20, 2)})
        self.store = self.open()
        self.owner, self.token = self.store.enroll()

    def open(self):
        return Admission(self.path, clock=lambda: self.now, **self.policy)

    def tearDown(self):
        self.store.close()
        self.directory.cleanup()

    def reject(self, reason, operation):
        with self.assertRaises(Rejected) as error:
            operation()
        self.assertEqual(str(error.exception), reason)

    def test_credentials_are_hashed_expire_and_revoke_without_charging(self):
        for bad in ('', 'wrong' * 10, None):
            self.reject('unauthorized', lambda: self.store.reserve(bad, 'stt'))
        self.assertNotIn(self.token.encode(), self.path.read_bytes())
        self.store.revoke(self.owner)
        self.reject('unauthorized', lambda: self.store.reserve(self.token, 'stt'))
        _, token = self.store.enroll(lifetime_seconds=1)
        self.now += 1
        self.reject('unauthorized', lambda: self.store.reserve(token, 'stt'))
        self.assertEqual(self.store.usage(), [])

    def test_repeat_sessions_and_restart_keep_charges(self):
        first = self.store.reserve(self.token, 'stt')
        self.reject('busy', lambda: self.store.reserve(self.token, 'stt'))
        self.store.finish(first, completed=True)
        self.store.finish(first, completed=False)
        second = self.store.reserve(self.token, 'stt')
        self.store.close()
        self.store = self.open()
        self.reject('busy', lambda: self.store.reserve(self.token, 'stt'))
        self.store.recover_interrupted()
        self.assertEqual(self.store.usage(), [('stt', 2, 40)])
        self.assertEqual(self.store.db.execute('SELECT state FROM request WHERE id=?', (second,)).fetchone()[0], 'interrupted')
        third = self.store.reserve(self.token, 'stt')
        self.store.finish(third, completed=False)
        self.reject('daily_limit', lambda: self.store.reserve(self.token, 'stt'))
        self.now += 86400
        _, token = self.store.enroll()
        fourth = self.store.reserve(token, 'stt')
        self.store.finish(fourth, completed=True)
        self.reject('budget_limit', lambda: self.store.reserve(token, 'stt'))
        self.assertEqual(self.store.usage(), [('stt', 4, 80)])

    def test_categories_share_total_cap(self):
        for _ in range(3):
            request = self.store.reserve(self.token, 'stt')
            self.store.finish(request, completed=True)
        ask = self.store.reserve(self.token, 'ask')
        self.store.finish(ask, completed=True)
        self.now += 86400
        _, token = self.store.enroll()
        stt = self.store.reserve(token, 'stt')
        self.reject('budget_limit', lambda: self.store.reserve(token, 'ask'))
        self.store.finish(stt, completed=False)
        self.reject('budget_limit', lambda: self.store.reserve(token, 'ask'))

    def test_ask_reservation_can_coexist_with_recording(self):
        self.store.reserve(self.token, 'stt')
        self.store.reserve(self.token, 'ask')
        self.assertEqual(self.store.usage(), [('ask', 1, 20), ('stt', 1, 20)])

    def test_concurrent_connections_cannot_double_reserve(self):
        barrier = threading.Barrier(2)
        def attempt():
            store = self.open()
            try:
                barrier.wait(timeout=5)
                try:
                    return store.reserve(self.token, 'stt')
                except Rejected as error:
                    return str(error)
            finally:
                store.close()
        with concurrent.futures.ThreadPoolExecutor(2) as executor:
            results = list(executor.map(lambda _: attempt(), range(2)))
        self.assertEqual(results.count('busy'), 1)
        self.assertEqual(self.store.usage(), [('stt', 1, 20)])

    def test_unknown_category_and_configuration_changes_fail_closed(self):
        self.reject('unsupported_category', lambda: self.store.reserve(self.token, 'memory'))
        with self.assertRaisesRegex(ValueError, 'migration'):
            Admission(self.path, total_microusd=101, limits=self.policy['limits'])
        self.assertEqual(self.store.usage(), [])
        self.assertEqual(self.store.authorized(self.token), self.owner)

class RecordingAllowanceTests(unittest.TestCase):
    def test_one_extra_attempt_survives_restart_expires_and_keeps_budget(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'usage.sqlite';now=[10*86400]
            def open_store():
                return Admission(path,clock=lambda:now[0],total_microusd=140,limits={'stt':(140,20,3)})
            store=open_store();_,token=store.enroll(lifetime_seconds=3*86400)
            def use():
                req=store.reserve(token,'stt');store.finish(req,completed=False)
            for _ in range(3):use()
            with self.assertRaisesRegex(Rejected,'daily_limit'):use()
            with self.assertRaises(ValueError):store.allow_one_recording_today(now[0]+86400)
            store.allow_one_recording_today(now[0])
            with self.assertRaises(ValueError):store.allow_one_recording_today(now[0])
            store.close();store=open_store()
            use()
            with self.assertRaisesRegex(Rejected,'daily_limit'):use()
            self.assertEqual(store.usage(),[('stt',4,80)])
            now[0]+=86400
            for _ in range(3):use()
            with self.assertRaisesRegex(Rejected,'daily_limit'):use()
            store.allow_one_recording_today(now[0])
            with self.assertRaisesRegex(Rejected,'budget_limit'):use()
            self.assertEqual(store.db.execute("SELECT daily FROM policy WHERE category='stt'").fetchone()[0],3)
            self.assertEqual(store.usage(),[('stt',7,140)])
            store.close()


if __name__ == '__main__':
    unittest.main()
