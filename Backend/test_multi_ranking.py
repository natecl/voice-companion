import json
from pathlib import Path
import unittest
from memory_models import JEV
from memory_multi_ranking import request,order
from admission import Rejected


class MultiRankingTests(unittest.TestCase):
    def test_independent_scores_can_select_two_sources_without_truth_threshold(self):
        req=request('Compare their hobbies',['Lena plays violin.','Marco plays soccer.','A sports catalog.'])
        answers={}
        for key in req['questions']:
            helpful=key!='p2'
            answers[key]=dict(type='choice',choice='helpful' if helpful else 'topical',confidence=.7,
                              probabilities=dict(helpful=.7 if helpful else .2,topical=.2 if helpful else .7,unrelated=.1))
        ranked=order(dict(model=JEV,answers=answers),req)
        self.assertEqual(ranked['order'],['p0','p1','none','p2'])
        self.assertEqual(len(ranked['judgments']),3)

    def test_limits_and_schema_reject_invalid_results(self):
        with self.assertRaises(Rejected):request('question',['x']*13)
        with self.assertRaises(Rejected):request('question',['x'*2001])
        with self.assertRaises(Rejected):order(dict(model=JEV,answers={}),request('question',['text']))


class MultiRankingIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_two_original_sources_reach_selected_context(self):
        import tempfile
        from memory_store import MemoryStore
        from memory_context import select,valid
        from memory_ranking import MemoryRanker
        from test_memory import source
        with tempfile.TemporaryDirectory() as directory:
            store=MemoryStore(Path(directory)/'memory.sqlite');owner=store.owner_for('qa')
            refs=[]
            for i,text in enumerate(['Lena plays violin.','Marco plays soccer.','A sports catalog.']):
                store.put_source(owner,source(f's{i}',text=text))
                refs.append(dict(session_id=f's{i}',revision=1,passage_id='p1'))
            class Budget:
                def reserve(self,*args):pass
                def finish(self,*args):pass
            class Models:
                async def judge(self,req):
                    answers={key:dict(type='choice',choice='helpful' if key!='p2' else 'topical',confidence=1.,
                        probabilities=dict(helpful=float(key!='p2'),topical=float(key=='p2'),unrelated=0.)) for key in req['questions']}
                    return dict(data=dict(model=JEV,answers=answers),usage={})
            result=await MemoryRanker(store,Models(),Budget(),multi_source=True).prepare(owner,'Compare their hobbies',select(store,owner,refs))
            self.assertEqual([i['session_id'] for i in result['packet']['items']],['s0','s1'])
            self.assertTrue(valid(store,owner,result['packet']))

class RecordedRoleTests(unittest.TestCase):
    def test_frozen_and_heldout_selections_from_recorded_provider(self):
        root=Path(__file__).parent/'fixtures/multi_source'
        for name,cases_name in [('multisource-role-v4.json','cases.json'),('multisource-role-v4-heldout.json','heldout.json')]:
            saved=json.loads((root/name).read_text())
            for case in json.loads((root/cases_name).read_text()):
                with self.subTest(case=case['id']):
                    req=request(case['query'],case['texts'],case['id'])
                    self.assertEqual(req['state']['contexts'][case['id']],saved['request']['state']['contexts'][case['id']])
                    for key,value in req['questions'].items():
                        self.assertEqual(value,saved['request']['questions'][case['id']+'_'+key])
                    answers={key:saved['response']['data']['answers'][case['id']+'_'+key] for key in req['questions']}
                    ranked=order(dict(model=JEV,answers=answers),req)['order']
                    self.assertEqual(sorted(int(k[1:]) for k in ranked[:ranked.index('none')]),case['expected'])

# Exercise the unchanged real socket boundary with the new selection adapter:
# source citations, deletion while answering, and unavailable-memory handling.
from functools import partial
from unittest.mock import patch
import test_memory_recall
from indexed_recall import IndexedMemoryRecall

class MultiIndexedSocketTests(test_memory_recall.RecallAskTests):
    async def exercise(self, **kwargs):
        class Judge:
            async def judge(self,req):
                return dict(data=dict(model=JEV,answers={key:dict(type='choice',choice='helpful',confidence=1.,
                    probabilities=dict(helpful=1.,topical=0.,unrelated=0.)) for key in req['questions']}),usage={})
        with patch('test_memory_recall.MemoryRecall',partial(IndexedMemoryRecall,multi_source=True)), patch('test_memory_recall.Judge',Judge):
            return await super().exercise(**kwargs)
