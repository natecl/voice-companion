import asyncio
import json
from pathlib import Path
import tempfile
import unittest
from companion_chat import CompanionChat
from memory_models import JEV
from memory_store import MemoryStore
from proactive_service import ProactiveService
from proactive_store import ProactiveStore
from test_memory import source


class Budget:
    def __init__(self):self.attempts={}
    def reserve(self,key,model):
        if key in self.attempts:raise AssertionError('Paid retry')
        self.attempts[key]=dict(model=model,state='reserved')
    def finish(self,key,usage=None):self.attempts[key]['state']='complete' if usage is not None else 'failed'


class Models:
    def __init__(self):self.calls=[];self.mutate=lambda:None;self.silence=False;self.bad=False;self.stall=False
    async def extract(self,request):
        self.calls.append(request)
        self.mutate()
        if self.stall:await asyncio.Future()
        state=json.loads(request['input'])
        return dict(usage={},data=dict(decision='silence' if self.silence else 'contribute',
            text='' if self.silence else 'An earlier note mentioned Alex waking at three each morning.',
            evidence_ids=[] if self.silence else ['unknown' if self.bad else state['sources'][0]['id']]))
    async def judge(self,request):
        self.calls.append(request)
        choices={'connection':'none' if self.silence else 'useful','novelty':'new'}
        return dict(usage={},data=dict(model=JEV,answers={key:dict(type='choice',choice=choices[key],confidence=1.,
            probabilities={name:float(name==choices[key]) for name in question['criteria']})
            for key,question in request['questions'].items()}))


class ProactiveServiceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        self.path=Path(folder.name)/'memory.sqlite'
        self.store=MemoryStore(self.path,clock=lambda:300.)
        self.owner=self.store.owner_for('qa')
        self.store.put_source(self.owner,source('prior',text='Alex has been waking at three each morning.'))
        self.live=dict(source('capture',text='We are discussing Alex waking at three with the doctor.'),completed=False)
        self.models=Models();self.budget=Budget();self.active=True
        self.service=ProactiveService(self.store,self.models,self.budget)

    async def evaluate(self,live=None):return await self.service.evaluate(self.owner,live or self.live,lambda:self.active)

    async def test_save_reopen_same_normal_chat_without_user_message(self):
        result=await self.evaluate();self.assertEqual(result['type'],'contribution')
        reopened=CompanionChat(MemoryStore(self.path)).page(self.owner)['turns']
        self.assertEqual(len(reopened),1);self.assertEqual(reopened[0]['kind'],'proactive')
        self.assertEqual(reopened[0]['question'],'')
        history=CompanionChat(self.store).context(self.owner)['turns'][0]
        self.assertNotIn('user',history);self.assertEqual(history['origin'],'proactive')
        self.assertEqual((await self.evaluate())['type'],'existing')
        self.assertEqual(len(self.models.calls),1)
        self.store.delete_source(self.owner,'prior')
        turn=CompanionChat(self.store).page(self.owner)['turns'][0]
        self.assertEqual(turn['answer'],result['text']);self.assertEqual(turn['state'],'outdated')

    async def test_grouped_messages_roundtrip_as_one_durable_contribution(self):
        messages=['Alex mentioned waking at three each morning.', 'That may be worth bringing up.']
        class GroupedModel:
            async def extract(inner,request):
                self.assertIn('messages',request['text']['format']['schema']['properties'])
                return dict(usage={},data=dict(decision='contribute',messages=messages,evidence_ids=['m1']))
        self.service=ProactiveService(self.store,GroupedModel(),self.budget,grouped_messages=True)
        result=await self.evaluate()
        self.assertEqual(result['type'],'contribution')
        turns=CompanionChat(MemoryStore(self.path)).page(self.owner)['turns']
        self.assertEqual(len(turns),1)
        self.assertEqual(turns[0]['answer'].split('\n\n'),messages)
        self.assertEqual((await self.evaluate())['type'],'existing')
        self.assertEqual(len(self.budget.attempts),1)
        self.store.delete_source(self.owner,'prior')
        self.assertEqual(CompanionChat(self.store).page(self.owner)['turns'][0]['answer'],result['text'])

    async def test_empty_other_owner_and_silence_do_not_write_messages(self):
        other=self.store.owner_for('other')
        self.assertEqual((await self.service.evaluate(other,self.live,lambda:True))['type'],'silence')
        self.assertEqual(len(self.models.calls),0)
        self.models.silence=True
        self.assertEqual((await self.evaluate())['type'],'silence')
        self.assertEqual(CompanionChat(self.store).page(self.owner)['turns'],[])

    async def test_jev_abstention_spends_only_one_call(self):
        self.service.route='jev';self.models.silence=True
        self.assertEqual((await self.evaluate())['type'],'silence')
        self.assertEqual(len(self.models.calls),1)
        self.assertEqual(self.models.calls[0]['model'],JEV)

    async def test_quiet_during_model_work_discards_result(self):
        self.models.mutate=lambda:setattr(self,'active',False)
        self.assertEqual((await self.evaluate())['type'],'cancelled')
        self.assertEqual(CompanionChat(self.store).page(self.owner)['turns'],[])
        self.active=True
        self.assertEqual((await self.evaluate())['type'],'existing')
        self.assertEqual(len(self.models.calls),1)

    async def test_deleted_or_revised_evidence_cannot_be_saved(self):
        self.models.mutate=lambda:self.store.delete_source(self.owner,'prior')
        self.assertEqual((await self.evaluate())['type'],'unavailable')
        self.assertEqual(CompanionChat(self.store).page(self.owner)['turns'],[])
        with self.store.connect() as db:
            self.assertEqual(db.execute('SELECT count(*) FROM companion_snapshot').fetchone()[0],0)

    async def test_bad_output_is_not_saved_or_retried(self):
        self.models.bad=True
        self.assertEqual((await self.evaluate())['type'],'unavailable')
        self.assertEqual((await self.evaluate())['type'],'existing')
        self.assertEqual(len(self.budget.attempts),1)
        self.assertEqual(CompanionChat(self.store).page(self.owner)['turns'],[])

    async def test_same_source_connection_deduplicated_after_new_revision(self):
        self.assertEqual((await self.evaluate())['type'],'contribution')
        self.assertEqual((await self.evaluate(dict(self.live,revision=2)))['type'],'silence')
        self.assertEqual(len(CompanionChat(self.store).page(self.owner)['turns']),1)

    async def test_concurrent_replay_and_cancellation_no_retry(self):
        self.models.stall=True
        task=asyncio.create_task(self.evaluate())
        for _ in range(10):
            if self.models.calls:break
            await asyncio.sleep(0)
        self.assertEqual((await self.evaluate())['state'],'pending')
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):await task
        self.assertEqual((await self.evaluate())['state'],'cancelled')
        self.assertEqual(len(self.models.calls),1)
        self.assertEqual(next(iter(self.budget.attempts.values()))['state'],'failed')

    def test_pending_attempt_survives_process_restart_without_paid_retry(self):
        messages=ProactiveStore(self.store)
        self.assertIsNone(messages.claim(self.owner,'capture','cutoff'))
        self.assertEqual(ProactiveStore(MemoryStore(self.path)).claim(self.owner,'capture','cutoff')['state'],'pending')

    async def test_budget_rejection_never_calls_provider_or_retries_cutoff(self):
        from admission import Rejected
        class ExhaustedBudget:
            def reserve(inner,key,model):raise Rejected('proactive_budget_limit')
            def finish(inner,key,usage=None):raise AssertionError('No reservation was made')
        self.service.budget=ExhaustedBudget()
        self.assertEqual((await self.evaluate())['type'],'unavailable')
        self.assertEqual((await self.evaluate())['type'],'existing')
        self.assertEqual(self.models.calls,[])
        self.assertEqual(CompanionChat(MemoryStore(self.path)).page(self.owner)['turns'],[])

    async def test_multi_message_text_has_one_delivery_and_cooldown(self):
        from proactive_policy import ProactivePolicy
        messages=['Alex mentioned waking at three.', 'That may be worth bringing up.']
        original=self.models.extract
        async def paragraphs(request):
            result=await original(request)
            result['data']['text']='\n\n'.join(messages)
            return result
        self.models.extract=paragraphs
        policy=ProactivePolicy();policy.start(self.owner,'capture')
        lease=policy.observe(self.live,0)
        result=await self.service.evaluate(self.owner,self.live,lambda:policy.valid(lease,1))
        self.assertEqual(result['type'],'contribution')
        self.assertTrue(policy.finish(lease,1,result['turn_id']))
        self.assertEqual(len(policy.delivered),1)
        newer=dict(self.live,revision=2)
        self.assertIsNone(policy.observe(newer,60))
        self.assertIsNotNone(policy.observe(newer,61))
        turns=CompanionChat(MemoryStore(self.path)).page(self.owner)['turns']
        self.assertEqual(len(turns),1)
        self.assertEqual(turns[0]['answer'].split('\n\n'),messages)
        self.assertEqual(len(self.models.calls),1)
        self.assertNotIn('messages',self.models.calls[0]['text']['format']['schema']['properties'])
