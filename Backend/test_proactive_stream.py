"""No-provider regressions for continuous speech and oversized utterances."""
import asyncio
import copy
import json
import unittest
from unittest.mock import patch
from admission import Rejected
from proactive_context import recent_window
from proactive_policy import ProactivePolicy
from test_proactive_policy import live
import test_proactive_service
import test_proactive_socket

class WindowTests(unittest.TestCase):
    def test_unicode_tail_fits_and_preserves_original_offsets(self):
        passages=live()['passages']
        passages[0]['text']='Earlier material. '+('日本語 sentence. '*700)+'Recent useful context.'
        window=recent_window(passages)
        self.assertLessEqual(len(json.dumps(window,ensure_ascii=False).encode()),5000)
        self.assertTrue(window[0]['truncated'])
        self.assertTrue(window[0]['text'].endswith('Recent useful context.'))
        self.assertEqual(window[0]['text'],passages[0]['text'][window[0]['text_start']:window[0]['text_end']])

    def test_many_large_passages_keep_recent_full_passages(self):
        passages=[dict(live()['passages'][0],id=f'p{i}',text='word '*350+str(i)) for i in range(8)]
        window=recent_window(passages)
        self.assertLessEqual(len(json.dumps(window,ensure_ascii=False).encode()),5000)
        self.assertEqual(window[-1],passages[-1])
        self.assertGreater(len(window),0)
        self.assertLess(len(window),8)

    def test_append_keeps_original_deadline_but_rewrite_cancels(self):
        p=ProactivePolicy();p.start('owner','capture')
        first=live();lease=p.observe(first,0)
        extended=copy.deepcopy(first);extended['revision']=2
        extended['passages'][0]['text']+=' More speech.'
        p.observe(extended,2)
        self.assertTrue(p.valid(lease,3))
        self.assertFalse(p.valid(lease,16))
        extended['revision']=3;extended['passages'][0]['text']='Correction.'
        p.observe(extended,4)
        self.assertFalse(p.valid(lease,5))

class StreamingSocketTests(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = test_proactive_socket.SocketTests.asyncSetUp
    asyncTearDown = test_proactive_socket.SocketTests.asyncTearDown
    open = test_proactive_socket.SocketTests.open
    observe = test_proactive_socket.SocketTests.observe
    async def test_appended_speech_delivers_one_inflight_result(self):
        entered=asyncio.Event();release=asyncio.Event()
        original=self.models.extract
        async def delayed(request):
            entered.set();await release.wait();return await original(request)
        self.models.extract=delayed
        socket,_=await self.open();await self.observe(socket)
        await asyncio.wait_for(entered.wait(),1)
        self.live=copy.deepcopy(self.live);self.live['revision']=2
        self.live['passages'][0]['text']+=' We are still talking.'
        self.now=2;await self.observe(socket)
        policy=self.handler.policies[(self.owner,'capture')]
        for _ in range(100):
            if policy.latest_source['revision']==2:break
            await asyncio.sleep(.001)
        self.assertEqual(policy.latest_source['revision'],2)
        release.set()
        event=json.loads(await asyncio.wait_for(socket.recv(),1))
        self.assertEqual(event['type'],'contribution')
        self.assertEqual(len(self.models.calls),1)
        await socket.close()

class LongUtteranceTests(unittest.IsolatedAsyncioTestCase):
    setUp = test_proactive_service.ProactiveServiceTests.setUp
    evaluate = test_proactive_service.ProactiveServiceTests.evaluate
    async def test_clipped_current_context_saves_exact_snapshot(self):
        self.live['passages'][0]['text']=('Earlier discussion. '*600)+'Alex wakes at three each morning.'
        result=await self.evaluate()
        self.assertEqual(result['type'],'contribution')
        state=json.loads(self.models.calls[0]['input'])
        current=state['current']['passages'][0]
        self.assertGreater(current['text_start'],0)
        with self.store.connect() as db:
            row=db.execute('SELECT payload FROM companion_snapshot').fetchone()
        item=json.loads(row[0])[0]
        self.assertEqual(item['text'],current['text'])
        self.assertEqual(item['text_start'],current['text_start'])

    async def test_oversized_evidence_defers_without_spending_and_next_update_works(self):
        with patch('proactive_service.prepare',side_effect=Rejected('proactive_context_too_large')):
            self.assertEqual((await self.evaluate())['type'],'silence')
        self.assertEqual(len(self.budget.attempts),0)
        self.live['revision']=2
        self.assertEqual((await self.evaluate())['type'],'contribution')
        self.assertEqual(len(self.budget.attempts),1)
