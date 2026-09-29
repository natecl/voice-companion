"""Multi-step real policy/retrieval/storage replay; synthetic model, no provider calls.

Export exact request states for a separately authorized semantic model screen.
Virtual time tests post-cooldown behavior without audio or wall-clock waiting.
"""
import asyncio
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'Backend'))
from companion_chat import CompanionChat
from memory_store import MemoryStore
from proactive_policy import ProactivePolicy
from proactive_service import ProactiveService
from proactive_replay import recording

SOURCES = {
    'cedar': 'For the Cedar pilot, the team agreed to test the basic recording flow with five people before adding features. Those tests had not happened as of this note. Calendar integration should wait until afterward.',
    'harbor': 'For the Harbor workshop, Mina said the venue must have step-free access. The first-floor room has step-free access; the upstairs room has only stairs.'
}
CEDAR = 'The Cedar team agreed to test the basic recording flow with five people before adding features. As of that note, the tests were still pending; calendar integration was meant to wait.'
HARBOR = 'Mina needs step-free access for the Harbor workshop. The earlier note says the first-floor room has it; the upstairs room has only stairs.'
STEPS = [
    dict(at=0, id='missing-prerequisite', text='For the Cedar pilot, the basic recording flow is working. Should we add calendar integration now?', source='cedar', answer=CEDAR, expected='contribution'),
    dict(at=30, id='acknowledged-during-cooldown', text='Right, we will test with five people before adding features. Calendar integration will wait. That is settled.', expected='not_scheduled'),
    dict(at=65, id='acknowledged-after-cooldown', text='The Cedar plan is settled: five people test the basic recording flow first, then calendar integration. Nothing more to decide there.', expected='silence'),
    dict(at=90, id='topic-covered', text='Moving to the Harbor workshop. Mina needs step-free access; the first-floor room has it and the upstairs room only has stairs. We already have those facts.', expected='silence'),
    dict(at=115, id='new-useful-opening', text='For the Harbor workshop, Joel just joined and is about to book the upstairs room, forgetting the step-free access requirement. Is that room suitable for Mina?', source='harbor', answer=HARBOR, expected='contribution'),
    dict(at=180, id='duplicate-output-defense', text='Back to Cedar: the five-person test before adding features and calendar integration afterward are already agreed. We do not need another reminder.', source='cedar', answer=CEDAR, expected='silence'),
    dict(at=205, id='quiet', text='Another question about the Harbor workshop venue and step-free access.', quiet=True, expected='not_scheduled'),
]


class ScriptedModel:
    def __init__(self, recorded=None): self.step=None; self.requests=[]; self.recorded=recorded
    async def extract(self, request):
        step=self.step;state=json.loads(request['input'])
        expected_previous=[] if step['at']==0 else [CEDAR] if step['at']<180 else [CEDAR,HARBOR]
        assert state['previous']==expected_previous, (step['id'],'previous contribution missing')
        assert step['text'] in ' '.join(p['text'] for p in state['current']['passages'])
        # Deliberately repeat at 180: durable duplicate defense must reject it,
        # independently of whether a real model would correctly remain silent.
        if 'source' in step:
            evidence=next(s['id'] for s in state['sources'] if s['session_id']==step['source'])
            data=dict(decision='contribute',text=step['answer'],evidence_ids=[evidence])
        else:data=dict(decision='silence',text='',evidence_ids=[])
        self.requests.append(dict(case=step['id'],request=request,
            expected_model_decision='silence' if step['id']=='duplicate-output-defense' else data['decision'],
            synthetic_response=data))
        if self.recorded and step['id']==self.recorded['case']:
            assert request==self.recorded['request'], 'Exact request changed; no live fallback'
            return self.recorded['response']
        if 'messages' in request['text']['format']['schema']['properties']:
            data=dict(decision=data['decision'],messages=[data['text']] if data['text'] else [],evidence_ids=data['evidence_ids'])
        return dict(data=data,usage={})


class SyntheticBudget:
    def __init__(self):self.keys=set()
    def reserve(self,key,model):
        assert key not in self.keys;self.keys.add(key)
    def finish(self,key,usage=None):pass


async def run(recorded=None, *, grouped_messages=False):
    with tempfile.TemporaryDirectory() as folder:
        path=Path(folder)/'memory.sqlite';store=MemoryStore(path,clock=lambda:300.)
        owner=store.owner_for('fictional-conversation-replay')
        for name,text in SOURCES.items():store.put_source(owner,recording(name,text))
        policy=ProactivePolicy();policy.start(owner,'capture')
        model=ScriptedModel(recorded);budget=SyntheticBudget()
        service=ProactiveService(store,model,budget,grouped_messages=grouped_messages)
        passages=[];results=[];delivered=[]
        for index,step in enumerate(STEPS,1):
            if step.get('quiet'):policy.quiet()
            passages.append(dict(id='p'+str(index),start=float(step['at']),duration=1.,text=step['text'],speakers=[]))
            live=dict(recording('capture','',revision=index,completed=False),passages=list(passages))
            lease=policy.observe(live,step['at'])
            if lease is None:result=dict(type='not_scheduled')
            else:
                model.step=step
                result=await service.evaluate(owner,live,lambda:policy.valid(lease,step['at']+1))
                policy.finish(lease,step['at']+1,result.get('turn_id'))
            assert result['type']==step['expected'],(step['id'],result)
            if result['type']=='contribution':delivered.append(result['text'])
            results.append(dict(case=step['id'],at=step['at'],result=result['type']))
            if recorded and step['id']==recorded['case']:break
        turns=CompanionChat(MemoryStore(path)).page(owner)['turns']
        assert [t['answer'] for t in turns]==delivered
        assert policy.capture=='capture'
        if not recorded:assert not policy.enabled and delivered==[CEDAR,HARBOR]
        return dict(provenance='Synthetic model decisions; real scheduling, retrieval and durable storage; no audio',
            steps=results,saved_messages=len(turns),model_requests=len(model.requests),paid_calls=0,
            requests=model.requests)


if __name__=='__main__':
    result=asyncio.run(run())
    if len(sys.argv)>1:Path(sys.argv[1]).write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k!='requests'},indent=2))
