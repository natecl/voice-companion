import sqlite3
import tempfile
import unittest
from pathlib import Path

from account_migration import migrate_offline
from account_sessions import AccountSessions
from account_tokens import GOOGLE, APPLE, VerifiedIdentity
from admission import Admission, Rejected
from memory_store import MemoryStore
from provider_grants import ProviderGrants
from cryptography.fernet import Fernet
from test_memory import source


class AccountMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.memory = MemoryStore(root/'memory.sqlite')
        self.admission = Admission(root/'usage.sqlite', total_microusd=100,
                                   limits={'ask': (100, 20, 3)})
        self.addCleanup(self.admission.close)
        self.sessions = AccountSessions(self.admission, self.memory)
        self.grants = ProviderGrants(self.admission, Fernet.generate_key())
        legacy_credential, self.legacy_token = self.admission.enroll()
        self.legacy = self.memory.owner_for(legacy_credential)
        self.memory.put_source(self.legacy, source(), learn=False)
        self.google = self.enroll('google', 'chosen-google', 'google-proof')
        self.apple = self.enroll('apple', 'unrelated-apple', 'apple-proof')
        self.memory.put_source(self.apple['owner'], source(text='Unrelated Apple data'), learn=False)
        self.grants.save_apple(self.apple['owner'], 'fixture.client', 'unrelated-grant')

    def enroll(self, provider, subject, proof):
        challenge = self.sessions.challenge(provider)
        identity = VerifiedIdentity(GOOGLE if provider == 'google' else APPLE,
                                    subject, int(self.admission.clock())+300)
        return self.sessions.exchange(challenge['challenge'], provider, identity, proof)

    def migrate(self, plan=None, **overrides):
        args = dict(source_owner=self.legacy, google_owner=self.google['owner'],
                    google_subject='chosen-google', expected_plan=plan)
        args.update(overrides)
        return migrate_offline(self.memory.path, Path(self.temp.name)/'usage.sqlite', **args)

    def test_cutover_preserves_content_ledgers_and_other_provider(self):
        reservation = self.admission.reserve(self.legacy_token, 'ask')
        self.admission.finish(reservation, completed=True)
        before_requests = self.admission.db.execute('SELECT * FROM request').fetchall()
        before_budget = self.admission.db.execute('SELECT * FROM budget').fetchall()
        before_policy = self.admission.db.execute('SELECT * FROM policy').fetchall()
        plan = self.migrate()
        self.assertEqual(plan['status'], 'planned')
        self.admission.authorized(self.legacy_token)
        self.assertEqual(self.migrate(plan['plan'])['status'], 'applied')
        for token in (self.legacy_token, self.google['token']):
            with self.assertRaisesRegex(Rejected, 'unauthorized'):
                self.admission.authorized(token)
        self.admission.authorized(self.apple['token'])
        self.assertEqual(self.memory.source(self.legacy, 'session-a'), source())
        self.assertEqual(self.memory.source(self.apple['owner'], 'session-a')['passages'][0]['text'], 'Unrelated Apple data')
        self.assertEqual(self.grants.apple_for(self.apple['owner']), [('fixture.client', 'unrelated-grant')])
        self.assertEqual(self.admission.db.execute('SELECT * FROM budget').fetchall(), before_budget)
        self.assertEqual(self.admission.db.execute('SELECT * FROM policy').fetchall(), before_policy)
        self.assertEqual(self.admission.db.execute('SELECT * FROM request').fetchall(), before_requests)
        with self.assertRaisesRegex(Rejected, 'migration_source_not_legacy'):
            self.migrate(plan['plan'])
        fresh = self.enroll('google', 'chosen-google', 'fresh-google-proof')
        self.assertEqual(fresh['owner'], self.legacy)
        self.admission.authorized(fresh['token'])
        with self.memory.connect() as db:
            old_credential = self.admission.db.execute('SELECT id FROM credential WHERE digest=?',
                                                       (self.admission.digest(self.google['token']),)).fetchone()[0]
            self.assertEqual(db.execute('SELECT owner FROM credential_owner WHERE credential=?',
                                         (old_credential,)).fetchone()[0], self.google['owner'])

    def test_active_request_blocks_cutover(self):
        self.admission.reserve(self.legacy_token, 'ask')
        with self.assertRaisesRegex(Rejected, 'migration_request_active'):
            self.migrate()

    def test_unknown_usage_owner_table_blocks_cutover(self):
        self.admission.db.execute('CREATE TABLE future_entitlement(owner TEXT, tier TEXT)')
        with self.assertRaisesRegex(Rejected, 'migration_unknown_owner_table'):
            self.migrate()

    def test_changed_plan_rejects_before_revocation(self):
        plan = self.migrate()
        self.memory.put_source(self.legacy, source('new-source'), learn=False)
        with self.assertRaisesRegex(Rejected, 'migration_plan_changed'):
            self.migrate(plan['plan'])
        self.admission.authorized(self.legacy_token)
        self.admission.authorized(self.google['token'])

    def test_nonempty_destination_and_wrong_identity_rejected(self):
        with self.assertRaisesRegex(Rejected, 'migration_google_identity_changed'):
            self.migrate(google_subject='wrong-subject')
        self.memory.put_source(self.google['owner'], source(), learn=False)
        with self.assertRaisesRegex(Rejected, 'migration_google_has_content'):
            self.migrate()

    def test_deletion_and_future_owner_table_rejected(self):
        self.admission.db.execute("INSERT INTO account_deletion VALUES(?,?,'pending')", (self.legacy, 'fixture'))
        with self.assertRaisesRegex(Rejected, 'migration_deletion_exists'):
            self.migrate()
        self.admission.db.execute('DELETE FROM account_deletion')
        with self.memory.connect() as db:
            db.execute('CREATE TABLE future_private_data(owner TEXT, value TEXT)')
        with self.assertRaisesRegex(Rejected, 'migration_unknown_owner_table'):
            self.migrate()

    def test_binding_failure_rolls_back_session_revocations(self):
        plan = self.migrate()
        with self.memory.connect() as db:
            db.execute("CREATE TRIGGER fail_cutover BEFORE UPDATE ON account_identity BEGIN SELECT RAISE(ABORT,'fixture failure'); END")
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'fixture failure'):
            self.migrate(plan['plan'])
        self.admission.authorized(self.legacy_token)
        self.admission.authorized(self.google['token'])
        self.assertEqual(self.migrate()['plan'], plan['plan'])

    def test_wal_pair_rejected_without_changing_journal_mode(self):
        with self.memory.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
        with self.assertRaisesRegex(Rejected, 'migration_requires_rollback_journals'):
            self.migrate()
        with self.memory.connect() as db:
            self.assertEqual(db.execute('PRAGMA journal_mode').fetchone()[0], 'wal')


if __name__ == '__main__':
    unittest.main()
