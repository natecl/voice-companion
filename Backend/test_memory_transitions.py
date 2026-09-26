"""Accepted fixture judgments through real storage; no model-quality claim."""
import tempfile
from pathlib import Path
import unittest

from admission import Rejected
from memory_store import MemoryStore
from test_memory import source, candidate
from test_memory_identity import descriptor


class TransitionTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)/'memory.sqlite'
        self.store = MemoryStore(self.path, clock=lambda:300.)
        self.owner = self.store.owner_for('test-owner')
        self.old = self.write('old', 'Maya enjoys swimming.', 100.)
        self.new = self.write('new', 'Maya now enjoys tennis instead.', 200.)
        self.store.put_source(self.owner, source('bridge', text='These references concern the same Maya.'))
        self.store.commit_claims(self.store.claim_job(self.owner), [])
        self.anchor = self.store.identities.link(self.owner, self.mention(self.old), [self.ref('old')], rubric='fixture')
        self.link_new()

    def ref(self, session):
        return dict(session=session, revision=1, passage='p1')

    def write(self, session, text, time):
        self.store.put_source(self.owner, dict(source(session, text=text), captured_at=time))
        claim = dict(candidate(text), mention=descriptor(), valid_from=time)
        self.store.commit_claims(self.store.claim_job(self.owner), [claim])
        return next(c['id'] for c in self.store.search(self.owner) if c['text']==text)

    def mention(self, claim):
        return self.store.identities.mentions(self.owner, claim)[0]['id']

    def link_new(self, bridge='bridge'):
        return self.store.identities.link(self.owner, self.mention(self.new),
            [self.ref('old'),self.ref('new'),self.ref(bridge)], rubric='fixture', anchor=self.anchor['id'])

    def states(self):
        with self.store.connect() as db:
            return {r['id']:r['state'] for r in db.execute('SELECT id,state FROM claim WHERE owner=?',(self.owner,))}

    def apply(self, incoming=None, target=None):
        incoming, target = incoming or self.new, target or self.old
        prepared = self.store.transitions.prepare_correction(self.owner, incoming, target)
        return self.store.transitions.apply_correction(self.owner, incoming, target, evidence_token=prepared['token'], rubric='fixture-v1')

    def test_correction_persists_history_and_idempotent_decision(self):
        result = self.apply()
        self.assertEqual(self.states(), {self.old:'superseded',self.new:'active'})
        self.assertEqual(len(self.store.search(self.owner)), 1)
        again = self.store.transitions.apply_correction(self.owner,self.new,self.old,
            evidence_token=result['evidence_token'],rubric='fixture-v1')
        self.assertEqual(result, again)
        self.store = MemoryStore(self.path)
        self.assertEqual(self.states()[self.old], 'superseded')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_correction').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM memory_correction_link').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT count(*) FROM support').fetchone()[0],2)

    def test_deleted_bridge_reopens_both_claims_without_current_resurrection(self):
        decision = self.apply()
        self.store.delete_source(self.owner,'bridge')
        self.assertEqual(self.states(),{self.old:'unresolved',self.new:'unresolved'})
        self.assertEqual(self.store.search(self.owner),[])
        proposals = self.store.search(self.owner,unresolved_only=True)
        self.assertIn(self.old,next(c['proposed_targets'] for c in proposals if c['id']==self.new))
        with self.assertRaisesRegex(Rejected,'stale_correction_decision'):
            self.store.transitions.apply_correction(self.owner,self.new,self.old,
                evidence_token=decision['evidence_token'],rubric='fixture-v1')

    def test_changed_source_scrubs_fact_but_does_not_restore_old_preference(self):
        self.apply()
        self.store.put_source(self.owner,source('new',revision=2,text='A revised recording.'))
        self.assertEqual(self.states(),{self.old:'unresolved',self.new:'invalid'})
        self.assertEqual(self.store.search(self.owner),[])
        with self.store.connect() as db:
            self.assertIsNone(db.execute('SELECT text FROM claim WHERE id=?',(self.new,)).fetchone()[0])

    def test_connected_correction_chain_reopens_conservatively(self):
        self.apply()
        latest = self.write('latest','Maya now enjoys cycling.',250.)
        self.store.identities.link(self.owner,self.mention(latest),[self.ref('latest'),self.ref('old')],rubric='fixture',anchor=self.anchor['id'])
        self.apply(latest,self.new)
        self.assertEqual(self.states()[latest],'active')
        self.store.delete_source(self.owner,'bridge')
        self.assertEqual(set(self.states().values()),{'unresolved'})
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM memory_correction WHERE state='reopened'").fetchone()[0],2)

    def test_new_evidence_allows_explicit_review_but_never_auto_reapplies(self):
        self.apply()
        self.store.delete_source(self.owner,'bridge')
        self.store.put_source(self.owner,source('replacement-bridge'))
        self.link_new('replacement-bridge')
        self.assertEqual(set(self.states().values()),{'unresolved'})
        self.apply()
        self.assertEqual(self.states(),{self.old:'superseded',self.new:'active'})

    def test_stale_prepared_decision_rejected_atomically(self):
        prepared = self.store.transitions.prepare_correction(self.owner,self.new,self.old)
        self.store.delete_source(self.owner,'bridge')
        before=self.states()
        with self.assertRaises(Rejected):
            self.store.transitions.apply_correction(self.owner,self.new,self.old,evidence_token=prepared['token'],rubric='fixture')
        self.assertEqual(self.states(),before)
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_correction').fetchone()[0],0)

    def test_different_owner_identity_and_legacy_subject_rejected(self):
        foreign=self.store.owner_for('other')
        with self.assertRaisesRegex(Rejected,'stale_correction_claim'):
            self.store.transitions.prepare_correction(foreign,self.new,self.old)
        different=self.write('other','Another Maya likes hiking.',250.)
        self.store.identities.link(self.owner,self.mention(different),[self.ref('other')],rubric='fixture')
        with self.assertRaisesRegex(Rejected,'different_correction_identity'):
            self.store.transitions.prepare_correction(self.owner,different,self.old)
        self.store.put_source(self.owner,source('legacy'))
        self.store.commit_claims(self.store.claim_job(self.owner),[candidate('Legacy fact')])
        legacy=next(c for c in self.store.search(self.owner) if c['text']=='Legacy fact')
        with self.assertRaisesRegex(Rejected,'unresolved_correction_identity'):
            self.store.transitions.prepare_correction(self.owner,legacy['id'],self.old)

    def test_unrelated_source_change_does_not_reopen_valid_correction(self):
        self.apply()
        self.store.put_source(self.owner, source('unrelated'))
        self.store.delete_source(self.owner, 'unrelated')
        self.assertEqual(self.states(), {self.old:'superseded', self.new:'active'})

    def test_changed_support_invalidates_prepared_token_without_partial_write(self):
        prepared = self.store.transitions.prepare_correction(self.owner, self.new, self.old)
        self.store.put_source(self.owner, source('duplicate'))
        self.store.commit_claims(self.store.claim_job(self.owner), [dict(
            candidate('Maya enjoys swimming.'), relation='duplicate', target=self.old)])
        before = self.states()
        with self.assertRaisesRegex(Rejected, 'stale_correction_decision'):
            self.store.transitions.apply_correction(self.owner, self.new, self.old,
                evidence_token=prepared['token'], rubric='fixture')
        self.assertEqual(before, self.states())
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_correction').fetchone()[0], 0)

    def test_migration_v5_preserves_identity_links_and_tombstones(self):
        self.store.delete_source(self.owner,'deleted')
        with self.store.connect() as db:
            db.execute('DROP TABLE memory_correction_link')
            db.execute('DROP TABLE memory_correction')
            db.execute('DROP TABLE IF EXISTS memory_embedding');db.execute('DROP TABLE IF EXISTS memory_passage_index');db.execute('PRAGMA user_version=5')
        self.store=MemoryStore(self.path,clock=lambda:300.)
        self.assertEqual(self.store.owner_for('test-owner'),self.owner)
        self.apply()
        self.assertEqual(self.store.put_source(self.owner,source('deleted'))['status'],'deleted')
        with self.store.connect() as db:
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],17)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(db.execute('PRAGMA foreign_key_check').fetchall(),[])


if __name__=='__main__': unittest.main()
