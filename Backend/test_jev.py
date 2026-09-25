import asyncio
import copy
import json
from pathlib import Path
import tempfile
import unittest
import httpx
from admission import Admission, Rejected
from jev import Jev, Judgment, MODEL, QUESTION, interpret, payload, route_question
from service_policy import STT, ASK, JEV, add_ask_policy

GOOD = {'model':MODEL,'answers':{'intent':{'type':'choice','choice':'recall','probabilities':{'recall':.97,'summary':.01,'perspective':.01,'mixed_uncertain':.01},'confidence':.91}},'usage':{'input_tokens':450}}

class JevTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_contract_and_private_context_minimization(self):
        requests=[]
        async def respond(request):
            requests.append(json.loads(request.content))
            return httpx.Response(200,json=GOOD)
        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            result=await Jev(client).classify('What time?')
        self.assertEqual(result.route,'recall')
        self.assertEqual(requests[0]['state'],{'user_question':'What time?'})
        self.assertEqual(requests[0]['questions'],{'intent':QUESTION})
        self.assertEqual(len(requests),1)

    async def test_timeout_cancels_provider_and_budget_denial_does_not_call(self):
        class Stall:
            calls=0
            closed=False
            async def classify(self, question):
                self.calls+=1
                try: await asyncio.Future()
                finally: self.closed=True
        with tempfile.TemporaryDirectory() as d:
            store=Admission(Path(d)/'usage',total_microusd=500,limits={'jev':(500,500,64)})
            _,token=store.enroll();provider=Stall()
            result=await route_question(provider,'When?',store=store,token=token)
            self.assertEqual((result.route,result.reason),('direct','timeout'))
            self.assertLess(result.seconds,.85)
            self.assertTrue(provider.closed)
            self.assertEqual(store.usage(),[('jev',1,500)])
            await route_question(provider,'When?',store=store,token=token)
            self.assertEqual(provider.calls,1)
            store.close()

    async def test_outer_cancel_propagates_and_closes_route(self):
        started=asyncio.Event();closed=asyncio.Event()
        class Stall:
            async def classify(self, question):
                started.set()
                try: await asyncio.Future()
                finally: closed.set()
        with tempfile.TemporaryDirectory() as d:
            store=Admission(Path(d)/'usage',total_microusd=500,limits={'jev':(500,500,64)})
            _,token=store.enroll()
            task=asyncio.create_task(route_question(Stall(),'When?',store=store,token=token))
            await started.wait();task.cancel()
            with self.assertRaises(asyncio.CancelledError): await task
            self.assertTrue(closed.is_set())
            self.assertEqual(store.db.execute('select state from request').fetchone()[0],'failed')
            store.close()

    def test_bad_distributions_model_and_uncertainty(self):
        for mutate in [lambda d:d.update(model='other'),lambda d:d['answers']['intent'].update(confidence=float('nan')),lambda d:d['answers']['intent'].update(choice='invalid'),lambda d:d['answers']['intent']['probabilities'].update(recall=.2),lambda d:d['usage'].update(input_tokens=10000)]:
            data=copy.deepcopy(GOOD);mutate(data)
            with self.assertRaises((ValueError,KeyError,TypeError)):interpret(data)
        data=copy.deepcopy(GOOD);data['answers']['intent']['confidence']=.4
        self.assertEqual(interpret(data).reason,'uncertain')
        data=copy.deepcopy(GOOD);data['answers']['intent'].update(choice='mixed_uncertain',probabilities={'recall':.01,'summary':.01,'perspective':.01,'mixed_uncertain':.97})
        self.assertEqual(interpret(data).route,'direct')

    def test_additive_migration_and_bounded_batch_preserve_limits(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'ledger'
            store=Admission(path,total_microusd=5_000_000,limits={'stt':STT,'ask':ASK})
            _,token=store.enroll();request=store.reserve(token,'ask');store.finish(request,completed=True);store.close()
            add_ask_policy(path,jev=True);add_ask_policy(path,jev=True)
            store=Admission(path,total_microusd=5_000_000,limits={'stt':STT,'ask':ASK,'jev':JEV})
            batch=store.reserve_evaluation(token,'ask',16)
            self.assertEqual(store.usage(),[('ask',2,51000)])
            with self.assertRaises(Rejected):store.reserve(token,'ask')
            with self.assertRaises(ValueError):store.reserve_evaluation(token,'ask',17)
            store.finish(batch,completed=False)
            self.assertEqual(store.db.execute("select daily from policy where category='ask'").fetchone()[0],20)
            self.assertEqual(store.usage(),[('ask',2,51000)])
            store.close()
