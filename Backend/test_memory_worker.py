"""Real queue/writer tests with local provider adapters, no paid inference."""
import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from urllib.request import urlopen
from websockets.asyncio.server import serve
from admission import Rejected
from memory_store import MemoryStore
from memory_writer import MemoryWorker, MemoryWriter
from relay import Relay
from test_memory import source
from test_memory_learning import answers, memory


class WorkerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = MemoryStore(Path(self.temp.name)/'memory.sqlite')
        self.owner = self.store.owner_for('fixture')
        self.calls = []
        self.reservations = []
        outer = self

        class Models:
            async def extract(self, request):
                outer.calls.append('extract')
                return {'data': {'memories':[memory()]}, 'usage':{}}
            async def verify_support(self, request):
                outer.calls.append('support')
                return {'data':answers(request), 'usage':{}}
            async def judge(self, request):
                outer.calls.append('judge')
                return {'data':answers(request), 'usage':{}}

        class Budget:
            def reserve(self, *args): outer.reservations.append(args)
            def finish(self, *args): pass

        class Admission:
            def active_credentials(self): return ['fixture']

        self.writer = MemoryWriter(self.store, Models(), Budget())
        self.worker = MemoryWorker(self.writer, Admission())

    async def wait_idle(self):
        async with asyncio.timeout(2):
            while self.worker.state != 'idle':
                if self.worker.state == 'halted': self.fail('Unexpected halted worker')
                await asyncio.sleep(.005)

    async def stop(self, task):
        task.cancel()
        with self.assertRaises(asyncio.CancelledError): await task

    def jobs(self):
        with self.store.connect() as db:
            return [dict(r) for r in db.execute('SELECT session,state,error FROM job ORDER BY rowid')]

    async def test_oversized_then_valid_learns_once_and_does_not_retry_after_restart(self):
        self.store.put_source(self.owner, source('large',text='A conversation sentence. '*900))
        self.store.put_source(self.owner, source('valid',text='Maya prefers morning meetings.'))
        task = asyncio.create_task(self.worker.run())
        try:
            await self.wait_idle()
            self.assertEqual([j['state'] for j in self.jobs()], ['failed','done'])
            self.assertEqual(self.jobs()[0]['error'], 'memory_extraction_too_large')
            self.assertEqual(len(self.store.search(self.owner)),1)
            self.assertEqual(self.calls, ['extract','support','judge'])
            self.assertEqual(len(self.reservations),3)
            self.assertEqual(self.worker.status()['quarantined'],1)
        finally: await self.stop(task)
        self.worker = MemoryWorker(self.writer,self.worker.admission)
        task=asyncio.create_task(self.worker.run())
        try:
            await self.wait_idle()
            self.assertEqual(len(self.reservations),3)
        finally: await self.stop(task)

    async def test_global_budget_auth_and_unknown_failures_halt_without_next_attempt(self):
        for error in [Rejected('profile_budget_limit'), PermissionError('secret-provider-text'), RuntimeError('private transcript')]:
            with self.subTest(error=type(error).__name__):
                # Each subcase has a fresh queue and worker.
                self.setUp()
                self.store.put_source(self.owner, source('first'))
                self.store.put_source(self.owner, source('following'))
                async def fail(request): raise error
                self.writer.models.extract=fail
                await asyncio.wait_for(self.worker.run(),2)
                self.assertEqual(self.worker.state,'halted')
                self.assertEqual([j['state'] for j in self.jobs()],['failed','queued'])
                self.assertEqual(len(self.reservations),1)
                if not isinstance(error, Rejected):
                    self.assertNotIn(str(error), json.dumps(self.worker.status()))

    async def test_budget_reservation_denial_makes_no_provider_call(self):
        self.store.put_source(self.owner, source('first'))
        self.store.put_source(self.owner, source('following'))
        def deny(*args): raise Rejected('profile_budget_limit')
        self.writer.budget.reserve = deny
        await asyncio.wait_for(self.worker.run(), 2)
        self.assertEqual(self.worker.state, 'halted')
        self.assertEqual(self.calls, [])
        self.assertEqual([j['state'] for j in self.jobs()], ['failed', 'queued'])

    async def test_source_deleted_in_flight_does_not_block_following_job(self):
        self.store.put_source(self.owner,source('deleted'))
        self.store.put_source(self.owner,source('following'))
        original=self.writer.models.extract
        first=True
        async def delete_then_return(request):
            nonlocal first
            if first:
                first=False
                self.store.delete_source(self.owner,'deleted')
            return await original(request)
        self.writer.models.extract=delete_then_return
        task=asyncio.create_task(self.worker.run())
        try:
            await self.wait_idle()
            self.assertEqual([j['state'] for j in self.jobs()],['obsolete','done'])
            self.assertEqual(len(self.store.search(self.owner)),1)
            self.assertEqual(len(self.reservations),4)
        finally: await self.stop(task)

    async def test_actual_http_diagnostics_show_halt_without_changing_liveness(self):
        self.store.put_source(self.owner,source())
        async def fail(request): raise Rejected('profile_budget_limit')
        self.writer.models.extract=fail
        await self.worker.run()
        relay=Relay('unused',learning_status=self.worker.status)
        async with serve(relay.handle,'127.0.0.1',0,process_request=relay.authorize) as server:
            port=server.sockets[0].getsockname()[1]
            def get(path):
                with urlopen(f'http://127.0.0.1:{port}{path}') as response:
                    return response.status,response.read().decode()
            code,body=await asyncio.to_thread(get,'/health/learning')
            self.assertEqual(code,200)
            self.assertEqual(json.loads(body)['state'],'halted')
            self.assertEqual(await asyncio.to_thread(get,'/health'),(200,'ready\n'))


if __name__=='__main__': unittest.main()
