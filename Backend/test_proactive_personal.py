"""Real Luna responses replayed through retrieval, validation and durable chat; no network."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from companion_chat import CompanionChat
from memory_store import MemoryStore
from proactive_service import ProactiveService
from test_proactive_service import Budget

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'scripts/evaluations'))
from proactive_personal_cases import seed_case
from proactive_replay import recording

class RecordedModel:
    def __init__(self,request,response):
        self.request,self.response=request,response
        self.calls=0
    async def extract(self,request):
        self.calls+=1
        if request != self.request:
            raise AssertionError('Request changed; no live fallback')
        return self.response

class PersonalReplayTests(unittest.IsolatedAsyncioTestCase):
    async def test_real_responses_survive_service_and_reopen(self):
        fixtures=ROOT/'fixtures/proactive'
        evidence=fixtures/'personal-evaluation'
        for cases_file,requests_file,variants in [
            ('personal-cases.json','requests.json',('baseline','candidate')),
            ('personal-validation.json','validation-requests.json',('candidate',))
        ]:
            cases={c['id']:c for c in json.loads((fixtures/cases_file).read_text())}
            for row in json.loads((evidence/requests_file).read_text()):
                for variant in variants:
                    with self.subTest(case=row['case'],variant=variant),tempfile.TemporaryDirectory() as folder:
                        path=Path(folder)/'memory.sqlite'
                        store=MemoryStore(path,clock=lambda:300.)
                        owner=store.owner_for('fictional-personal-evaluation')
                        case=cases[row['case']];seed_case(store,owner,case)
                        saved=json.loads((evidence/(row['case']+'-'+variant+'.json')).read_text())
                        model=RecordedModel(row[variant],saved)
                        service=ProactiveService(store,model,Budget())
                        live=recording('capture',case['live'],completed=False)
                        # Baseline is archived evidence; candidate must use the selected runtime prompt.
                        import proactive_models
                        prompt=row[variant]['instructions'] if variant=='baseline' else proactive_models.PROMPT
                        with patch('proactive_models.PROMPT',prompt):
                            result=await service.evaluate(owner,live,lambda:True)
                        decision=saved['data']['decision']
                        self.assertEqual(result['type'],'contribution' if decision=='contribute' else 'silence')
                        if variant=='candidate':self.assertEqual(decision,case['expected'])
                        self.assertEqual(model.calls,1)
                        turns=CompanionChat(MemoryStore(path)).page(owner)['turns']
                        if decision=='contribute':
                            self.assertEqual(len(turns),1)
                            self.assertEqual(turns[0]['answer'],saved['data']['text'])
                            self.assertEqual(turns[0]['kind'],'proactive')
                            self.assertEqual(turns[0]['question'],'')
                            self.assertEqual(CompanionChat(store).context(owner)['turns'][0]['origin'],'proactive')
                            store.delete_source(owner,'prior')
                            self.assertEqual(CompanionChat(store).page(owner)['turns'][0]['answer'],saved['data']['text'])
                        else:self.assertEqual(turns,[])
                        self.assertEqual((await service.evaluate(owner,live,lambda:True))['type'],'existing')
                        self.assertEqual(model.calls,1)
