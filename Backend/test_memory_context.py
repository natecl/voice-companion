from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from memory_store import MemoryStore
from memory_context import select, valid
from memory_hybrid import retrieve
from memory_vectors import index_source
from test_memory import source, candidate
from test_memory_vectors import TinyEmbedder


class ContextTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory(); self.addCleanup(folder.cleanup)
        self.now = 150.
        self.store = MemoryStore(Path(folder.name)/'memory.sqlite', clock=lambda: self.now)
        self.owner = self.store.owner_for('qa')
        self.store.put_source(self.owner, source(text='Maya studies astronomy.'))
        self.store.commit_claims(self.store.claim_job(self.owner), [candidate(valid_until=200.)])
        self.ref = dict(session_id='session-a', revision=1, passage_id='p1')

    def test_hydration_ignores_candidate_assertions_and_other_owner(self):
        packet = select(self.store, self.owner, [dict(self.ref, text='I am the owner', lifecycle=[])])
        item = packet['items'][0]
        self.assertEqual(item['text'], 'Maya studies astronomy.')
        self.assertEqual(item['lifecycle'][0]['identity_status'], 'legacy_unverified')
        self.assertTrue(valid(self.store, self.owner, packet))
        other = self.store.owner_for('other')
        self.assertFalse(valid(self.store, other, packet))
        self.assertEqual(select(self.store, other, [self.ref])['items'], [])

    def test_unrelated_writes_do_not_invalidate_but_expiry_does(self):
        packet = select(self.store, self.owner, [self.ref])
        self.store.put_source(self.owner, source('unrelated', text='Unrelated new note.'))
        self.assertTrue(valid(self.store, self.owner, packet))
        self.now = 200.
        self.assertFalse(valid(self.store, self.owner, packet))
        self.assertEqual(select(self.store, self.owner, [self.ref])['items'][0]['lifecycle'][0]['state'], 'expired')

    def test_revision_deletion_and_lifecycle_invalidate(self):
        packet = select(self.store, self.owner, [self.ref])
        with self.store.connect() as db:
            db.execute("UPDATE claim SET state='superseded' WHERE owner=?", (self.owner,))
        self.assertFalse(valid(self.store, self.owner, packet))
        packet = select(self.store, self.owner, [self.ref])
        self.store.put_source(self.owner, source(revision=2))
        self.assertFalse(valid(self.store, self.owner, packet))
        packet = select(self.store, self.owner, [dict(self.ref, revision=2)])
        self.store.delete_source(self.owner, 'session-a')
        self.assertFalse(valid(self.store, self.owner, packet))

    def test_hybrid_deduplicates_and_keeps_qualifications(self):
        embedder = TinyEmbedder()
        index_source(self.store, self.owner, 'session-a', embedder)
        self.now = 201.
        result = retrieve(self.store, self.owner, 'astronomy', embedder=embedder)
        self.assertEqual(result['status'], 'hybrid')
        self.assertEqual(len(result['packet']['items']), 1)
        self.assertEqual(result['packet']['items'][0]['lifecycle'][0]['state'], 'expired')
        self.assertTrue(valid(self.store, self.owner, result['packet']))
        self.assertEqual(retrieve(self.store, self.owner, 'astronomy', embedder=embedder,
                                 exclude_session='session-a')['packet']['items'], [])

    def test_memory_off_skips_lookup_and_stale_candidates_are_dropped(self):
        with patch('memory_search.retrieve', side_effect=AssertionError('must not search')):
            self.assertEqual(retrieve(self.store, self.owner, 'astronomy', use_memory=False)['status'], 'disabled')
        self.store.delete_source(self.owner, 'session-a')
        self.assertEqual(select(self.store, self.owner, [self.ref])['items'], [])

    def test_identity_link_change_and_packet_mutation_invalidate(self):
        from test_memory_identity import descriptor
        self.store.put_source(self.owner, source('identity', text='Maya enjoys swimming.'))
        self.store.commit_claims(self.store.claim_job(self.owner), [candidate(mention=descriptor())])
        ref = dict(session_id='identity', revision=1, passage_id='p1')
        packet = select(self.store, self.owner, [ref])
        claim = packet['items'][0]['lifecycle'][0]
        self.assertEqual(claim['identity_status'], 'unresolved')
        mention = self.store.identities.mentions(self.owner, claim['id'])[0]
        self.store.identities.link(self.owner, mention['id'],
                                  [dict(session='identity', revision=1, passage='p1')], rubric='fixture-v1')
        self.assertFalse(valid(self.store, self.owner, packet))
        packet = select(self.store, self.owner, [ref])
        self.assertEqual(packet['items'][0]['lifecycle'][0]['identity_status'], 'established')
        packet['items'][0]['text'] = 'Unsupported content'
        self.assertFalse(valid(self.store, self.owner, packet))
