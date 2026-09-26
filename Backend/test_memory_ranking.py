import json
from pathlib import Path
import unittest
from admission import Rejected
from memory_models import JEV
from memory_ranking import request, order


class RankingTests(unittest.TestCase):
    def test_recorded_role_retains_order_and_none_alternative(self):
        root=Path(__file__).parent/'fixtures'
        saved=json.loads((root/'memory_reranking/jev-role.json').read_text())
        positives=json.loads((root/'memory_semantic/cases.json').read_text())
        cases=json.loads((root/'memory_reranking/cases.json').read_text())
        texts=[case['text'] for case in positives]+cases['distractors']
        queries=[case['query'] for case in positives]+cases['irrelevant_queries']
        for i,query in enumerate(queries):
            req=request(query,texts)
            self.assertEqual(req['questions']['ranking'],saved['request']['questions'][f'q{i}'])
            response=dict(model=JEV,answers={'ranking':saved['response']['data']['answers'][f'q{i}']})
            ranked=order(response,req)
            self.assertEqual(ranked['order'][0],f'p{i}' if i<6 else 'none')
            self.assertEqual(len(ranked['order']),13)

    def test_invalid_or_oversized_input_is_explicit(self):
        for query,texts in [('', ['text']),('query',[]),('query',['x']*13),('query',['x'*2001])]:
            with self.assertRaises(Rejected):request(query,texts)


class RankingIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_store_to_ranker_with_recorded_judgment(self):
        import tempfile
        from memory_store import MemoryStore
        from memory_context import select,valid
        from memory_ranking import MemoryRanker
        from test_memory import source
        saved=json.loads((Path(__file__).parent/'fixtures/memory_reranking/jev-role.json').read_text())
        for case in ('q0','q6'):
            with tempfile.TemporaryDirectory() as directory:
                store=MemoryStore(Path(directory)/'memory.sqlite');owner=store.owner_for('qa')
                question=saved['request']['questions'][case]
                refs=[]
                for name,text in question['instructions']['passages'].items():
                    store.put_source(owner,source(name,text=text))
                    refs.append(dict(session_id=name,revision=1,passage_id='p1'))
                packet=select(store,owner,refs)
                calls=[]
                class Budget:
                    def reserve(self,*args):calls.append('reserve')
                    def finish(self,*args):pass
                class Models:
                    async def judge(self,req):
                        assert req['questions']['ranking']==question
                        return dict(data=dict(model=JEV,answers={'ranking':saved['response']['data']['answers'][case]}),usage={})
                ranker=MemoryRanker(store,Models(),Budget())
                result=await ranker.prepare(owner,question['instructions']['query'],packet)
                self.assertTrue(valid(store,owner,result['packet']))
                self.assertEqual(result['status'],'available' if case=='q0' else 'no_match')
                self.assertEqual(len(calls),1)
                if case=='q0':self.assertEqual(result['packet']['items'][0]['session_id'],'p0')
                else:self.assertEqual(result['packet']['items'],[])

    async def test_delete_during_judgment_cannot_return_selected_evidence(self):
        import tempfile
        from memory_store import MemoryStore
        from memory_context import select
        from memory_ranking import MemoryRanker
        from test_memory import source
        with tempfile.TemporaryDirectory() as directory:
            store=MemoryStore(Path(directory)/'memory.sqlite');owner=store.owner_for('qa')
            store.put_source(owner,source())
            packet=select(store,owner,[dict(session_id='session-a',revision=1,passage_id='p1')])
            class Budget:
                def reserve(self,*args):pass
                def finish(self,*args):pass
            class Models:
                async def judge(self,req):
                    store.delete_source(owner,'session-a')
                    return dict(data=dict(model=JEV,answers={'ranking':dict(type='choice',choice='p0',probabilities={'p0':1.,'none':0.},confidence=1.)}),usage={})
            with self.assertRaisesRegex(Rejected,'memory_context_changed'):
                await MemoryRanker(store,Models(),Budget()).prepare(owner,'appointment',packet)
