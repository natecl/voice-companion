"""Identity storage gates: real SQLite transactions, no semantic/model claims."""
import tempfile
from pathlib import Path
import unittest

from admission import Rejected
from memory_store import MemoryStore
from test_memory import source, candidate


def descriptor(name='Maya', relationship='daughter', qualifiers=None, speaker=None):
    return dict(name=name, relationship=relationship,
                qualifiers=[] if qualifiers is None else qualifiers, speaker_label=speaker)


class IdentityTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)/'memory.sqlite'
        self.store = MemoryStore(self.path, clock=lambda: 300.)
        self.owner = self.store.owner_for('owner-a')

    def write(self, session, mention=None, *, owner=None, relation=None, target=None):
        owner = owner or self.owner
        text = 'Maya enjoys swimming.'
        data = source(session, text=text)
        data['passages'][0]['speakers'] = [1]
        self.store.put_source(owner, data)
        c = candidate(text)
        if mention is not None: c['mention'] = mention
        if relation: c.update(relation=relation, target=target)
        self.store.commit_claims(self.store.claim_job(owner), [c])
        claim = next(c for c in self.store.search(owner, historical=True) if any(s['session']==session for s in c['sources']))
        mentions = self.store.identities.mentions(owner, claim['id'])
        selected = next((m for m in mentions if m['session']==session), None)
        return claim, selected

    def ref(self, session, revision=1):
        return dict(session=session, revision=revision, passage='p1')

    def seed(self, mention):
        return self.store.identities.link(self.owner, mention['id'], [self.ref(mention['session'])], rubric='fixture-v1')

    def status(self, claim):
        return next(c for c in self.store.search(self.owner, historical=True) if c['id']==claim['id'])

    def test_same_name_is_unresolved_and_separate_entities_are_opaque(self):
        a, ma = self.write('one', descriptor())
        b, mb = self.write('two', descriptor())
        self.assertNotEqual(ma['id'], mb['id'])
        self.assertEqual(self.status(a)['identity_status'], 'unresolved')
        la, lb = self.seed(ma), self.seed(mb)
        self.assertNotEqual(la['entity'], lb['entity'])
        self.assertNotEqual(la['entity'], self.owner)
        self.assertEqual(self.status(a)['entity_id'], la['entity'])
        self.assertEqual(self.status(b)['entity_id'], lb['entity'])

    def test_link_requires_anchor_evidence_is_idempotent_and_persists(self):
        a, ma = self.write('one', descriptor())
        b, mb = self.write('two', descriptor())
        la = self.seed(ma)
        with self.assertRaisesRegex(Rejected, 'missing_anchor_evidence'):
            self.store.identities.link(self.owner, mb['id'], [self.ref('two')], rubric='fixture-v1', anchor=la['id'])
        refs = [self.ref('one'), self.ref('two')]
        link = self.store.identities.link(self.owner, mb['id'], refs, rubric='fixture-v1', anchor=la['id'])
        self.assertEqual(link['entity'], la['entity'])
        self.assertEqual(self.store.identities.link(self.owner, mb['id'], refs, rubric='fixture-v1', anchor=la['id']), link)
        with self.assertRaisesRegex(Rejected, 'identity_link_conflict'):
            self.seed(mb)
        self.store = MemoryStore(self.path)
        self.assertEqual(self.status(b)['entity_id'], la['entity'])

    def test_distinguishing_and_incomplete_metadata_prevents_link(self):
        a, ma = self.write('one', descriptor())
        anchor = self.seed(ma)
        for index, value in enumerate([descriptor(qualifiers=['other']), descriptor(relationship='colleague'),
                                       dict(descriptor(), qualifiers=None)]):
            session = f'other-{index}'
            b, mb = self.write(session, value)
            with self.assertRaisesRegex(Rejected, 'identity_distinction|incomplete_identity_metadata'):
                self.store.identities.link(self.owner, mb['id'], [self.ref('one'),self.ref(session)],
                                           rubric='fixture-v1', anchor=anchor['id'])
            self.assertEqual(self.status(b)['identity_status'], 'unresolved')

    def test_unknown_speaker_never_establishes_account_owner(self):
        claim, mention = self.write('speech', descriptor(name=None, relationship=None, speaker=1))
        self.assertEqual(self.status(claim)['identity_status'], 'unresolved')
        link = self.seed(mention)
        self.assertNotEqual(link['entity'], self.owner)
        self.assertEqual(mention['description']['speaker_label'], 1)
        # The entity is merely a fresh subject referent, not biometric verification.
        self.assertNotEqual(self.status(claim)['subject'], 'user')

    def test_cross_owner_mention_anchor_and_evidence_are_rejected(self):
        a, ma = self.write('one', descriptor())
        anchor = self.seed(ma)
        other = self.store.owner_for('owner-b')
        b, mb = self.write('two', descriptor(), owner=other)
        with self.assertRaisesRegex(Rejected, 'stale_identity_mention'):
            self.store.identities.link(self.owner, mb['id'], [self.ref('one')], rubric='fixture-v1')
        with self.assertRaisesRegex(Rejected, 'stale_identity_evidence'):
            self.store.identities.link(other, mb['id'], [self.ref('one'),self.ref('two')], rubric='fixture-v1', anchor=anchor['id'])
        # Same session IDs across accounts do not make the foreign anchor eligible.
        self.write('one', descriptor(), owner=other)
        with self.assertRaisesRegex(Rejected, 'stale_identity_anchor'):
            self.store.identities.link(other, mb['id'], [self.ref('one'),self.ref('two')], rubric='fixture-v1', anchor=anchor['id'])

    def test_bridge_deletion_invalidates_transitive_links_without_promoting(self):
        a, ma = self.write('one', descriptor())
        b, mb = self.write('two', descriptor())
        c, mc = self.write('three', descriptor())
        self.store.put_source(self.owner, source('bridge', text='Both references concern the same Maya.'))
        la = self.seed(ma)
        lb = self.store.identities.link(self.owner, mb['id'], [self.ref(s) for s in ['one','two','bridge']], rubric='fixture-v1', anchor=la['id'])
        self.store.identities.link(self.owner, mc['id'], [self.ref('two'), self.ref('three')], rubric='fixture-v1', anchor=lb['id'])
        self.assertEqual(self.status(c)['identity_status'], 'established')
        self.store.delete_source(self.owner, 'bridge')
        self.assertEqual(self.status(a)['identity_status'], 'established')
        for claim in (b,c):
            self.assertEqual(self.status(claim)['identity_status'], 'unresolved')
            self.assertIsNone(self.status(claim)['entity_id'])
        # Restoring the source cannot revive invalid links.
        self.assertEqual(self.store.put_source(self.owner, source('bridge'))['status'], 'deleted')
        with self.assertRaisesRegex(Rejected, 'stale_identity_anchor'):
            self.store.identities.link(self.owner, mc['id'], [self.ref('two'),self.ref('three')], rubric='fixture-v1', anchor=lb['id'])

    def test_revision_and_deletion_scrub_mentions_and_reject_late_links(self):
        a, ma = self.write('one', descriptor(qualifiers=['older']))
        self.seed(ma)
        self.store.put_source(self.owner, source('one', revision=2))
        self.assertEqual(self.store.identities.mentions(self.owner, a['id']), [])
        with self.assertRaisesRegex(Rejected, 'stale_identity_mention'):
            self.seed(ma)
        with self.store.connect() as db:
            self.assertIsNone(db.execute('SELECT description FROM memory_mention WHERE id=?', (ma['id'],)).fetchone()[0])
            self.assertEqual(db.execute("SELECT count(*) FROM memory_identity_link WHERE state='active'").fetchone()[0], 0)
        self.store.delete_source(self.owner, 'one')

    def test_mention_validation_rolls_back_entire_claim_batch(self):
        self.store.put_source(self.owner, source('bad'))
        job = self.store.claim_job(self.owner)
        good = dict(candidate(), mention=descriptor())
        bad = dict(candidate(), mention=descriptor(speaker=42))
        with self.assertRaisesRegex(Rejected, 'invalid_mention_speaker'):
            self.store.commit_claims(job, [good,bad])
        self.assertEqual(self.store.search(self.owner, historical=True), [])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_mention').fetchone()[0], 0)
            self.assertEqual(db.execute('SELECT state FROM job WHERE id=?', (job['id'],)).fetchone()[0], 'running')

    def test_duplicate_support_survives_one_mention_source_deletion(self):
        a, ma = self.write('one', descriptor())
        b, mb = self.write('two', descriptor(), relation='duplicate', target=a['id'])
        self.assertEqual(a['id'], b['id'])
        root = self.seed(mb)
        self.store.identities.link(self.owner, ma['id'], [self.ref('one'),self.ref('two')], rubric='fixture-v1', anchor=root['id'])
        self.store.delete_source(self.owner, 'one')
        self.assertEqual(self.status(a)['entity_id'], root['entity'])
        self.assertEqual([s['session'] for s in self.status(a)['sources']], ['two'])

    def test_legacy_judgment_payload_does_not_change_with_storage_annotations(self):
        from memory_models import judgment_request
        from test_memory_learning import memory
        old = dict(id='prior', subject='maya', text='Maya swims.')
        before = judgment_request(source(), [memory()], [[old]])
        after = judgment_request(source(), [memory()], [[dict(old, identity_status='unresolved', entity_id=None)]])
        self.assertEqual(before, after)

    def test_migrate_v4_preserves_legacy_ids_and_does_not_backfill(self):
        a, _ = self.write('old')
        self.store.delete_source(self.owner, 'deleted')
        with self.store.connect() as db:
            for table in ['memory_correction_link','memory_correction','memory_identity_support','memory_identity_link','memory_mention','memory_entity']:
                db.execute('DROP TABLE '+table)
            db.execute('DROP TABLE IF EXISTS memory_embedding');db.execute('DROP TABLE IF EXISTS memory_passage_index');db.execute('PRAGMA user_version=4')
        self.store = MemoryStore(self.path)
        old = self.status(a)
        self.assertEqual(old['subject'], a['subject'])
        self.assertEqual(old['identity_status'], 'legacy_unverified')
        self.assertIsNone(old['entity_id'])
        self.assertEqual(self.store.identities.mentions(self.owner, a['id']), [])
        self.assertEqual(self.store.owner_for('owner-a'), self.owner)
        self.assertEqual(self.store.put_source(self.owner, source('deleted'))['status'], 'deleted')
        with self.store.connect() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0], 14)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(), [])
        MemoryStore(self.path)


if __name__ == '__main__':
    unittest.main()
