import json
import tempfile
from pathlib import Path
import unittest
from admission import Rejected
from memory_store import MemoryStore
from memory_recall import MemoryRecall, combined_shortlist, model_source
from test_memory import source, candidate
from test_memory_recall import Judge, Budget
from test_ask import QUESTION


class ProfileRecallTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=MemoryStore(Path(self.temp.name)/'memory.sqlite',clock=lambda:200.,personal_learning=True,personal_recall=True)
        self.owner=self.store.owner_for('credential')
        self.budget=Budget()
        self.recall=MemoryRecall(self.store,Judge(),self.budget)

    def write(self, name, text, claims):
        self.store.put_source(self.owner,dict(source(name,text=text),origin='personal_text'))
        self.store.commit_claims(self.store.claim_job(self.owner),claims)

    async def test_paraphrase_candidate_survives_recent_conversation_noise(self):
        self.write('personal','I enjoy drawing birds.',[dict(candidate(),text='The user enjoys drawing birds.',subject='user',kind='fact')])
        for i in range(20):
            self.store.put_source(self.owner,dict(source(f'noise-{i}',text='Work schedule agenda updates.'),captured_at=190.))
        candidates=combined_shortlist(self.store.recall_snapshot(self.owner),dict(QUESTION,question='Suggest a relaxing creative activity.'))
        self.assertTrue(any('birds' in c['text'] for c in candidates))
        self.assertLessEqual(len(candidates),12)

    async def test_retired_fact_cannot_leak_through_original_note(self):
        self.write('old','I prefer quiet mornings. My daughter Maya swims.',
                   [dict(candidate(),text='The user prefers quiet mornings.',subject='user',kind='preference'),
                    dict(candidate(),text="The user's daughter Maya swims.",subject='maya',profile_link=True,kind='fact')])
        prior=next(c for c in self.store.profile(self.owner) if c['subject']=='user')
        self.write('new','Correction: I prefer lively mornings.',
                   [dict(candidate(),text='The user prefers lively mornings.',subject='user',kind='preference',relation='supersedes',target=prior['id'])])
        manifest=await self.recall.prepare('credential',dict(QUESTION,question='What does my daughter enjoy?'))
        selected=[model_source(c) for c in manifest['sources']]
        self.assertNotIn('quiet',json.dumps(selected))
        self.assertTrue(any('quiet' in c.get('source_text','') for c in manifest['sources']))
        self.store.delete_source(self.owner,'old')
        with self.assertRaisesRegex(Rejected,'memory_context_changed'):await self.recall.validate(manifest)
        self.assertFalse(any(c['session_id']=='old' for c in combined_shortlist(self.store.recall_snapshot(self.owner),QUESTION)))

    async def test_history_and_owner_scope(self):
        self.write('old','I preferred quiet mornings.',[dict(candidate(),text='The user preferred quiet mornings.',subject='user',kind='preference',valid_until=150.)])
        current=await self.recall.prepare('credential',QUESTION)
        self.assertEqual(current['sources'],[])
        history=await self.recall.prepare('credential',dict(QUESTION,question='What was my previous preference?'))
        self.assertEqual(history['sources'][0]['use'],'historical')
        self.assertEqual((await self.recall.prepare('other',QUESTION))['sources'],[])

if __name__=='__main__':unittest.main()
