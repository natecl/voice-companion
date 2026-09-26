import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from admission import Rejected
from indexed_recall import IndexedMemoryRecall,memory_disabled
from memory_store import MemoryStore
from memory_models import JEV
from test_memory import source,candidate
from test_ask import QUESTION
from test_memory_recall import Budget


class Judge:
    async def judge(self,req):
        q=req['questions']['ranking']
        return dict(data=dict(model=JEV,answers={'ranking':dict(type='choice',choice='p0',confidence=1.,
            probabilities={key:float(key=='p0') for key in q['criteria']})}),usage={})


class IndexedRecallTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.store=MemoryStore(Path(folder.name)/'memory.sqlite',clock=lambda:300.)
        self.owner=self.store.owner_for('qa');self.budget=Budget()
        self.recall=IndexedMemoryRecall(self.store,Judge(),self.budget)

    async def test_ask_compatible_sources_correction_and_selected_validation(self):
        self.store.put_source(self.owner,source('old',text='Maya enjoys swimming.'))
        self.store.commit_claims(self.store.claim_job(self.owner),[candidate('Maya enjoys swimming.')])
        old=self.store.search(self.owner)[0]['id']
        self.store.put_source(self.owner,source('new',text='Maya now enjoys tennis instead.'))
        self.store.commit_claims(self.store.claim_job(self.owner),[candidate('Maya enjoys tennis.',relation='supersedes',target=old)])
        manifest=await self.recall.prepare('qa',dict(QUESTION,question='What sport does Maya enjoy?',memory=True,session_id='now'))
        self.assertEqual({s['session_id'] for s in manifest['sources']},{'old','new'})
        self.assertEqual(manifest['coverage'],'partial')
        self.assertTrue(all(s['id'].startswith('m') for s in manifest['sources']))
        self.store.put_source(self.owner,source('unrelated',text='An unrelated new recording.'))
        await self.recall.validate(manifest)
        self.store.delete_source(self.owner,'new')
        with self.assertRaisesRegex(Rejected,'memory_context_changed'):await self.recall.validate(manifest)

    async def test_explicit_opt_out_precedes_all_retrieval(self):
        for query in ["Don't use my past notes. What time?",'Only use this transcript: what time?']:
            with patch.object(self.store,'owner_for',side_effect=AssertionError('must not look up')):
                result=await self.recall.prepare('qa',dict(QUESTION,question=query))
            self.assertEqual(result['status'],'disabled')
        self.assertEqual(self.budget.calls,0)
        self.assertFalse(memory_disabled(dict(QUESTION,question='He said do not use my past notes. What did he mean?')))

    async def test_empty_library_does_not_spend(self):
        result=await self.recall.prepare('qa',QUESTION)
        self.assertEqual(result['sources'],[]);self.assertEqual(self.budget.calls,0)

    async def test_joint_prompt_budget_cannot_drop_known_correction(self):
        self.store.put_source(self.owner,source(text='The appointment is at noon.'))
        huge=dict(QUESTION,passages=[dict(id='p1',start=0,text='x'*11000)])
        with self.assertRaisesRegex(Rejected,'recall_too_large'):await self.recall.prepare('qa',huge)

    def test_false_memory_flag_is_valid(self):
        from ask import validate_request
        data=dict(QUESTION,memory=False,session_id='now')
        self.assertEqual(validate_request(json.dumps(data)),data)


import test_memory_recall


class IndexedSocketTests(test_memory_recall.RecallAskTests):
    async def exercise(self, **kwargs):
        with patch('test_memory_recall.MemoryRecall',IndexedMemoryRecall), patch('test_memory_recall.Judge',Judge):
            return await super().exercise(**kwargs)
