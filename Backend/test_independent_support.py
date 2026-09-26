import copy,json,sqlite3,tempfile,unittest
from pathlib import Path
from contextlib import closing
from types import SimpleNamespace
from evaluate_independent_support import screen_cases,build,parse,reserve,RESERVATION
from admission import Rejected
class IndependentSupportTests(unittest.TestCase):
    def test_cost_bound_and_citations(self):
        cases,_=screen_cases();req,bound=build(cases)
        self.assertLessEqual(bound,RESERVATION);self.assertEqual(req['model'],'gpt-6-sol')
        data={k:dict(verdict='uncertain',passages=[]) for k in cases}
        parse(data,cases)
        key=next(iter(data));data[key]=dict(verdict='supported',passages=['invented'])
        with self.assertRaisesRegex(Rejected,'citations'):parse(data,cases)
        cases[key]['claim']='x'*50000
        with self.assertRaisesRegex(Rejected,'cost_bound'):build(cases)
    def test_no_retry_or_spend_above_approved_allowance(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'budget.sqlite'
            with closing(sqlite3.connect(path)) as db, db:
                db.execute('CREATE TABLE profile_attempt(id TEXT PRIMARY KEY,model TEXT,reserved INTEGER,state TEXT,usage TEXT)')
                db.execute("INSERT INTO profile_attempt VALUES('prior','jev-1.13.0',3160000,'completed',NULL)")
            budget=SimpleNamespace(path=path,cap=3200000)
            reserve(budget,'screen')
            with self.assertRaisesRegex(Rejected,'paid_retry'):reserve(budget,'screen')
            with self.assertRaisesRegex(Rejected,'budget_limit'):reserve(budget,'another')
            with closing(sqlite3.connect(path)) as db, db:self.assertEqual(db.execute('SELECT sum(reserved) FROM profile_attempt').fetchone()[0],3200000)
    def test_recorded_screen_passes_all_frozen_support_cases(self):
        artifact=json.loads((Path(__file__).parent/'fixtures/independent-support/sol-screen.json').read_text())
        cases,expected=screen_cases();req,bound=build(cases)
        previous=copy.deepcopy(artifact['request']);previous['max_output_tokens']=1300
        self.assertEqual(req,previous) # Only the future cost ceiling changed after this run.
        self.assertLess(artifact['response']['usage']['output_tokens'],req['max_output_tokens'])
        verdicts=parse(artifact['response']['data'],cases)
        self.assertEqual(expected,artifact['expected'])
        self.assertEqual(len(verdicts),17)
        self.assertTrue(all((v['verdict']=='supported')==(expected[k]=='supported') for k,v in verdicts.items()))
        self.assertTrue(all(artifact['checks'].values()))
