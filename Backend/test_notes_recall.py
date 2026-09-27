import test_indexed_recall
from memory_models import JEV
from notes_recall import NotesFirstRecall,collect
from recording_notes import RecordingNotes
from test_memory import source
from test_ask import QUESTION
from admission import Rejected


class Judge:
    async def judge(self,request):
        return dict(usage={},data=dict(model=JEV,answers={key:dict(type='choice',choice='helpful',confidence=1.,
            probabilities={name:float(name=='helpful') for name in q['criteria']}) for key,q in request['questions'].items()}))


class NotesRecallTests(test_indexed_recall.IndexedRecallTests):
    def setUp(self):
        super().setUp();self.recall=NotesFirstRecall(self.store,Judge(),self.budget)

    def add_note(self):
        self.store.put_source(self.owner,source(text='Cedar meets at the garden pavilion.'))
        notes=RecordingNotes(self.store);notes.enqueue(self.owner,'session-a',1)
        notes.complete(notes.claim(self.owner,'session-a'),dict(title='Cedar',
            overview=dict(text='Cedar meets at the garden pavilion.',passages=['p1']),sections=[]))

    async def test_notes_resolve_to_original_evidence_and_revalidate(self):
        self.add_note()
        manifest=await self.recall.prepare('qa',dict(QUESTION,question='Where does Cedar meet?'))
        self.assertTrue(manifest['notes']);self.assertEqual(self.budget.calls,1)
        self.assertTrue(all(s['evidence_type']=='original_source' for s in manifest['sources']))
        await self.recall.validate(manifest)
        with self.store.transaction() as db:db.execute("UPDATE recording_notes SET state='outdated'")
        with self.assertRaisesRegex(Rejected,'memory_context_changed'):await self.recall.validate(manifest)

    async def test_omitted_detail_uses_transcript_without_notes(self):
        self.add_note()
        self.store.put_source(self.owner,source('detail',text='The access code is 4821.'))
        manifest=await self.recall.prepare('qa',dict(QUESTION,question='What is the access code?'))
        self.assertTrue(any('4821' in s['text'] for s in manifest['sources']))

    async def test_mutation_during_judgment_never_rehydrates_as_new_evidence(self):
        self.add_note();parent=self
        class Mutating(Judge):
            async def judge(self,request):
                parent.store.delete_source(parent.owner,'session-a')
                return await super().judge(request)
        self.recall.models=Mutating()
        with self.assertRaisesRegex(Rejected,'memory_context_changed'):
            await self.recall.prepare('qa',dict(QUESTION,question='Where does Cedar meet?'))

    async def test_provider_error_does_not_retry(self):
        self.add_note()
        class Failure:
            async def judge(self,request):raise RuntimeError('provider unavailable')
        self.recall.models=Failure()
        with self.assertRaisesRegex(RuntimeError,'provider unavailable'):
            await self.recall.prepare('qa',dict(QUESTION,question='Cedar'))
        self.assertEqual(self.budget.calls,1)

    def test_pool_is_bounded_and_unknown_speakers_do_not_become_profile(self):
        self.add_note()
        pool=collect(self.store,self.owner,'Cedar')
        self.assertLessEqual(len(pool),12)
        self.assertFalse(any(c['kind']=='personal' for c in pool))

    def test_long_transcript_window_preserves_original_offsets(self):
        text='padding '*400+'access code is 4821. '+'ending '*400
        self.store.put_source(self.owner,source(text=text))
        pool=collect(self.store,self.owner,'access code')
        self.assertTrue(pool)
        item=pool[0]['packet']['items'][0]
        self.assertIn('4821',item['text'])
        self.assertEqual(item['text'],text[item['text_start']:item['text_end']])
        self.assertLessEqual(len(pool[0]['text']),1800)

    def test_notes_recall_flag_requires_dependencies(self):
        from hosted import notes_recall_setting
        self.assertFalse(notes_recall_setting({}))
        with self.assertRaises(ValueError):notes_recall_setting({'VOICE_ENABLE_NOTES_RECALL':'1'})
        env={key:'1' for key in ('VOICE_ENABLE_NOTES_RECALL','VOICE_ENABLE_RECORDING_NOTES','VOICE_ENABLE_MEMORY_REWORK','VOICE_ENABLE_MEMORY_RECALL','VOICE_ENABLE_INDEPENDENT_VERIFICATION')}
        self.assertTrue(notes_recall_setting(env))


import test_companion_runtime

class NotesRuntimeTests(test_companion_runtime.RuntimeTests):
    notes_recall=True
