"""Explicit $0.02 capture/sign-out QA grant; disposable ledger only."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from admission import Admission, Rejected
from service_policy import (TWO_TOPIC_RESUME_APPROVAL, TWO_TOPIC_RESUME_POLICIES,
    TESTFLIGHT_SIGNOUT_APPROVAL, TESTFLIGHT_SIGNOUT_POLICIES,
    extend_testflight_signout_policy, open_ledger)


class TestFlightSignoutBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'usage.sqlite'
        self.ledger = Admission(self.path, total_microusd=5_275_000, limits=TWO_TOPIC_RESUME_POLICIES)
        self.addCleanup(lambda: self.ledger.close())
        self.ledger.db.execute('CREATE TABLE qa_budget_extension(id TEXT PRIMARY KEY, amount INTEGER NOT NULL)')
        self.ledger.db.executemany('INSERT INTO qa_budget_extension VALUES(?,?)',
            [('prior-grant', 50_000), (TWO_TOPIC_RESUME_APPROVAL, 45_000)])
        credential, self.token = self.ledger.enroll()
        self.ledger.db.execute('INSERT INTO request VALUES(?,?,?,?,?,?)',
            ('historical-stt', credential, 'stt', 100, 1_340_000, 'completed'))
        self.ledger.db.execute('INSERT INTO recording_qa_grant VALUES(?,?,?)', ('old-daily-grant', 0, 100))

    def tables(self):
        db = self.ledger.db
        return {name: db.execute(f'SELECT * FROM "{name}" ORDER BY rowid').fetchall()
                for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

    def fund(self):
        with self.ledger.transaction():
            extend_testflight_signout_policy(self.ledger.db)

    def reopen(self, migrate=False):
        self.ledger.close()
        with patch.dict(os.environ, VOICE_DATA_DIR=self.temp.name, VOICE_ENABLE_ASK='1'):
            self.ledger = open_ledger(migrate=migrate)

    def test_startup_preserves_original_policy_and_never_funds(self):
        before = self.tables()
        self.reopen(migrate=True)
        self.assertEqual(self.tables(), before)
        self.reopen(migrate=False)
        self.assertEqual(self.tables(), before)
        with self.assertRaisesRegex(Rejected, 'budget_limit'):
            self.ledger.reserve(self.token, 'stt')

    def test_explicit_idempotent_grant_preserves_rows_and_reopens_for_one_attempt(self):
        before = self.tables()
        self.fund()
        after = self.tables()
        for name, rows in before.items():
            if name not in ('budget', 'policy', 'qa_budget_extension'):
                self.assertEqual(after[name], rows, name)
        self.assertEqual(after['budget'], [(1, 5_295_000)])
        self.assertEqual(dict((r[0], tuple(r[1:])) for r in after['policy']), TESTFLIGHT_SIGNOUT_POLICIES)
        self.assertEqual(after['qa_budget_extension'], before['qa_budget_extension'] + [(TESTFLIGHT_SIGNOUT_APPROVAL, 20_000)])
        self.fund()
        self.assertEqual(self.tables(), after)
        self.reopen(migrate=True)
        self.assertEqual(self.tables(), after)
        self.reopen(migrate=False)
        self.assertEqual(self.tables(), after)
        reservation = self.ledger.reserve(self.token, 'stt')
        self.ledger.finish(reservation, completed=False)
        self.fund()  # No automatic retry allocation even after a failed attempt.
        with self.assertRaisesRegex(Rejected, 'budget_limit'):
            self.ledger.reserve(self.token, 'stt')

    def test_unknown_baseline_and_missing_approval_refused_without_changes(self):
        for sql in ("UPDATE policy SET daily=7 WHERE category='stt'",
                    "DELETE FROM qa_budget_extension WHERE id='two-topic-resume-20260929-050'",
                    "UPDATE budget SET cap=5275001"):
            with self.subTest(sql=sql):
                self.ledger.db.execute('SAVEPOINT case_change')
                self.ledger.db.execute(sql)
                before = self.tables()
                with self.assertRaisesRegex(ValueError, 'baseline'):
                    extend_testflight_signout_policy(self.ledger.db)
                self.assertEqual(self.tables(), before)
                self.ledger.db.execute('ROLLBACK TO case_change')
                self.ledger.db.execute('RELEASE case_change')

    def test_active_request_and_mismatched_existing_grant_refused(self):
        self.ledger.db.execute("UPDATE request SET state='active'")
        before = self.tables()
        with self.assertRaisesRegex(ValueError, 'Active'):
            self.fund()
        self.assertEqual(self.tables(), before)
        self.ledger.db.execute("UPDATE request SET state='completed'")
        self.ledger.db.execute('INSERT INTO qa_budget_extension VALUES(?,?)', (TESTFLIGHT_SIGNOUT_APPROVAL, 1))
        before = self.tables()
        with self.assertRaisesRegex(ValueError, 'approval'):
            self.fund()
        self.assertEqual(self.tables(), before)

    def test_requires_transaction_and_rolls_back_partial_failure(self):
        before = self.tables()
        with self.assertRaisesRegex(ValueError, 'transaction'):
            extend_testflight_signout_policy(self.ledger.db)
        self.ledger.db.execute("CREATE TRIGGER block_cap BEFORE UPDATE ON policy BEGIN SELECT RAISE(ABORT, 'fixture failure'); END")
        import sqlite3
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'fixture failure'):
            self.fund()
        self.assertEqual(self.tables(), before)

    def test_funded_caps_without_exact_grant_fail_startup(self):
        self.fund()
        self.ledger.db.execute('DELETE FROM qa_budget_extension WHERE id=?', (TESTFLIGHT_SIGNOUT_APPROVAL,))
        before = self.tables()
        with patch.dict(os.environ, VOICE_DATA_DIR=self.temp.name, VOICE_ENABLE_ASK='1'):
            with self.assertRaises(ValueError):
                open_ledger(migrate=True)
        self.assertEqual(self.tables(), before)


if __name__ == '__main__':
    unittest.main()
