import tempfile
from pathlib import Path
import unittest
from admission import Admission, Rejected
from memory_store import MemoryStore
from memory_models import extraction_request, parse_candidates, support_request, judgment_request, parse_judgments, parse_support
from memory_writer import select_claims
from profile_budget import ProfileBudget, provision, ALLOCATION, PER_CALL
from test_memory import source
from test_memory_learning import memory, answers


class ProfileContractTests(unittest.TestCase):
    def test_identity_metadata_and_independent_judgment(self):
        note = dict(source(text='My daughter Maya swims. I enjoy walking.'),origin='personal_text')
        user = memory('The user enjoys walking.', 'user', subject_scope='user',subject_relation=None)
        daughter = memory("The user's daughter Maya swims.", 'Maya',subject_scope='related',subject_relation='daughter')
        candidates = parse_candidates({'memories':[user,daughter]},note)
        self.assertIn('subject_scope',extraction_request(note)['text']['format']['schema']['properties']['memories']['items']['required'])
        request = support_request(note,candidates)
        self.assertEqual(request['state']['author_identity'],'authenticated_user_personal_note')
        supported = parse_support(answers(request),request)
        request = judgment_request(note,candidates,[[],[]])
        judgments = parse_judgments(answers(request,{'attribution_0':'user','attribution_1':'related'}),request)
        claims,_ = select_claims(note,candidates,judgments,[[],[]],supported)
        self.assertEqual(claims[0]['subject'],'user')
        self.assertTrue(claims[1]['profile_link'])
        self.assertNotEqual(claims[1]['subject'],'user')
        judgments['attribution_0'] = answers(request,{'attribution_0':'wrong'})['answers']['attribution_0']
        claims,_ = select_claims(note,candidates,judgments,[[],[]],supported)
        self.assertEqual(len(claims),1)

    def test_live_support_regression_preserves_people_and_quotes(self):
        import json
        fixture=json.loads((Path(__file__).parents[1]/'Fixtures/personal-support-provider-response.json').read_text())
        self.assertEqual(parse_support(fixture['response']['data'],fixture['request']),
                         ['unsupported','unsupported','supported','supported'])

    def test_older_correction_target_survives_unrelated_recent_facts(self):
        from profile_identity import rank_related
        old = {'text':'The user prefers quiet mornings.'}
        pool = [{'text':f'The user likes hobby {i}.'} for i in range(8)] + [old]
        self.assertIs(rank_related({'text':'The user now prefers lively mornings.'},pool)[0],old)

    def test_legacy_source_cannot_claim_personal_schema_and_learning_is_opt_in(self):
        user = memory('The user enjoys walking.','user',subject_scope='user',subject_relation=None)
        with self.assertRaises(Rejected): parse_candidates({'memories':[user]},source())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'memory.sqlite'
            store = MemoryStore(path)
            owner = store.owner_for('test')
            store.put_source(owner,dict(source(),origin='personal_text'))
            self.assertIsNone(store.claim_job(owner))
            enabled = MemoryStore(path,personal_learning=True)
            # Enabling does not silently backfill held notes.
            self.assertIsNone(enabled.claim_job(owner))
            enabled.put_source(owner,dict(source('new'),origin='personal_text'))
            self.assertIsNotNone(enabled.claim_job(owner))


class ProfileBudgetTests(unittest.TestCase):
    def test_aggregate_cap_idempotence_and_no_automatic_refill(self):
        with tempfile.TemporaryDirectory() as folder:
            global_path, memory_path = (Path(folder)/n for n in ('usage.sqlite','memory-budget.sqlite'))
            admission=Admission(global_path,total_microusd=5_000_000,limits={'ask':(2_500_000,3000,20)})
            self.addCleanup(admission.close)
            admission.enroll()
            provision(global_path,memory_path); provision(global_path,memory_path)
            budget=ProfileBudget(memory_path)
            for i in range(ALLOCATION//PER_CALL):
                budget.reserve(str(i), ('gpt-6-luna','jev-1.13.0')[i%2]);budget.finish(str(i),{})
            provision(global_path,memory_path)
            with self.assertRaisesRegex(Rejected,'profile_budget_limit'): budget.reserve('overflow','gpt-6-luna')
            with self.assertRaisesRegex(Rejected,'paid_retry'): budget.reserve('0','jev-1.13.0')
            with self.assertRaisesRegex(Rejected,'unapproved'): budget.reserve('other','other')
            self.assertEqual(sum(r['reserved_microusd'] for r in budget.report()),ALLOCATION)
            self.assertEqual(len(admission.usage()),1)


class ProfileWriterTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_writer_updates_user_and_keeps_related_people_separate(self):
        from memory_models import MemoryModels
        from memory_writer import MemoryWriter
        with tempfile.TemporaryDirectory() as folder:
            store=MemoryStore(Path(folder)/'memory.sqlite',personal_learning=True,clock=lambda:200.)
            owner=store.owner_for('fixture')
            candidates=[memory('The user prefers quiet mornings.','user',subject_scope='user',subject_relation=None),
                        memory("The user's daughter Maya enjoys swimming.",'Maya',subject_scope='related',subject_relation='daughter')]
            class LocalBudget:
                def reserve(self,*args): pass
                def finish(self,*args): pass
            correcting=False
            async def extract(request): return {'data':{'memories':candidates},'usage':{}}
            async def judge(request):
                choices={}
                for key in request['questions']:
                    if key.startswith('attribution'): choices[key]='user' if key.endswith('_0') else 'related'
                    if correcting and key=='relation_0': choices[key]='update_0'
                return {'data':answers(request,choices),'usage':{}}
            writer=MemoryWriter(store,MemoryModels('unused','unused',luna_call=extract,jev_call=judge),LocalBudget())
            store.put_source(owner,dict(source('first'),origin='personal_text'))
            self.assertEqual((await writer.process_next(owner))['accepted'],2)
            self.assertEqual(len(store.profile(owner)),2)
            candidates=[dict(candidates[0],text='The user now prefers lively mornings.')]
            correcting=True
            store.put_source(owner,dict(source('second'),origin='personal_text',captured_at=150.))
            self.assertEqual((await writer.process_next(owner))['accepted'],1)
            self.assertEqual(len(store.profile(owner)),2)
            self.assertFalse(any('quiet' in c['text'] for c in store.profile(owner)))
            self.assertIsNone(await writer.process_next(owner))
            store.delete_source(owner,'second')
            self.assertFalse(any(c['subject']=='user' for c in store.profile(owner)))

if __name__=='__main__': unittest.main()
