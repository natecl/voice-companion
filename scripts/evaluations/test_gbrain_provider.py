"""Offline cost and no-retry contract tests for the evaluation transport."""
import importlib.util
from pathlib import Path
import sqlite3
import unittest
spec = importlib.util.spec_from_file_location('provider', Path(__file__).with_name('gbrain-provider.py'))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:', isolation_level=None)
        self.db.executescript('''CREATE TABLE request(id TEXT PRIMARY KEY, credential TEXT, category TEXT, created REAL, reserved INTEGER, state TEXT CHECK(state IN ('active','completed','failed','interrupted')));
        CREATE TABLE budget(id INTEGER,cap INTEGER); INSERT INTO budget VALUES(1,5000000);
        CREATE TABLE policy(category TEXT,cap INTEGER); INSERT INTO policy VALUES('ask',2950000);
        CREATE TABLE credential(id TEXT); INSERT INTO credential VALUES('synthetic');''')
    def tearDown(self):
        self.db.close()
    def test_reserved_attempt_cannot_retry(self):
        p.reserve(self.db,p.PREFIX+'one',5000)
        with self.assertRaises(ValueError):p.reserve(self.db,p.PREFIX+'one',5000)
        self.assertEqual(self.db.execute('SELECT sum(reserved) FROM request').fetchone()[0],5000)
    def test_allowance_is_not_enlarged(self):
        p.reserve(self.db,p.PREFIX+'one',500000)
        with self.assertRaises(ValueError):p.reserve(self.db,p.PREFIX+'two',1)
    def test_existing_global_spend_counts(self):
        self.db.execute("INSERT INTO request VALUES('prior','x','stt',0,4999999,'completed')")
        with self.assertRaises(ValueError):p.reserve(self.db,p.PREFIX+'one',2)
    def test_category_headroom_counts(self):
        self.db.execute("INSERT INTO request VALUES('prior','x','ask',0,2950000,'completed')")
        with self.assertRaises(ValueError):p.reserve(self.db,p.PREFIX+'one',1)
    def test_invalid_model_rejected_before_reserve(self):
        with self.assertRaises(ValueError):p.validate(dict(kind='chat',body=dict(model='other')))
    def test_cost_bound(self):
        body=dict(model='gpt-6-luna',store=False,tools=[],service_tier='default',reasoning={'effort':'none'},max_output_tokens=4000,input='test')
        endpoint,bound=p.validate(dict(kind='chat',body=body))
        self.assertEqual(endpoint,'responses'); self.assertGreater(bound,3000)

if __name__=='__main__':unittest.main()
