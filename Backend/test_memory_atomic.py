import copy
import json
from pathlib import Path
import tempfile
import unittest
from admission import Rejected
import memory_atomic
import memory_evidence
from memory_store import MemoryStore
from test_memory import source


class AtomicTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.path=Path(folder.name)/'memory.sqlite'
        self.store=MemoryStore(self.path,personal_learning=True,clock=lambda:300.)
        self.owner=self.store.owner_for('owner')

    def prepare(self,session,text='My daughter Maya enjoys swimming.'):
        data=source(session,text=text);data['origin']='personal_text'
        self.store.put_source(self.owner,data);job=self.store.claim_job(self.owner)
        raw=dict(text=text,kind='preference',basis='stated',scope='related_to_author',
                 mention=dict(name='Maya',relationship='daughter',qualifiers=[],speaker_label=None),
                 evidence=[dict(passage='p1',quote=text)],time=dict(status='current',expression=None),
                 change=dict(kind='none',previous_text=None))
        p=memory_evidence.parse(dict(memories=[raw]),data)[0]
        return job,dict(proposal=p,action='new',rubric='fixture-accepted',judgments={'provenance':'fixture-only'})

    def seed(self):
        job,item=self.prepare('old');identifier=memory_atomic.commit(self.store,job,[item])[0]
        with self.store.connect() as db:
            anchor=dict(db.execute('SELECT * FROM memory_identity_link WHERE state=\'active\'').fetchone())
        return identifier,anchor

    def correction(self,old,anchor):
        job,item=self.prepare('new','My daughter Maya now enjoys tennis instead of swimming.')
        with self.store.connect() as db:token=memory_atomic.snapshot(db,self.owner,old)
        item.update(action='correct',target=old,snapshots={old:token},anchor=anchor['id'],
                    anchor_refs=[dict(session='old',revision=1,passage='p1')])
        return job,item

    def test_fact_identity_and_correction_commit_together_and_survive_reopen(self):
        old,anchor=self.seed();job,item=self.correction(old,anchor)
        new=memory_atomic.commit(self.store,job,[item])[0]
        reopened=MemoryStore(self.path)
        rows={r['id']:r for r in reopened.search(self.owner,historical=True)}
        self.assertEqual(rows[old]['state'],'superseded');self.assertEqual(rows[new]['state'],'active')
        self.assertEqual(rows[new]['entity_id'],rows[old]['entity_id'])
        with reopened.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_fact_evidence').fetchone()[0],2)
            self.assertEqual(db.execute('SELECT state FROM job WHERE id=?',(job['id'],)).fetchone()[0],'done')
            self.assertEqual(db.execute('SELECT state FROM memory_correction').fetchone()[0],'active')

    def test_late_identity_failure_rolls_back_entire_fact_batch(self):
        old,anchor=self.seed();job,item=self.correction(old,anchor)
        item['anchor']='missing-anchor'
        with self.assertRaisesRegex(Rejected,'stale_identity_anchor'):memory_atomic.commit(self.store,job,[item])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM claim').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM memory_mention').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT count(*) FROM memory_fact_evidence').fetchone()[0],1)
            self.assertEqual(db.execute('SELECT state FROM job WHERE id=?',(job['id'],)).fetchone()[0],'running')

    def test_changed_prior_evidence_rejects_stale_semantic_decision(self):
        old,anchor=self.seed();job,item=self.correction(old,anchor)
        with self.store.transaction() as db:db.execute("UPDATE claim SET state='unresolved' WHERE id=?",(old,))
        with self.assertRaisesRegex(Rejected,'stale_relation_target'):memory_atomic.commit(self.store,job,[item])
        with self.store.connect() as db:self.assertEqual(db.execute('SELECT count(*) FROM claim').fetchone()[0],1)

    def test_deletion_scrubs_metadata_and_reopens_dependent_correction(self):
        old,anchor=self.seed();job,item=self.correction(old,anchor)
        new=memory_atomic.commit(self.store,job,[item])[0]
        self.store.delete_source(self.owner,'old')
        with self.store.connect() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM memory_fact_evidence WHERE session='old'").fetchone()[0],0)
            self.assertEqual(db.execute('SELECT state FROM claim WHERE id=?',(new,)).fetchone()[0],'unresolved')

    def test_deleted_incoming_job_cannot_commit_late_result(self):
        job,item=self.prepare('incoming');self.store.delete_source(self.owner,'incoming')
        with self.assertRaisesRegex(Rejected,'stale_job'):memory_atomic.commit(self.store,job,[item])
        self.assertEqual(self.store.search(self.owner),[])

    def test_unresolved_or_past_proposal_is_not_current_profile_fact(self):
        job,item=self.prepare('past','My daughter Maya enjoyed swimming as a child.')
        item['proposal']['time']['status']='past'
        memory_atomic.commit(self.store,job,[item])
        self.assertEqual(self.store.search(self.owner),[])
        self.assertEqual(len(self.store.search(self.owner,unresolved_only=True)),1)

    def test_schema7_migration_adds_no_automatic_fact_metadata_or_jobs(self):
        self.seed()
        with self.store.connect() as db:
            db.execute('DROP TABLE memory_fact_evidence');db.execute('PRAGMA user_version=7')
        reopened=MemoryStore(self.path)
        with reopened.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_fact_evidence').fetchone()[0],0)
            self.assertEqual(db.execute('SELECT count(*) FROM claim').fetchone()[0],1)
            self.assertEqual(db.execute('PRAGMA user_version').fetchone()[0],8)
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone()[0],'ok')
        self.assertIsNone(reopened.claim_job(self.owner))
