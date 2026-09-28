"""Exact-request replay of the real provider screen through the durable service."""
import json
from pathlib import Path
import tempfile
import unittest
from companion_chat import CompanionChat
from memory_store import MemoryStore
from proactive_service import ProactiveService

ROOT=Path(__file__).parent/'fixtures/proactive'

class Replay:
    def __init__(self,calls):self.calls=list(calls);self.used=0
    async def invoke(self,request):
        saved=self.calls[self.used];self.used+=1
        if saved['request']!=request:raise AssertionError('Unmatched request; no paid fallback')
        raw=saved['raw']
        if request['model']=='gpt-6-luna':
            text=''.join(c['text'] for o in raw['output'] if o['type']=='message' for c in o['content'] if c['type']=='output_text')
            data=json.loads(text)
        else:data=raw
        return dict(data=data,usage=raw['usage'])
    extract=invoke
    judge=invoke

class Budget:
    def reserve(self,*args):pass
    def finish(self,*args):pass

def source(session,text,completed):
    return dict(session_id=session,revision=1,captured_at=100.,timezone='UTC',completed=completed,
        passages=[dict(id='p1',start=0.,duration=5.,text=text,speakers=[])])

class RecordedScreen(unittest.IsolatedAsyncioTestCase):
    async def test_exact_live_screen_through_service(self):
        cases={c['id']:c for c in json.loads((ROOT/'cases.json').read_text())}
        for row in json.loads((ROOT/'live-screen-20260928/results.json').read_text()):
            with self.subTest(case=row['case'],route=row['route']),tempfile.TemporaryDirectory() as folder:
                store=MemoryStore(Path(folder)/'memory.sqlite',clock=lambda:300.)
                owner=store.owner_for('qa');case=cases[row['case']]
                store.put_source(owner,source('prior',case['past'],True))
                model=Replay(row['calls'])
                service=ProactiveService(store,model,Budget(),route=row['route'])
                result=await service.evaluate(owner,source('capture',case['live'],False),lambda:True)
                self.assertEqual(result['type'],'contribution' if row['decision']=='contribute' else 'silence')
                self.assertEqual(model.used,len(row['calls']))
                turns=CompanionChat(store).page(owner)['turns']
                if row['decision']=='contribute':self.assertEqual(turns[0]['answer'],row['text'])
                else:self.assertEqual(turns,[])
