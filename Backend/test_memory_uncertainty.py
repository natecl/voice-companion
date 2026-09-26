"""Real store/writer execution with recorded or synthetic judgments; no provider calls."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from admission import Rejected
from memory_store import MemoryStore
from memory_writer import MemoryWriter, select_claims
from test_memory import source, candidate

FIXTURE = Path(__file__).parent / 'fixtures/memory_rework/maya_correction.json'


class UncertaintyTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / 'memory.sqlite'
        self.store = MemoryStore(self.path, personal_learning=True, clock=lambda: 300.)
        self.owner = self.store.owner_for('test-owner')
        self.fixture = json.loads(FIXTURE.read_text())
        self.store.put_source(self.owner, dict(source('old', text="My daughter Maya enjoys swimming."), origin='personal_text'))
        self.store.commit_claims(self.store.claim_job(self.owner), [dict(
            candidate(self.fixture['old']['text']), subject=self.fixture['old']['subject'],
            kind='preference', profile_link=True)])
        self.old = self.store.profile(self.owner)[0]

    def selected(self, answers=None):
        fixture = self.fixture
        claims, _ = select_claims(fixture['source'], fixture['cached']['extract']['data']['memories'],
            answers or fixture['cached']['judge']['data']['answers'], [[self.old]], ['supported'])
        return claims

    def write(self, claims):
        self.store.put_source(self.owner, self.fixture['source'])
        job = self.store.claim_job(self.owner)
        self.store.commit_claims(job, claims)
        return job

    async def test_recorded_maya_through_actual_writer_persists_uncertainty(self):
        fixture = self.fixture
        calls = []

        class ReplayModels:
            async def extract(self, request):
                calls.append('extract')
                return fixture['cached']['extract']

            async def verify_support(self, request):
                calls.append('support')
                return fixture['cached']['support']

            async def judge(self, request):
                calls.append('judge')
                return fixture['cached']['judge']

        class ReplayBudget:
            def reserve(self, *args): pass
            def finish(self, *args): pass

        self.store.put_source(self.owner, fixture['source'])
        result = await MemoryWriter(self.store, ReplayModels(), ReplayBudget()).process_next(self.owner)
        self.assertEqual(calls, ['extract', 'support', 'judge'])
        self.assertEqual(result['decisions'][0]['reason'], 'unresolved')
        self.assertEqual([c['id'] for c in self.store.profile(self.owner)], [self.old['id']])
        self.assertEqual(len(self.store.search(self.owner, historical=True)), 1)
        reopened = MemoryStore(self.path, personal_learning=True)
        unresolved = reopened.search(self.owner, unresolved_only=True)
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]['state'], 'unresolved')
        self.assertEqual(unresolved[0]['identity_status'], 'unresolved')
        mention = reopened.identities.mentions(self.owner, unresolved[0]['id'])[0]
        self.assertEqual(mention['description']['name'], 'Maya')
        self.assertEqual(mention['description']['relationship'], 'daughter')
        self.assertIsNone(mention['description']['qualifiers'])
        self.assertEqual(unresolved[0]['proposed_targets'], [self.old['id']])
        self.assertEqual(unresolved[0]['sources'][0]['session'], fixture['source']['session_id'])
        self.assertEqual(reopened.profile(self.owner)[0]['state'], 'active')

    def test_conflict_and_incompatible_update_never_default_to_new(self):
        answers = copy.deepcopy(self.fixture['cached']['judge']['data']['answers'])
        answers['relation_0'] = dict(choice='conflict', confidence=1., probabilities={'conflict':1.})
        self.assertEqual(self.selected(answers)[0]['relation'], 'unresolved')
        answers['relation_0'] = dict(choice='update_0', confidence=1., probabilities={'update_0':1.})
        self.old['kind'] = 'event'  # Strong judgment cannot bypass incompatible store contract.
        incompatible = self.selected(answers)[0]
        self.assertEqual(incompatible['relation'], 'unresolved')
        self.assertNotEqual(incompatible['subject'], self.old['subject'])

    def test_explicit_new_and_supported_correction_keep_their_behavior(self):
        answers = copy.deepcopy(self.fixture['cached']['judge']['data']['answers'])
        answers['relation_0'] = dict(choice='new', confidence=1., probabilities={'new':1.})
        self.assertEqual(self.selected(answers)[0]['relation'], 'new')
        answers['relation_0'] = dict(choice='update_0', confidence=1., probabilities={'update_0':1.})
        claims = self.selected(answers)
        self.assertEqual(claims[0]['relation'], 'supersedes')
        self.write(claims)
        self.assertIn('tennis', self.store.profile(self.owner)[0]['text'])
        states = {c['id']:c['state'] for c in self.store.search(self.owner, historical=True)}
        self.assertEqual(states[self.old['id']], 'superseded')

    def test_cross_owner_proposal_rolls_back_entire_job(self):
        other = self.store.owner_for('other-owner')
        self.store.put_source(other, source('other'))
        self.store.commit_claims(self.store.claim_job(other), [candidate()])
        foreign_id = self.store.search(other)[0]['id']
        self.store.put_source(self.owner, self.fixture['source'])
        job = self.store.claim_job(self.owner)
        claims = self.selected()
        claims.append(dict(claims[0], proposed_targets=[foreign_id]))
        with self.assertRaisesRegex(Rejected, 'stale_relation_target'):
            self.store.commit_claims(job, claims)
        self.assertEqual(self.store.search(self.owner, unresolved_only=True), [])
        self.assertEqual(self.store.search(other, unresolved_only=True), [])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT state FROM job WHERE id=?', (job['id'],)).fetchone()[0], 'running')

    def test_target_deletion_does_not_promote_unresolved_claim(self):
        self.write(self.selected())
        self.store.delete_source(self.owner, 'old')
        unresolved = self.store.search(self.owner, unresolved_only=True)
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]['proposed_targets'], [])
        self.assertEqual(self.store.profile(self.owner), [])
        self.store.delete_source(self.owner, self.fixture['source']['session_id'])
        self.assertEqual(self.store.search(self.owner, unresolved_only=True), [])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM claim_relation_proposal').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT count(*) FROM claim WHERE text IS NOT NULL').fetchone()[0], 0)

    def test_deleted_target_and_revised_source_reject_stale_commit(self):
        claims = self.selected()
        self.store.put_source(self.owner, self.fixture['source'])
        job = self.store.claim_job(self.owner)
        self.store.delete_source(self.owner, 'old')
        with self.assertRaisesRegex(Rejected, 'stale_relation_target'):
            self.store.commit_claims(job, claims)
        revised = dict(self.fixture['source'], revision=2)
        self.store.put_source(self.owner, revised)
        with self.assertRaisesRegex(Rejected, 'stale_job'):
            self.store.commit_claims(job, claims)
        self.assertEqual(self.store.search(self.owner, unresolved_only=True), [])

    def test_schema3_migration_preserves_claims_tombstones_and_owner(self):
        self.store.delete_source(self.owner, 'deleted')
        with self.store.connect() as db:
            db.execute('DROP TABLE claim_relation_proposal')
            db.execute('PRAGMA user_version=3')
        migrated = MemoryStore(self.path, personal_learning=True)
        self.assertEqual(migrated.owner_for('test-owner'), self.owner)
        self.assertEqual(migrated.profile(self.owner)[0]['id'], self.old['id'])
        self.assertEqual(migrated.put_source(self.owner, source('deleted'))['status'], 'deleted')
        with migrated.connect() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 5)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        self.write(self.selected())
        MemoryStore(self.path)  # Reopening is idempotent; no inference/backfill.
        self.assertEqual(len(migrated.search(self.owner, unresolved_only=True)), 1)


if __name__ == '__main__':
    unittest.main()
