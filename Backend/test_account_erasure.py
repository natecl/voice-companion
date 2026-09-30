"""Fictional populated owners; real SQLite transactions, no network/providers."""
import sqlite3
import tempfile
import unittest
from pathlib import Path

from admission import Rejected
from account_erasure import erase_content, OWNER_TABLES, INDEX_TABLES, CHILD_TABLES
from memory_store import MemoryStore
from companion_chat import CompanionChat
from recording_notes import RecordingNotes
from proactive_store import ProactiveStore
from test_memory import source, candidate
from test_recording_notes import notes
from test_memory_vectors import TinyEmbedder
from memory_vectors import index_source


class AccountErasureTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'memory.sqlite'
        self.store = MemoryStore(self.path, embedding_model='fixture-model-v1')
        self.owner = self.bind('account-a')
        self.other = self.bind('account-b')

    def bind(self, credential, subject=None):
        return self.store.owner_for_identity(credential, issuer='https://accounts.google.com', subject=subject or credential)

    def populate(self, owner):
        self.store.put_source(owner, source())
        job = self.store.claim_job(owner)
        self.store.chunk_plan(job)
        self.store.cache_result(job, 'extract', 'hash', {'text': 'Fictional appointment'})
        self.store.commit_claims(job, [candidate(), candidate(text='Appointment Wednesday')])
        n = RecordingNotes(self.store)
        n.enqueue(owner, 'session-a', 1)
        n.complete(n.claim(owner, 'session-a'), notes())
        index_source(self.store, owner, 'session-a', TinyEmbedder())
        chat = CompanionChat(self.store)
        chat.start(owner, 'question', 'Where is the fictional meeting?')
        chat.complete(owner, 'question', 'At the fictional pavilion.')
        ProactiveStore(self.store).claim(owner, 'capture', 'cutoff')
        # Complete provenance graph, including retained quotes and correction links.
        # Judgment rows are storage fixtures, not model-quality evidence.
        with self.store.transaction() as db:
            db.execute("INSERT OR IGNORE INTO memory_chunk VALUES(?,0,'chunk','fictional plan','fictional claims')", (job['id'],))
            claims = [r[0] for r in db.execute('SELECT id FROM claim WHERE owner=? ORDER BY id', (owner,))]
            entity, mention, link, correction = [owner + suffix for suffix in ('-entity', '-mention', '-link', '-correction')]
            db.execute('INSERT INTO memory_entity VALUES(?,?)', (entity, owner))
            db.execute("INSERT INTO memory_mention VALUES(?,?,?,'session-a',1,'p1','fictional subject','active')", (mention, owner, claims[0]))
            db.execute("INSERT INTO memory_identity_link VALUES(?,?,?,?,NULL,'active','fixture')", (link, owner, mention, entity))
            db.execute("INSERT INTO memory_identity_support VALUES(?,?,'session-a',1,'p1')", (link, owner))
            db.execute("INSERT INTO memory_correction VALUES(?,?,?,?,?,'active','fixture','evidence')", (correction, owner, *claims, entity))
            db.execute('INSERT INTO memory_correction_link VALUES(?,?)', (correction, link))
            db.execute('INSERT INTO claim_relation_proposal VALUES(?,?)', claims)
            db.execute("INSERT INTO memory_fact_evidence VALUES(?,?,'session-a',1,'fictional proposal','fictional judgment')", (claims[0], owner))
            db.execute("INSERT INTO retained_recording VALUES(?,'session-a',1,100,'UTC','fictional retained quote')", (owner,))
            db.execute("INSERT INTO companion_snapshot VALUES(?,'snapshot','session-a','fictional live context')", (owner,))
            db.execute("INSERT INTO companion_dependency VALUES(?,'question','session-a','{}','fixture')", (owner,))
            db.execute("INSERT INTO proactive_connection VALUES(?,'capture','connection','question')", (owner,))
        return job

    def snapshot(self):
        with self.store.connect() as db:
            tables = [r[0] for r in db.execute("SELECT name FROM sqlite_schema WHERE type='table' ORDER BY name")]
            return {t: sorted([tuple(r) for r in db.execute(f'SELECT * FROM {t}')], key=repr) for t in tables}

    def test_every_application_table_has_an_erasure_policy(self):
        tables = set(self.snapshot())
        shadow = {f'{table}_{suffix}' for table in INDEX_TABLES for suffix in ('config', 'content', 'data', 'docsize', 'idx')}
        self.assertEqual(tables - shadow, set(OWNER_TABLES + INDEX_TABLES + CHILD_TABLES) |
                         {'owner', 'erased_account', 'erased_account_credential'})

    def test_populated_owner_erased_other_owner_unchanged_after_restart(self):
        self.populate(self.owner)
        self.populate(self.other)
        before = self.snapshot()
        for table in OWNER_TABLES + INDEX_TABLES + CHILD_TABLES:
            self.assertTrue(before[table], table)  # Exercise every content table.
        self.assertEqual(erase_content(self.store, self.owner), {'status': 'erased'})
        self.store = MemoryStore(self.path)
        self.assertEqual(erase_content(self.store, self.owner), {'status': 'erased'})
        after = self.snapshot()
        for table in OWNER_TABLES + INDEX_TABLES:
            with self.store.connect() as db:
                self.assertEqual(db.execute(f'SELECT count(*) FROM {table} WHERE owner=?', (self.owner,)).fetchone()[0], 0, table)
            expected = [row for row in before[table] if row in after[table]]
            self.assertEqual(after[table], expected, table)
            self.assertEqual(len(after[table]) * 2, len(before[table]), table)
        for table in CHILD_TABLES:
            self.assertEqual(len(after[table]) * 2, len(before[table]), table)
            self.assertTrue(all(row in before[table] for row in after[table]), table)
        self.assertEqual(self.store.source(self.other, 'session-a'), source())
        with self.store.connect() as db:
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
            for table in INDEX_TABLES:
                db.execute(f"INSERT INTO {table}({table}) VALUES('integrity-check')")

    def test_old_credentials_cannot_recreate_owner_but_fresh_signin_can(self):
        self.bind('second-session', 'account-a')
        erase_content(self.store, self.owner)
        for credential in ('account-a', 'second-session'):
            for operation in (lambda: self.store.owner_for(credential), lambda: self.bind(credential, 'account-a')):
                with self.assertRaisesRegex(Rejected, 'account_erased'):
                    operation()
        with self.assertRaisesRegex(Rejected, 'unknown_owner'):
            self.store.owner_for('new-credential', existing_owner=self.owner)
        with self.store.transaction() as db:
            with self.assertRaisesRegex(sqlite3.IntegrityError, 'account_erased'):
                db.execute('INSERT INTO owner VALUES(?)', (self.owner,))
        fresh = self.bind('fresh-session', 'account-a')
        self.assertNotEqual(fresh, self.owner)
        self.assertIsNone(self.store.source(fresh, 'session-a'))

    def test_legacy_and_unknown_owner_are_not_erased(self):
        legacy = self.store.owner_for('founder')
        self.store.put_source(legacy, source())
        before = self.snapshot()
        for owner in (legacy, 'missing', None):
            with self.assertRaisesRegex(Rejected, 'account_not_enrolled'):
                erase_content(self.store, owner)
        self.assertEqual(self.snapshot(), before)

    def test_failed_delete_rolls_back_content_identity_and_tombstones(self):
        self.populate(self.owner)
        with self.store.connect() as db:
            db.execute("CREATE TRIGGER refuse_delete BEFORE DELETE ON owner BEGIN SELECT RAISE(ABORT, 'fixture failure'); END")
        before = self.snapshot()
        with self.assertRaisesRegex(sqlite3.IntegrityError, 'fixture failure'):
            erase_content(self.store, self.owner)
        self.assertEqual(self.snapshot(), before)
        with self.store.connect() as db:
            db.execute('DROP TRIGGER refuse_delete')
        erase_content(self.store, self.owner)

    def test_late_learning_notes_chat_and_sync_cannot_resurrect_content(self):
        self.store.put_source(self.owner, source())
        job = self.store.claim_job(self.owner)
        notes_store = RecordingNotes(self.store)
        notes_store.enqueue(self.owner, 'session-a', 1)
        note_job = notes_store.claim(self.owner, 'session-a')
        chat = CompanionChat(self.store)
        chat.start(self.owner, 'pending', 'A pending question')
        erase_content(self.store, self.owner)
        before = self.snapshot()
        operations = (
            lambda: self.store.cache_result(job, 'extract', 'hash', {}),
            lambda: self.store.commit_claims(job, [candidate()]),
            lambda: notes_store.complete(note_job, notes()),
            lambda: chat.complete(self.owner, 'pending', 'Late answer'),
            lambda: chat.start(self.owner, 'new', 'Late question'),
            lambda: self.store.put_source(self.owner, source()),
            lambda: self.store.delete_source(self.owner, 'session-a'),
            lambda: ProactiveStore(self.store).claim(self.owner, 'capture', 'late'),
        )
        for operation in operations:
            with self.assertRaises((Rejected, sqlite3.IntegrityError)):
                operation()
        self.store.finish_failed(job, 'cancelled')
        notes_store.fail(note_job, 'generation_failed')
        self.assertEqual(self.snapshot(), before)

    def test_embedding_finishing_after_erasure_is_rejected(self):
        self.store.put_source(self.owner, source())
        embedder = TinyEmbedder()
        embedder.after = lambda: erase_content(self.store, self.owner)
        with self.assertRaisesRegex(Rejected, 'stale_embedding_source'):
            index_source(self.store, self.owner, 'session-a', embedder)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_embedding').fetchone()[0], 0)

    def test_schema20_upgrade_preserves_data_and_backup_retains_tombstones(self):
        self.populate(self.owner)
        with self.store.connect() as db:
            db.executescript('DROP TRIGGER prevent_erased_owner_recreation; DROP TABLE erased_account_credential; DROP TABLE erased_account; PRAGMA user_version=20;')
        before = self.snapshot()
        self.store = MemoryStore(self.path)
        after = self.snapshot()
        for table, rows in before.items():
            self.assertEqual(rows, after[table], table)
        erase_content(self.store, self.owner)
        backup = Path(self.folder.name) / 'backup.sqlite'
        self.store.backup(backup)
        restored = MemoryStore(backup)
        with self.assertRaisesRegex(Rejected, 'account_erased'):
            restored.owner_for('account-a')
        self.assertIsNone(restored.source(self.owner, 'session-a'))


if __name__ == '__main__':
    unittest.main()
