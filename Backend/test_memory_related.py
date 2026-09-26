from pathlib import Path
import tempfile
import unittest
from admission import Rejected
from memory_store import MemoryStore
from memory_context import select, valid
from memory_related import expand
from test_memory import source,candidate


class RelatedTests(unittest.TestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.store=MemoryStore(Path(folder.name)/'memory.sqlite',clock=lambda:300.)
        self.owner=self.store.owner_for('qa')

    def write(self,session,text,**extra):
        self.store.put_source(self.owner,source(session,text=text))
        self.store.commit_claims(self.store.claim_job(self.owner),[candidate(text,**extra)])
        with self.store.connect() as db:
            return db.execute('SELECT claim FROM support WHERE owner=? AND session=?',(self.owner,session)).fetchone()[0]

    def packet(self,session):
        return select(self.store,self.owner,[dict(session_id=session,revision=1,passage_id='p1')])

    def test_old_match_brings_full_correction_chain_and_history(self):
        old=self.write('old','Swimming')
        middle=self.write('middle','Tennis',relation='supersedes',target=old)
        self.write('current','Cycling',relation='supersedes',target=middle)
        packet=expand(self.store,self.owner,self.packet('old'))
        self.assertEqual({i['session_id'] for i in packet['items']},{'old','middle','current'})
        self.assertEqual({i['text']:i['lifecycle'][0]['state'] for i in packet['items']},
                         {'Swimming':'superseded','Tennis':'superseded','Cycling':'active'})
        self.assertTrue(valid(self.store,self.owner,packet))
        self.assertEqual(len(expand(self.store,self.owner,self.packet('current'))['items']),3)

    def test_unresolved_change_is_included_without_promoting_it(self):
        old=self.write('old','Swimming')
        before=self.packet('old')
        self.write('uncertain','Maybe tennis',relation='unresolved',proposed_targets=[old])
        self.assertFalse(valid(self.store,self.owner,before))
        packet=expand(self.store,self.owner,self.packet('old'))
        self.assertEqual(len(packet['items']),2)
        self.assertEqual(next(i for i in packet['items'] if i['session_id']=='uncertain')['lifecycle'][0]['state'],'unresolved')
        self.store.delete_source(self.owner,'uncertain')
        self.assertFalse(valid(self.store,self.owner,packet))
        self.assertEqual(len(expand(self.store,self.owner,self.packet('old'))['items']),1)

    def test_overflow_is_explicit_and_no_other_owner_or_deleted_evidence(self):
        old=self.write('old','Swimming')
        self.write('new','Tennis',relation='supersedes',target=old)
        with self.assertRaisesRegex(Rejected,'related_context_too_large'):
            expand(self.store,self.owner,self.packet('old'),max_claims=1)
        with self.assertRaisesRegex(Rejected,'related_context_too_large'):
            expand(self.store,self.owner,self.packet('old'),max_items=1)
        with self.assertRaisesRegex(Rejected,'memory_context_changed'):
            expand(self.store,self.store.owner_for('other'),self.packet('old'))
        packet=self.packet('old');self.store.delete_source(self.owner,'old')
        with self.assertRaisesRegex(Rejected,'memory_context_changed'):expand(self.store,self.owner,packet)
        # Deleting the historical source must not poison the surviving correction.
        surviving=expand(self.store,self.owner,self.packet('new'))
        self.assertEqual([i['session_id'] for i in surviving['items']],['new'])

    def test_ranker_returns_correction_evidence_even_when_model_picks_old_match(self):
        import asyncio
        from memory_models import JEV
        from memory_ranking import MemoryRanker
        old=self.write('old','Swimming')
        self.write('new','Tennis',relation='supersedes',target=old)
        class Budget:
            def reserve(self,*args):pass
            def finish(self,*args):pass
        class Models:
            async def judge(self,req):
                return dict(data=dict(model=JEV,answers={'ranking':dict(type='choice',choice='p0',
                    probabilities={'p0':1.,'none':0.},confidence=1.)}),usage={})
        result=asyncio.run(MemoryRanker(self.store,Models(),Budget()).prepare(self.owner,'What sport?',self.packet('old')))
        self.assertEqual({i['session_id'] for i in result['packet']['items']},{'old','new'})
        self.assertTrue(valid(self.store,self.owner,result['packet']))
