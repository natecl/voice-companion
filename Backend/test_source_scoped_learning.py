"""Source-scoped learning exercises the real store with controlled model decisions."""
import unittest
import test_memory_evidence_writer as baseline
from test_memory import source
from test_memory_learning import answers
from admission import Rejected


class SourceScopedTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        baseline.EvidenceWriterTests.setUp(self)
        self.writer.source_scoped=True

    run_source=baseline.EvidenceWriterTests.run_source
    # Reuse behavioral guards, not the old pipeline's ordered-call replay tests.
    test_full_writer_correction_and_distinct_person=baseline.EvidenceWriterTests.test_full_writer_correction_and_distinct_person
    test_same_source_correction_is_atomic_and_uses_pending_evidence=baseline.EvidenceWriterTests.test_same_source_correction_is_atomic_and_uses_pending_evidence
    test_uncertain_identity_preserves_unresolved_without_overwrite=baseline.EvidenceWriterTests.test_uncertain_identity_preserves_unresolved_without_overwrite
    test_source_deleted_after_judgment_never_commits=baseline.EvidenceWriterTests.test_source_deleted_after_judgment_never_commits
    test_same_source_chain_does_not_correct_already_replaced_fact_twice=baseline.EvidenceWriterTests.test_same_source_chain_does_not_correct_already_replaced_fact_twice
    test_supported_fact_survives_uncertain_attribution_without_profile_or_identity=baseline.EvidenceWriterTests.test_supported_fact_survives_uncertain_attribution_without_profile_or_identity
    test_completed_change_requires_independent_current_applicability=baseline.EvidenceWriterTests.test_completed_change_requires_independent_current_applicability
    test_historical_future_and_uncertain_changes_do_not_replace_current_fact=baseline.EvidenceWriterTests.test_historical_future_and_uncertain_changes_do_not_replace_current_fact
    test_correction_chain_can_cross_event_and_current_fact_wording=baseline.EvidenceWriterTests.test_correction_chain_can_cross_event_and_current_fact_wording

    async def test_compatible_facts_skip_cross_source_identity(self):
        await self.run_source('one',[baseline.proposal('My daughter Maya enjoys swimming.')])
        await self.run_source('two',[baseline.proposal('My daughter Maya likes apples.')])
        rows=self.store.search(self.owner)
        self.assertEqual(len(rows),2)
        self.assertNotEqual(rows[0]['entity_id'],rows[1]['entity_id'])
        self.assertEqual(self.calls,['extract','judge','extract','judge','judge'])
        self.assertTrue(all(r['profile_link'] for r in rows))

    async def test_uncertain_change_still_checks_prior_context(self):
        await self.run_source('one',[baseline.proposal('My daughter Maya enjoys swimming.')])
        normal=self.writer.models.judge
        async def uncertain(request):
            if any('replacement' in q['criteria'] for q in request['questions'].values()):
                return dict(data=answers(request,{k:'uncertain' for k in request['questions']}),usage={})
            return await normal(request)
        self.writer.models.judge=uncertain
        p=baseline.proposal('My daughter Maya might prefer tennis now.');p['change']['kind']='uncertain'
        await self.run_source('two',[p])
        self.assertEqual(len(self.store.search(self.owner)),1)
        self.assertEqual(len(self.store.search(self.owner,unresolved_only=True)),1)

    async def test_changed_fact_can_correct_target_without_linking_unrelated_property(self):
        await self.run_source('one',[baseline.proposal('My daughter Maya enjoys swimming.'),
                                     baseline.proposal('My daughter Maya likes apples.')])
        normal=self.writer.models.judge
        async def specific_relation(request):
            if any('replacement' in q['criteria'] for q in request['questions'].values()):
                labels={k:('addition' if 'apples' in request['state']['pairs'][k]['previous']['claim'] else 'replacement') for k in request['questions']}
                return dict(data=answers(request,labels),usage={})
            return await normal(request)
        self.writer.models.judge=specific_relation
        await self.run_source('two',[baseline.proposal('My daughter Maya now enjoys tennis instead of swimming.','correction')])
        rows=self.store.search(self.owner,historical=True)
        self.assertEqual(next(r for r in rows if r['text']=='My daughter Maya enjoys swimming.')['state'],'superseded')
        self.assertEqual(next(r for r in rows if 'apples' in r['text'])['state'],'active')
        self.assertEqual(next(r for r in rows if 'tennis' in r['text'])['state'],'active')

    async def test_compatible_cross_role_facts_remain_separate(self):
        await self.run_source('one',[baseline.proposal('My daughter Maya enjoys swimming.')])
        p=baseline.proposal('My colleague Maya also enjoys tennis.');p['mention']['relationship']='colleague'
        await self.run_source('two',[p])
        rows=self.store.search(self.owner)
        self.assertEqual(len(rows),2)
        self.assertNotEqual(rows[0]['entity_id'],rows[1]['entity_id'])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM memory_correction').fetchone()[0],0)
