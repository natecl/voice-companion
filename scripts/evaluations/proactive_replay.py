"""Free behavioral replay of scheduling + real SQLite evidence discovery.

No provider response is inferred: the example draft is a labeled synthetic fixture.
"""
import json
from pathlib import Path
import tempfile
from memory_store import MemoryStore
from proactive_policy import ProactivePolicy
from proactive_context import prepare
from proactive_models import parse_draft


def recording(session,text,revision=1,completed=True):
    return dict(session_id=session,revision=revision,captured_at=100.,timezone='UTC',completed=completed,
        passages=[dict(id='p1',start=0.,duration=5.,text=text,speakers=[])])


def run():
    with tempfile.TemporaryDirectory() as directory:
        store=MemoryStore(Path(directory)/'memory.sqlite',clock=lambda:300.)
        owner=store.owner_for('synthetic-replay')
        store.put_source(owner,recording('prior','Alex has been waking up at three every morning.'))
        policy=ProactivePolicy();policy.start(owner,'live')
        live=recording('live',"We are discussing Alex waking at three with the doctor.",completed=False)
        lease=policy.observe(live,0)
        context=prepare(store,owner,live)
        result=parse_draft(dict(decision='contribute',text='An earlier note mentioned Alex waking at three each morning.',
            evidence_ids=['m1']),context['state'])
        delivered=policy.finish(lease,1,'alex-sleep')
        assert delivered and policy.observe(live,61) is None
        revised=recording('live',"We already discussed Alex waking at three.",revision=2,completed=False)
        late=policy.observe(revised,62);policy.quiet()
        assert not policy.finish(late,63,'repeat')
        assert prepare(store,store.owner_for('other-owner'),live) is None
        return dict(input='synthetic; no audio or model calls',delivered=[result['text']],
            supporting_sources=[s['session_id'] for s in context['state']['sources']],
            duplicate_suppressed=True,quiet_rejected_pending=True,owner_isolation=True,
            paid_calls=0,chat_persistence='not integrated in this checkpoint')


if __name__=='__main__':print(json.dumps(run(),indent=2))
