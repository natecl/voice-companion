"""Regression cases for evidence discovery, not fresh provider quality evidence."""
from admission import Rejected
import test_notes_recall as baseline
from test_memory import source
from test_ask import QUESTION
from notes_recall import collect
from evaluate_notes_first import save_note


class UnifiedRecallTests(baseline.NotesRecallTests):
    async def test_competing_account_survives_bad_relevance_choice(self):
        texts=[('a','Leah: I think the Northstar picnic is at Riverside Park this Saturday.'),
               ('b','Amir: I heard the Northstar picnic would be at the botanical garden, but the organizer has not confirmed a venue.')]
        for session,text in texts:
            src=source(session,text=text);self.store.put_source(self.owner,src)
            save_note(self.store,self.owner,src,dict(title='Northstar picnic',overview=dict(text=text,passages=['p1']),sections=[]))
        class Misranking(baseline.Judge):
            async def judge(self,request):
                result=await super().judge(request)
                for key,text in request['state']['contexts']['main']['candidates'].items():
                    if 'Amir:' in text:
                        answer=result['data']['answers'][key];answer['choice']='unrelated'
                        answer['probabilities']={k:float(k=='unrelated') for k in answer['probabilities']}
                return result
        self.recall.models=Misranking()
        manifest=await self.recall.prepare('qa',dict(QUESTION,question='Where is the Northstar picnic definitely taking place?'))
        self.assertEqual({s['session_id'] for s in manifest['sources']},{'a','b'})
        self.assertEqual(len(manifest['sources']),2)
        self.assertTrue(any('not confirmed' in s['text'] for s in manifest['sources']))
        self.assertEqual(self.budget.calls,1)

    def test_duplicate_notes_do_not_multiply_ranking_candidates(self):
        src=source(text='Cedar meets at the garden pavilion.');self.store.put_source(self.owner,src)
        item=dict(text='Cedar meets at the garden pavilion.',passages=['p1'])
        save_note(self.store,self.owner,src,dict(title='Cedar',overview=item,sections=[dict(heading='Meeting',items=[item,item])]))
        pool=collect(self.store,self.owner,'Where does Cedar meet?')
        self.assertEqual(len(pool),1)
        self.assertEqual(pool[0]['text'],src['passages'][0]['text'])
        self.assertIn('note',pool[0]['kinds']);self.assertIn('transcript',pool[0]['kinds'])

    async def test_other_owner_and_attached_session_never_enter_context(self):
        self.add_note()
        other=self.store.owner_for('other')
        self.store.put_source(other,source('private',text='Cedar private secret.'))
        result=await self.recall.prepare('qa',dict(QUESTION,question='Cedar',session_id='session-a'))
        self.assertEqual(result['sources'],[])
        self.assertEqual(self.budget.calls,0)

    async def test_invalid_judgment_does_not_trigger_unranked_fallback(self):
        self.add_note()
        class Invalid:
            async def judge(self,request):return dict(data={},usage={})
        self.recall.models=Invalid()
        with self.assertRaisesRegex(Rejected,'invalid_judgment'):
            await self.recall.prepare('qa',dict(QUESTION,question='Cedar'))
        self.assertEqual(self.budget.calls,1)
