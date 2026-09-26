import asyncio
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from websockets.asyncio.server import serve
from websockets.asyncio.client import connect
from admission import Admission, Rejected
from memory_store import MemoryStore
from memory_service import MemoryService
from relay import Relay


def source(session='session-a', revision=1, text='The appointment is Tuesday at ten.'):
    return {'session_id': session, 'revision': revision, 'captured_at': 100., 'timezone': 'UTC',
            'completed': True, 'passages': [{'id': 'p1', 'start': 0., 'duration': 2., 'text': text, 'speakers': []}]}


def candidate(text='Appointment Tuesday', **kw):
    return dict(text=text, subject='appointment', kind='event', basis='stated', passages=['p1'],
                judgment_version='fixture-v1', valid_from=100., **kw)


class MemoryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name)/'memory.sqlite'
        self.now = [150.]
        self.store = MemoryStore(self.path, clock=lambda: self.now[0])
        self.owner = self.store.owner_for('credential-a')

    def write(self, content, claims):
        self.store.put_source(self.owner, content)
        if content.get('origin') == 'personal_text':
            # Fixture-only admission; production personal learning remains held.
            with self.store.connect() as db:
                db.execute("UPDATE job SET state='queued' WHERE owner=? AND session=? AND state='profile_pending'", (self.owner, content['session_id']))
        job = self.store.claim_job(self.owner)
        self.store.commit_claims(job, claims)
        return job

    def test_review_empty_job_preserves_history_and_guards_retries(self):
        old=self.write(source(),[])
        with self.assertRaisesRegex(Rejected,'review_not_eligible'):
            self.store.review_empty_job('other-owner',old['id'],'review-v6')
        reviewed=self.store.review_empty_job(self.owner,old['id'],'review-v6')
        self.assertNotEqual(old['id'],reviewed['id'])
        self.assertIsNone(self.store.claim_job(self.owner))
        with self.assertRaisesRegex(Rejected,'review_already_attempted'):
            self.store.review_empty_job(self.owner,old['id'],'review-v6')
        self.store.commit_claims(reviewed,[candidate()])
        with self.assertRaisesRegex(Rejected,'review_not_empty'):
            self.store.review_empty_job(self.owner,old['id'],'review-v7')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT state FROM job WHERE id=?',(old['id'],)).fetchone()[0],'done')

    def test_review_cannot_restore_deleted_or_revised_source(self):
        for session in ('deleted','revised'):
            old=self.write(source(session),[])
            if session=='deleted':self.store.delete_source(self.owner,session)
            else:self.store.put_source(self.owner,source(session,revision=2))
            with self.assertRaisesRegex(Rejected,'review_not_eligible'):
                self.store.review_empty_job(self.owner,old['id'],'review-v6')

    def test_persistence_idempotency_revision_and_backup(self):
        data = source()
        self.assertEqual(self.store.put_source(self.owner, data)['status'], 'stored')
        self.assertEqual(self.store.put_source(self.owner, data)['status'], 'unchanged')
        with self.assertRaises(Rejected):
            self.store.put_source(self.owner, source(text='Conflict'))
        other = MemoryStore(self.path)
        self.assertEqual(other.source(self.owner, 'session-a'), data)
        job = other.claim_job(self.owner)
        self.store.put_source(self.owner, source(revision=2))
        with self.assertRaisesRegex(Rejected, 'stale_job'):
            other.commit_claims(job, [candidate()])
        self.assertEqual(self.store.put_source(self.owner, data)['status'], 'stale')
        backup = Path(self.directory.name)/'backup.sqlite'
        self.store.backup(backup)
        restored = MemoryStore(backup)
        self.assertEqual(restored.source(self.owner, 'session-a')['revision'], 2)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)

    def test_owner_renewal_and_isolation(self):
        second = self.store.owner_for('credential-b')
        self.write(source(), [candidate()])
        self.assertEqual(self.store.owner_for('renewal', existing_owner=self.owner), self.owner)
        self.assertEqual(self.store.owner_for('renewal'), self.owner)
        self.assertEqual(self.store.search(second), [])
        self.assertIsNone(self.store.source(second, 'session-a'))
        self.store.delete_source(second, 'session-a')
        self.assertIsNotNone(self.store.source(self.owner, 'session-a'))
        target = self.store.search(self.owner)[0]['id']
        self.store.put_source(second, source('other-session'))
        with self.assertRaisesRegex(Rejected, 'invalid_relation'):
            self.store.commit_claims(self.store.claim_job(second), [candidate(relation='duplicate', target=target)])
        with self.assertRaisesRegex(Rejected, 'owner_conflict'):
            self.store.owner_for('credential-a', existing_owner=second)

    def test_temporal_correction_expiration_and_evidence_annotations(self):
        self.write(source(), [candidate(valid_until=200.)])
        old = self.store.search(self.owner)[0]['id']
        updated = candidate('Appointment Wednesday', relation='supersedes', target=old, valid_until=300.)
        updated['valid_from'] = 160.
        self.now[0] = 170.
        self.write(source('session-b', text='Correction: Wednesday.'), [updated])
        self.assertEqual([c['text'] for c in self.store.search(self.owner)], ['Appointment Wednesday'])
        self.assertEqual(len(self.store.search(self.owner, historical=True)), 2)
        self.assertEqual(self.store.evidence(self.owner, 'session-a')['passages'][0]['claims'][0]['state'], 'superseded')
        self.now[0] = 400.
        self.assertEqual(self.store.search(self.owner), [])  # read-time filtering before maintenance
        self.store.maintain()
        self.assertEqual(len(self.store.search(self.owner, historical=True)), 2)
        self.assertIsNotNone(self.store.source(self.owner, 'session-a'))

    def test_multi_source_duplicate_deletion_and_stale_resurrection(self):
        self.write(source(), [candidate()])
        first = self.store.search(self.owner)[0]['id']
        self.write(source('session-b'), [candidate(relation='duplicate', target=first)])
        self.store.delete_source(self.owner, 'session-a')
        remaining = self.store.search(self.owner)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(len(remaining[0]['sources']), 1)
        self.store.put_source(self.owner, source('session-c'))
        job = self.store.claim_job(self.owner)
        self.store.delete_source(self.owner, 'session-c')
        with self.assertRaisesRegex(Rejected, 'stale_job'):
            self.store.commit_claims(job, [candidate()])
        self.store.delete_source(self.owner, 'session-b')
        self.assertEqual(self.store.search(self.owner, historical=True), [])
        self.assertEqual(self.store.put_source(self.owner, source('session-a', 10))['status'], 'deleted')
        self.assertIsNone(self.store.evidence(self.owner, 'session-a'))
        with self.store.connect() as db:
            self.assertIsNone(db.execute('SELECT text FROM claim WHERE id=?', (first,)).fetchone()[0])

    def test_invalid_source_atomic_rollback_and_interrupted_jobs(self):
        malformed = source(); malformed['passages'][0]['start'] = float('nan')
        with self.assertRaises(Rejected): self.store.put_source(self.owner, malformed)
        self.store.put_source(self.owner, source())
        job = self.store.claim_job(self.owner)
        invalid = candidate(); invalid['passages'] = ['missing']
        with self.assertRaises(Rejected): self.store.commit_claims(job, [candidate(), invalid])
        self.assertEqual(self.store.search(self.owner), [])
        self.store.recover_jobs()
        self.assertIsNone(self.store.claim_job(self.owner))  # no paid automatic retry after crash
        with self.assertRaises(Rejected): self.store.commit_claims(job, [candidate()])
        self.assertIn({'state': 'interrupted', 'count': 1}, self.store.diagnostics(self.owner)['job'])

    def test_stable_profile_revision_invalidation_and_old_update_rejection(self):
        pref = candidate('Prefers mornings'); pref.update(subject='user', kind='preference')
        self.write(dict(source(), origin='personal_text'), [pref])
        self.now[0] = 10_000_000
        self.store.maintain()
        self.assertEqual(len(self.store.profile(self.owner)), 1)
        target = self.store.profile(self.owner)[0]['id']
        old = dict(pref, relation='supersedes', target=target, valid_from=1.)
        self.store.put_source(self.owner, dict(source('old-import'), origin='personal_text'))
        with self.store.connect() as db:
            db.execute("UPDATE job SET state='queued' WHERE session='old-import'")
        with self.assertRaisesRegex(Rejected, 'ambiguous_update'):
            self.store.commit_claims(self.store.claim_job(self.owner), [old])
        self.store.put_source(self.owner, dict(source(revision=2), origin='personal_text'))
        self.assertEqual(self.store.profile(self.owner), [])

    def test_profile_correction_expiry_and_stale_commit(self):
        fact = dict(candidate(), subject='user', kind='fact', text='I am training for a race.')
        self.write(dict(source('goal'), origin='personal_text'), [fact])
        old = self.store.profile(self.owner)[0]['id']
        self.write(dict(source('correction'), origin='personal_text'),
                   [dict(fact, text='I am training for a swim.', relation='supersedes', target=old, valid_from=120.)])
        self.assertEqual([c['text'] for c in self.store.profile(self.owner)], ['I am training for a swim.'])
        self.write(dict(source('temporary'), origin='personal_text'),
                   [dict(fact, text='I plan to travel this week.', basis='tentative', valid_until=200.)])
        self.assertEqual(len(self.store.profile(self.owner)), 2)
        self.now[0] = 201.
        self.assertEqual(len(self.store.profile(self.owner)), 1)
        self.store.put_source(self.owner, dict(source('pending'), origin='personal_text'))
        with self.store.connect() as db:
            db.execute("UPDATE job SET state='queued' WHERE session='pending'")
        job = self.store.claim_job(self.owner)
        self.store.delete_source(self.owner, 'pending')
        with self.assertRaisesRegex(Rejected, 'stale_job'):
            self.store.commit_claims(job, [fact])

    def test_v2_migration_preserves_sources_and_does_not_invent_profile_links(self):
        self.write(source(), [candidate()])
        with self.store.connect() as db:
            db.execute('ALTER TABLE claim DROP COLUMN profile_link')
            db.execute('PRAGMA user_version=2')
        migrated = MemoryStore(self.path, clock=lambda: self.now[0])
        self.assertEqual(migrated.source(self.owner, 'session-a'), source())
        self.assertEqual(len(migrated.search(self.owner)), 1)
        self.assertEqual(migrated.profile(self.owner), [])
        with migrated.connect() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 8)

    def test_personal_sources_are_held_and_origin_cannot_be_rewritten(self):
        note = dict(source(), origin='personal_text')
        self.store.put_source(self.owner, note)
        self.assertIsNone(self.store.claim_job(self.owner))
        self.assertEqual(self.store.recall_snapshot(self.owner), [])
        self.assertEqual(self.store.put_source(self.owner, note)['status'], 'unchanged')
        with self.assertRaisesRegex(Rejected, 'source_origin_conflict'):
            self.store.put_source(self.owner, source(revision=2))
        self.store = MemoryStore(self.path)
        self.assertEqual(self.store.source(self.owner, 'session-a')['origin'], 'personal_text')
        self.store.delete_source(self.owner, 'session-a')
        self.assertEqual(self.store.put_source(self.owner, note)['status'], 'deleted')

    def test_profile_identity_guard_and_broad_relationship_lifecycle(self):
        user = candidate('I enjoy swimming'); user.update(subject='user', kind='fact')
        self.store.put_source(self.owner, source())
        with self.assertRaisesRegex(Rejected, 'unverified_personal_source'):
            self.store.commit_claims(self.store.claim_job(self.owner), [user])
        self.store.delete_source(self.owner, 'session-a')
        self.write(dict(source('personal'), origin='personal_text'), [user])
        daughter = candidate('My daughter Maya enjoys swimming')
        daughter.update(subject='maya-personal', kind='fact', profile_link=True)
        self.write(dict(source('family'), origin='personal_text'), [daughter])
        # Other conversations must not displace profile facts before profile filtering.
        for index in range(55):
            self.write(source(f'noise-{index}'), [candidate()])
        profile = self.store.profile(self.owner)
        self.assertEqual({c['subject'] for c in profile}, {'user', 'maya-personal'})
        self.assertTrue(all(c['sources'] for c in profile))
        other = self.store.owner_for('other')
        self.assertEqual(self.store.profile(other), [])
        self.store.delete_source(self.owner, 'family')
        self.assertEqual([c['subject'] for c in self.store.profile(self.owner)], ['user'])
        self.store.delete_source(self.owner, 'personal')
        self.assertEqual(self.store.profile(self.owner), [])

    def test_unknown_subject_cannot_merge_across_sessions(self):
        unknown = candidate(); unknown['subject'] = None
        self.write(source(), [unknown])
        target = self.store.search(self.owner)[0]['id']
        self.store.put_source(self.owner, source('session-b'))
        with self.assertRaisesRegex(Rejected, 'invalid_relation'):
            self.store.commit_claims(self.store.claim_job(self.owner), [dict(unknown, relation='duplicate', target=target)])
        self.assertEqual(len(self.store.search(self.owner)), 1)

    def test_write_failure_and_future_schema_preserve_existing_data(self):
        self.store.put_source(self.owner, source())
        with self.store.connect() as lock:
            lock.execute('BEGIN IMMEDIATE')
            with self.assertRaises(sqlite3.OperationalError):
                self.store.delete_source(self.owner, 'session-a')
            lock.execute('ROLLBACK')
        self.assertIsNotNone(self.store.source(self.owner, 'session-a'))
        with self.store.connect() as db: db.execute('PRAGMA user_version=999')
        with self.assertRaisesRegex(ValueError, 'Unsupported memory schema'): MemoryStore(self.path)


class MemorySocketTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_socket_auth_persistence_delete_and_no_provider_usage(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            ledger = Admission(directory/'usage.sqlite', total_microusd=100, limits={'stt': (100,20,6)})
            try:
                credential, token = ledger.enroll()
                store = MemoryStore(directory/'memory.sqlite')
                owner = store.owner_for(credential)
                relay = Relay('unused', admission=ledger, memory=MemoryService(ledger,store))
                async with serve(relay.handle, '127.0.0.1', 0, process_request=relay.authorize) as server:
                    url = f'ws://127.0.0.1:{server.sockets[0].getsockname()[1]}/memory'
                    async def request(data):
                        async with connect(url, additional_headers={'Authorization': 'Bearer '+token}) as client:
                            await client.send(json.dumps(data))
                            return json.loads(await client.recv())
                    envelope = dict(version=1, owner=owner, operation='upsert', source=source())
                    self.assertEqual((await request(envelope))['status'], 'stored')
                    self.assertEqual((await request(envelope))['status'], 'unchanged')
                    self.assertEqual((await request(envelope | {'owner': 'someone-else'}))['message'], 'memory_owner_mismatch')
                    self.assertEqual((await request(dict(version=1, owner=owner, operation='delete', session_id='session-a')))['status'], 'deleted')
                    self.assertEqual((await request(envelope))['status'], 'deleted')
                    personal = dict(version=2, owner=owner, operation='upsert', source=dict(source('personal'), origin='personal_text'))
                    self.assertEqual((await request(personal | {'version': 1}))['message'], 'invalid_memory_request')
                    ack = await request(personal)
                    self.assertEqual((ack['version'], ack['status']), (2, 'stored'))
                    self.assertIsNone(store.claim_job(owner))
                    self.assertEqual((await request(personal | {'owner': 'someone-else'}))['message'], 'memory_owner_mismatch')
                    ledger.revoke(credential)
                    with self.assertRaises(Exception): await request(envelope)
                self.assertEqual(ledger.usage(), [])
                self.assertIsNone(MemoryStore(directory/'memory.sqlite').source(owner, 'session-a'))
            finally:
                ledger.close()


if __name__ == '__main__': unittest.main()
