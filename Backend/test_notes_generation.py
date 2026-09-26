import asyncio
import unittest
from admission import Rejected
from notes_generation import NotesGenerator,request
from test_recording_notes import RecordingNotesTests,notes

class GenerationTests(RecordingNotesTests,unittest.IsolatedAsyncioTestCase):
    async def test_budget_failure_never_calls_provider(self):
        class Budget:
            def reserve(self,*args):raise Rejected('notes_budget_limit')
        async def provider(req):raise AssertionError('Unexpected provider call')
        self.notes.enqueue(self.owner,'session-a',1)
        with self.assertRaises(Rejected):await NotesGenerator(self.store,provider,Budget()).generate(self.owner,'session-a')
        self.assertEqual(self.notes.read(self.owner,'session-a')['error'],'budget_limit')

    async def test_invalid_output_and_cancelled_generation_fail_without_retry(self):
        for cancel in (False,True):
            self.setUp();self.notes.enqueue(self.owner,'session-a',1);calls=[]
            class Budget:
                def reserve(self,*args):calls.append('reserved')
                def finish(self,*args):calls.append('finished')
            async def provider(req):
                if cancel:raise asyncio.CancelledError()
                return dict(data={},usage={})
            with self.assertRaises((Rejected,asyncio.CancelledError)):
                await NotesGenerator(self.store,provider,Budget()).generate(self.owner,'session-a')
            self.assertEqual(calls,['reserved','finished'])
            self.assertEqual(self.notes.read(self.owner,'session-a')['state'],'failed')
            self.assertFalse(await NotesGenerator(self.store,provider,Budget()).generate(self.owner,'session-a'))

    def test_prompt_only_contains_own_transcript_and_no_tools(self):
        req=request(self.source)
        self.assertEqual(req['tools'],[]);self.assertFalse(req['store'])
        self.assertEqual(req['model'],'gpt-6-luna')
        self.assertEqual(req['text']['format']['schema']['properties']['overview']['properties']['passages']['items']['enum'],['p1'])

    async def test_source_deleted_during_generation_is_not_recreated(self):
        class Budget:
            def reserve(self,*args):pass
            def finish(self,*args):pass
        async def provider(req):
            self.store.delete_source(self.owner,'session-a')
            return dict(data=notes(),usage={})
        self.notes.enqueue(self.owner,'session-a',1)
        with self.assertRaisesRegex(Rejected,'source_unavailable'):
            await NotesGenerator(self.store,provider,Budget()).generate(self.owner,'session-a')
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM recording_notes').fetchone()[0],0)

class RecordedNotesAcceptance(unittest.IsolatedAsyncioTestCase):
    async def test_exact_provider_replay_through_generator_and_reopen(self):
        import tempfile,contextlib,io
        from pathlib import Path
        from evaluate_recording_notes import run
        with tempfile.TemporaryDirectory() as folder,contextlib.redirect_stdout(io.StringIO()):
            results=await run(Path(folder)/'replay',replay=Path(__file__).parent/'fixtures/recording-notes/calls.json')
            self.assertEqual(len(results),5)
            reflection=next(r for r in results if r['case']=='reflection')
            self.assertIn('not',reflection['notes']['overview']['text'])
